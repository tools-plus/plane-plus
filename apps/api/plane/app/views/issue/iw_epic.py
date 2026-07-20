# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# InfraWatch — Epic-specific views
# Epics are issues with type.is_epic=True

from collections import defaultdict

from django.db import transaction
from django.db.models import Count, F, Q
from django.utils import timezone

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from plane.app.permissions import ROLE, allow_permission
from plane.db.models import Issue, IssueType, Workspace
from plane.iw.gating import assert_project_epics_enabled

from .activity import IssueActivityEndpoint
from .attachment import IssueAttachmentEndpoint, IssueAttachmentV2Endpoint
from .base import IssueViewSet, IssueListEndpoint, ProjectUserDisplayPropertyEndpoint
from .comment import IssueCommentViewSet
from .link import IssueLinkViewSet
from .reaction import IssueReactionViewSet
from .sub_issue import SubIssuesEndpoint


class IwEpicViewSet(IssueViewSet):
    """
    ViewSet for epics — issues whose type has is_epic=True.
    Inherits all behaviour from IssueViewSet but:
    - Scopes queryset to epic-typed issues only
    - Auto-sets type_id on create
    - Gates every action behind the project's "Epics" toggle (PP-85)
    """

    def get_queryset(self):
        return Issue.issue_objects.filter(
            project_id=self.kwargs.get("project_id"),
            workspace__slug=self.kwargs.get("slug"),
            type__is_epic=True,
        ).distinct()

    def list(self, request, slug, project_id):
        assert_project_epics_enabled(slug, project_id)
        # NOTE: allow_permission (on the parent's list()) reads slug/project_id
        # out of kwargs, so these must be passed as keywords, not positionals.
        return super().list(request, slug=slug, project_id=project_id)

    def retrieve(self, request, slug, project_id, pk=None):
        assert_project_epics_enabled(slug, project_id)
        return super().retrieve(request, slug=slug, project_id=project_id, pk=pk)

    def partial_update(self, request, slug, project_id, pk=None):
        assert_project_epics_enabled(slug, project_id)
        return super().partial_update(request, slug=slug, project_id=project_id, pk=pk)

    def destroy(self, request, slug, project_id, pk=None):
        assert_project_epics_enabled(slug, project_id)
        return super().destroy(request, slug=slug, project_id=project_id, pk=pk)

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def create(self, request, slug, project_id):
        assert_project_epics_enabled(slug, project_id)

        workspace = Workspace.objects.get(slug=slug)
        epic_type = IssueType.objects.filter(
            workspace=workspace, is_epic=True
        ).first()
        if not epic_type:
            # Safety net: with PP-85 provisioning (plane.iw.signals /
            # plane.iw.provisioning) this should be unreachable whenever
            # epics are enabled, but fail clean instead of creating a
            # typeless issue if it's somehow still missing. Mirrors the same
            # guard in plane.iw.views.epic.EpicListCreateAPIEndpoint.post.
            return Response(
                {"error": "No epic issue type configured for this workspace"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # request.data may be a plain dict (JSON) or a QueryDict (form)
        if hasattr(request.data, "_mutable"):
            request.data._mutable = True
            request.data["type"] = str(epic_type.id)
            request.data._mutable = False
        else:
            request.data["type"] = str(epic_type.id)

        with transaction.atomic():
            return super().create(request, slug=slug, project_id=project_id)

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def analytics(self, request, slug, project_id, pk):
        """Return aggregate analytics for an epic's child work items."""
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

        # Completion percentage (only completed, excludes cancelled)
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


class IwEpicListEndpoint(IssueListEndpoint):
    """
    Non-paginated epic list endpoint.
    """

    def get_queryset(self):
        return Issue.issue_objects.filter(
            project_id=self.kwargs.get("project_id"),
            workspace__slug=self.kwargs.get("slug"),
            type__is_epic=True,
        ).distinct()

    def get(self, request, slug, project_id):
        assert_project_epics_enabled(slug, project_id)
        # NOTE: allow_permission (on IssueListEndpoint.get) reads slug/project_id
        # out of kwargs, so these must be passed as keywords, not positionals.
        return super().get(request, slug=slug, project_id=project_id)


class IwEpicSubIssuesEndpoint(SubIssuesEndpoint):
    """
    Same as SubIssuesEndpoint, gated behind the project's "Epics" toggle
    (PP-85). Mounted under the /epics/ URL prefix for both the epic
    "sub-issues" and epic "issues" (child work item) routes — see
    plane.app.urls.iw_epic.
    """

    def get(self, request, slug, project_id, issue_id):
        assert_project_epics_enabled(slug, project_id)
        return super().get(request, slug=slug, project_id=project_id, issue_id=issue_id)

    def post(self, request, slug, project_id, issue_id):
        assert_project_epics_enabled(slug, project_id)
        return super().post(request, slug=slug, project_id=project_id, issue_id=issue_id)


class IwEpicActivityEndpoint(IssueActivityEndpoint):
    """
    Same as IssueActivityEndpoint, gated behind the project's "Epics" toggle
    (PP-85). Mounted under the /epics/.../history/ route — see
    plane.app.urls.iw_epic.
    """

    def get(self, request, slug, project_id, issue_id):
        assert_project_epics_enabled(slug, project_id)
        # NOTE: allow_permission (on IssueActivityEndpoint.get) reads
        # slug/project_id out of kwargs, so these must be passed as keywords.
        return super().get(request, slug=slug, project_id=project_id, issue_id=issue_id)


class _EpicSubResourceGateMixin:
    """
    Shared gate for epic sub-resource routes (comments, reactions, links,
    attachments, user-properties) mounted under the /epics/ URL prefix (PP-85).

    Unlike IwEpicSubIssuesEndpoint/IwEpicActivityEndpoint (which gate inside
    each handler), these mixins gate via `initial()` — DRF calls `initial()`
    once per request, after authentication/permission checks but before any
    action/handler method runs, for both `ModelViewSet` actions dispatched
    through `.as_view({...})` and plain `APIView` methods alike. That gives a
    single choke point that covers every HTTP method/action mapped to these
    shared upstream views without having to override each one (list, create,
    retrieve, update, partial_update, destroy, get, post, patch, delete, ...),
    guaranteeing no write happens before the gate is checked.
    """

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        assert_project_epics_enabled(self.kwargs.get("slug"), self.kwargs.get("project_id"))


class IwEpicCommentViewSet(_EpicSubResourceGateMixin, IssueCommentViewSet):
    """
    Same as IssueCommentViewSet, gated behind the project's "Epics" toggle
    (PP-85). Mounted under the /epics/.../comments/ routes — see
    plane.app.urls.iw_epic.
    """


class IwEpicReactionViewSet(_EpicSubResourceGateMixin, IssueReactionViewSet):
    """
    Same as IssueReactionViewSet, gated behind the project's "Epics" toggle
    (PP-85). Mounted under the /epics/.../reactions/ routes — see
    plane.app.urls.iw_epic.
    """


class IwEpicLinkViewSet(_EpicSubResourceGateMixin, IssueLinkViewSet):
    """
    Same as IssueLinkViewSet, gated behind the project's "Epics" toggle
    (PP-85). Mounted under the /epics/.../issue-links/ routes — see
    plane.app.urls.iw_epic.
    """


class IwEpicAttachmentEndpoint(_EpicSubResourceGateMixin, IssueAttachmentEndpoint):
    """
    Same as IssueAttachmentEndpoint, gated behind the project's "Epics"
    toggle (PP-85). Mounted under the /epics/.../issue-attachments/ routes —
    see plane.app.urls.iw_epic.
    """


class IwEpicAttachmentV2Endpoint(_EpicSubResourceGateMixin, IssueAttachmentV2Endpoint):
    """
    Same as IssueAttachmentV2Endpoint, gated behind the project's "Epics"
    toggle (PP-85). Mounted under the /epics/.../attachments/ (v2) routes —
    see plane.app.urls.iw_epic.
    """


class IwEpicUserDisplayPropertyEndpoint(_EpicSubResourceGateMixin, ProjectUserDisplayPropertyEndpoint):
    """
    Same as ProjectUserDisplayPropertyEndpoint, gated behind the project's
    "Epics" toggle (PP-85). Mounted under the /epics-user-properties/ route —
    see plane.app.urls.iw_epic.
    """
