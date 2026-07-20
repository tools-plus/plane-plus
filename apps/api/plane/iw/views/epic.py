# InfraWatch — Epic API (API key authenticated)
# Exposes epic CRUD under /api/v1/ with X-Api-Key auth
# Epics are issues with type.is_epic=True

import json

from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import (
    Case,
    CharField,
    Count,
    Exists,
    F,
    Func,
    Max,
    OuterRef,
    Q,
    Subquery,
    Value,
    When,
)
from django.utils import timezone

from rest_framework import status
from rest_framework.response import Response

from plane.api.views.base import BaseAPIView
from plane.api.serializers import IssueSerializer
from plane.app.permissions import ProjectEntityPermission
from plane.bgtasks.issue_activities_task import issue_activity
from plane.bgtasks.webhook_task import model_activity
from plane.db.models import (
    CycleIssue,
    FileAsset,
    Issue,
    IssueLink,
    IssueType,
    Project,
    ProjectMember,
    Workspace,
)
from plane.iw.gating import assert_epics_enabled, assert_project_epics_enabled
from plane.utils.host import base_host


class EpicListCreateAPIEndpoint(BaseAPIView):
    """List and create epics via API key.

    Epics are issues whose IssueType has is_epic=True.
    Mirrors the work-item list/create endpoint but scoped to epics only.
    """

    model = Issue
    webhook_event = "issue"
    permission_classes = [ProjectEntityPermission]
    serializer_class = IssueSerializer
    use_read_replica = True

    def get_queryset(self):
        return (
            Issue.issue_objects.annotate(
                sub_issues_count=Issue.issue_objects.filter(parent=OuterRef("id"))
                .order_by()
                .annotate(count=Func(F("id"), function="Count"))
                .values("count")
            )
            .filter(
                project_id=self.kwargs.get("project_id"),
                workspace__slug=self.kwargs.get("slug"),
                type__is_epic=True,
            )
            .select_related("project", "workspace", "state", "parent")
            .prefetch_related("assignees", "labels")
            .order_by(self.kwargs.get("order_by", "-created_at"))
        ).distinct()

    def get(self, request, slug, project_id):
        """List epics in a project (paginated)."""
        assert_project_epics_enabled(slug, project_id)

        # Custom ordering for priority and state
        priority_order = ["urgent", "high", "medium", "low", "none"]
        state_order = ["backlog", "unstarted", "started", "completed", "cancelled"]

        order_by_param = request.GET.get("order_by", "-created_at")

        issue_queryset = (
            self.get_queryset()
            .annotate(
                cycle_id=Subquery(
                    CycleIssue.objects.filter(
                        issue=OuterRef("id"), deleted_at__isnull=True
                    ).values("cycle_id")[:1]
                )
            )
            .annotate(
                link_count=IssueLink.objects.filter(issue=OuterRef("id"))
                .order_by()
                .annotate(count=Func(F("id"), function="Count"))
                .values("count")
            )
            .annotate(
                attachment_count=FileAsset.objects.filter(
                    issue_id=OuterRef("id"),
                    entity_type=FileAsset.EntityTypeContext.ISSUE_ATTACHMENT,
                )
                .order_by()
                .annotate(count=Func(F("id"), function="Count"))
                .values("count")
            )
        )

        total_issue_queryset = Issue.issue_objects.filter(
            project_id=project_id,
            workspace__slug=slug,
            type__is_epic=True,
        )

        # Priority Ordering
        if order_by_param == "priority" or order_by_param == "-priority":
            priority_order = (
                priority_order
                if order_by_param == "priority"
                else priority_order[::-1]
            )
            issue_queryset = issue_queryset.annotate(
                priority_order=Case(
                    *[
                        When(priority=p, then=Value(i))
                        for i, p in enumerate(priority_order)
                    ],
                    output_field=CharField(),
                )
            ).order_by("priority_order")

        # State Ordering
        elif order_by_param in [
            "state__name",
            "state__group",
            "-state__name",
            "-state__group",
        ]:
            state_order = (
                state_order
                if order_by_param in ["state__name", "state__group"]
                else state_order[::-1]
            )
            issue_queryset = issue_queryset.annotate(
                state_order=Case(
                    *[
                        When(state__group=state_group, then=Value(i))
                        for i, state_group in enumerate(state_order)
                    ],
                    default=Value(len(state_order)),
                    output_field=CharField(),
                )
            ).order_by("state_order")
        # assignee and label ordering
        elif order_by_param in [
            "labels__name",
            "-labels__name",
            "assignees__first_name",
            "-assignees__first_name",
        ]:
            issue_queryset = issue_queryset.annotate(
                max_values=Max(
                    order_by_param[1::]
                    if order_by_param.startswith("-")
                    else order_by_param
                )
            ).order_by(
                "-max_values" if order_by_param.startswith("-") else "max_values"
            )
        else:
            issue_queryset = issue_queryset.order_by(order_by_param)

        return self.paginate(
            request=request,
            queryset=issue_queryset,
            total_count_queryset=total_issue_queryset,
            on_results=lambda issues: IssueSerializer(
                issues, many=True, fields=self.fields, expand=self.expand
            ).data,
        )

    def post(self, request, slug, project_id):
        """Create a new epic in the project.

        Automatically sets the epic IssueType so the caller does not
        need to know the type_id.
        """
        project = Project.objects.get(pk=project_id)
        assert_epics_enabled(project)
        workspace = Workspace.objects.get(slug=slug)

        # Find or fail: the workspace must have an epic issue type
        epic_type = IssueType.objects.filter(
            workspace=workspace, is_epic=True
        ).first()
        if not epic_type:
            return Response(
                {"error": "No epic issue type configured for this workspace"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Inject the epic type into the request data
        data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
        data["type"] = str(epic_type.id)

        serializer = IssueSerializer(
            data=data,
            context={
                "project_id": project_id,
                "workspace_id": project.workspace_id,
                "default_assignee_id": project.default_assignee_id,
            },
        )

        if serializer.is_valid():
            if (
                request.data.get("external_id")
                and request.data.get("external_source")
                and Issue.objects.filter(
                    project_id=project_id,
                    workspace__slug=slug,
                    external_source=request.data.get("external_source"),
                    external_id=request.data.get("external_id"),
                ).exists()
            ):
                issue = Issue.objects.filter(
                    workspace__slug=slug,
                    project_id=project_id,
                    external_id=request.data.get("external_id"),
                    external_source=request.data.get("external_source"),
                ).first()
                return Response(
                    {
                        "error": "Epic with the same external id and external source already exists",
                        "id": str(issue.id),
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            serializer.save()
            # Refetch to apply created_at / created_by overrides
            issue = Issue.objects.filter(
                workspace__slug=slug,
                project_id=project_id,
                pk=serializer.data["id"],
            ).first()
            issue.created_at = request.data.get("created_at", timezone.now())
            issue.created_by_id = request.data.get("created_by", request.user.id)
            issue.save(update_fields=["created_at", "created_by"])

            # Track activity
            issue_activity.delay(
                type="issue.activity.created",
                requested_data=json.dumps(self.request.data, cls=DjangoJSONEncoder),
                actor_id=str(request.user.id),
                issue_id=str(serializer.data.get("id", None)),
                project_id=str(project_id),
                current_instance=None,
                epoch=int(timezone.now().timestamp()),
            )
            model_activity.delay(
                model_name="issue",
                model_id=str(serializer.data["id"]),
                requested_data=request.data,
                current_instance=None,
                actor_id=request.user.id,
                slug=slug,
                origin=base_host(request=request, is_app=True),
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EpicDetailAPIEndpoint(BaseAPIView):
    """Retrieve, update, and delete an epic via API key."""

    model = Issue
    webhook_event = "issue"
    permission_classes = [ProjectEntityPermission]
    serializer_class = IssueSerializer
    use_read_replica = True

    def get_queryset(self):
        return (
            Issue.issue_objects.annotate(
                sub_issues_count=Issue.issue_objects.filter(parent=OuterRef("id"))
                .order_by()
                .annotate(count=Func(F("id"), function="Count"))
                .values("count")
            )
            .filter(
                project_id=self.kwargs.get("project_id"),
                workspace__slug=self.kwargs.get("slug"),
                type__is_epic=True,
            )
            .select_related("project", "workspace", "state", "parent")
            .prefetch_related("assignees", "labels")
            .order_by(self.kwargs.get("order_by", "-created_at"))
        ).distinct()

    def get(self, request, slug, project_id, pk):
        """Retrieve a single epic."""
        assert_project_epics_enabled(slug, project_id)
        issue = (
            Issue.issue_objects.annotate(
                sub_issues_count=Issue.issue_objects.filter(parent=OuterRef("id"))
                .order_by()
                .annotate(count=Func(F("id"), function="Count"))
                .values("count")
            )
            .filter(type__is_epic=True)
            .get(workspace__slug=slug, project_id=project_id, pk=pk)
        )
        return Response(
            IssueSerializer(issue, fields=self.fields, expand=self.expand).data,
            status=status.HTTP_200_OK,
        )

    def patch(self, request, slug, project_id, pk):
        """Update an epic."""
        assert_project_epics_enabled(slug, project_id)
        # Epics cannot have a parent — reject any attempt to set one
        if request.data.get("parent") or request.data.get("parent_id"):
            return Response(
                {"error": "An epic cannot be set as a child of another issue."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        issue = Issue.objects.get(
            workspace__slug=slug,
            project_id=project_id,
            pk=pk,
            type__is_epic=True,
        )
        project = Project.objects.get(pk=project_id)
        current_instance = json.dumps(
            IssueSerializer(issue).data, cls=DjangoJSONEncoder
        )
        requested_data = json.dumps(self.request.data, cls=DjangoJSONEncoder)
        serializer = IssueSerializer(
            issue,
            data=request.data,
            context={
                "project_id": project_id,
                "workspace_id": project.workspace_id,
            },
            partial=True,
        )
        if serializer.is_valid():
            if (
                request.data.get("external_id")
                and (issue.external_id != str(request.data.get("external_id")))
                and Issue.objects.filter(
                    project_id=project_id,
                    workspace__slug=slug,
                    external_source=request.data.get(
                        "external_source", issue.external_source
                    ),
                    external_id=request.data.get("external_id"),
                ).exists()
            ):
                return Response(
                    {
                        "error": "Epic with the same external id and external source already exists",
                        "id": str(issue.id),
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            serializer.save()
            issue_activity.delay(
                type="issue.activity.updated",
                requested_data=requested_data,
                actor_id=str(request.user.id),
                issue_id=str(pk),
                project_id=str(project_id),
                current_instance=current_instance,
                epoch=int(timezone.now().timestamp()),
            )
            model_activity.delay(
                model_name="issue",
                model_id=str(pk),
                requested_data=request.data,
                current_instance=current_instance,
                actor_id=request.user.id,
                slug=slug,
                origin=base_host(request=request, is_app=True),
            )
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, slug, project_id, pk):
        """Delete an epic."""
        assert_project_epics_enabled(slug, project_id)
        issue = Issue.objects.get(
            workspace__slug=slug,
            project_id=project_id,
            pk=pk,
            type__is_epic=True,
        )
        if issue.created_by_id != request.user.id and (
            not ProjectMember.objects.filter(
                workspace__slug=slug,
                member=request.user,
                role=20,
                project_id=project_id,
                is_active=True,
            ).exists()
        ):
            return Response(
                {"error": "Only admin or creator can delete the epic"},
                status=status.HTTP_403_FORBIDDEN,
            )
        current_instance = json.dumps(
            IssueSerializer(issue).data, cls=DjangoJSONEncoder
        )
        issue.delete()
        issue_activity.delay(
            type="issue.activity.deleted",
            requested_data=json.dumps({"issue_id": str(pk)}),
            actor_id=str(request.user.id),
            issue_id=str(pk),
            project_id=str(project_id),
            current_instance=current_instance,
            epoch=int(timezone.now().timestamp()),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class EpicAnalyticsAPIEndpoint(BaseAPIView):
    """Return aggregate analytics for an epic's child work items (v1 API)."""

    permission_classes = [ProjectEntityPermission]

    def get(self, request, slug, project_id, pk):
        assert_project_epics_enabled(slug, project_id)

        # Verify the epic exists
        epic = Issue.issue_objects.filter(
            project_id=project_id,
            workspace__slug=slug,
            type__is_epic=True,
            pk=pk,
        ).first()
        if not epic:
            return Response(
                {"error": "Epic not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        children = Issue.issue_objects.filter(parent_id=pk)
        total = children.count()

        if total == 0:
            return Response(
                {
                    "total_issues": 0,
                    "completed_issues": 0,
                    "cancelled_issues": 0,
                    "started_issues": 0,
                    "unstarted_issues": 0,
                    "backlog_issues": 0,
                    "overdue_issues": 0,
                    "completion_percentage": 0,
                    "distribution": {
                        "state_group": {},
                        "priority": {},
                        "assignee": {},
                    },
                }
            )

        # State group breakdown
        state_counts = dict(
            children.values_list("state__group")
            .annotate(count=Count("id"))
            .values_list("state__group", "count")
        )

        completed = state_counts.get("completed", 0)
        cancelled = state_counts.get("cancelled", 0)
        started = state_counts.get("started", 0)
        unstarted = state_counts.get("unstarted", 0)
        backlog = state_counts.get("backlog", 0)

        # Overdue: target_date < today AND not completed/cancelled
        today = timezone.now().date()
        overdue = children.filter(
            target_date__lt=today,
        ).exclude(
            state__group__in=["completed", "cancelled"],
        ).count()

        # Completion percentage
        completion_pct = round((completed / total) * 100, 2) if total else 0

        # Priority breakdown
        priority_counts = dict(
            children.values_list("priority")
            .annotate(count=Count("id"))
            .values_list("priority", "count")
        )

        # Assignee breakdown
        assignee_rows = (
            children.filter(
                issue_assignee__deleted_at__isnull=True,
            )
            .values(assignee_id=F("issue_assignee__assignee_id"))
            .annotate(count=Count("id", distinct=True))
        )
        assignee_counts = {
            str(row["assignee_id"]): row["count"]
            for row in assignee_rows
            if row["assignee_id"] is not None
        }

        return Response(
            {
                "total_issues": total,
                "completed_issues": completed,
                "cancelled_issues": cancelled,
                "started_issues": started,
                "unstarted_issues": unstarted,
                "backlog_issues": backlog,
                "overdue_issues": overdue,
                "completion_percentage": completion_pct,
                "distribution": {
                    "state_group": state_counts,
                    "priority": priority_counts,
                    "assignee": assignee_counts,
                },
            }
        )
