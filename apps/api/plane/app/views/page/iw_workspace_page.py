# Plane Plus-specific views — isolated to avoid upstream merge conflicts.

# Python imports
import json
from datetime import datetime
from django.core.serializers.json import DjangoJSONEncoder

# Django imports
from django.db.models import (
    Exists,
    OuterRef,
    Q,
    Value,
    UUIDField,
)
from django.http import StreamingHttpResponse
from django.contrib.postgres.fields import ArrayField
from django.db.models.functions import Coalesce
from django.contrib.postgres.aggregates import ArrayAgg

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.app.serializers import (
    PageSerializer,
    PageDetailSerializer,
    PageBinaryUpdateSerializer,
)
from plane.db.models import (
    Page,
    UserFavorite,
    UserRecentVisit,
    Workspace,
    WorkspaceMember,
)
from plane.utils.error_codes import ERROR_CODES

# Local imports
from ..base import BaseViewSet
from plane.bgtasks.page_transaction_task import page_transaction
from plane.bgtasks.page_version_task import track_page_version
from plane.app.permissions import WorkspacePagePermission


class WorkspacePageViewSet(BaseViewSet):
    """
    CRUD ViewSet for workspace-level pages (is_global=True).
    Endpoint: /api/v1/workspaces/{slug}/pages/
    """

    serializer_class = PageSerializer
    model = Page
    permission_classes = [WorkspacePagePermission]
    search_fields = ["name"]

    def get_queryset(self):
        subquery = UserFavorite.objects.filter(
            user=self.request.user,
            entity_type="page",
            entity_identifier=OuterRef("pk"),
            workspace__slug=self.kwargs.get("slug"),
        )
        return (
            self.filter_queryset(
                super()
                .get_queryset()
                .filter(
                    workspace__slug=self.kwargs.get("slug"),
                    is_global=True,
                )
                .filter(parent__isnull=True)
                .filter(Q(owned_by=self.request.user) | Q(access=0))
                .select_related("workspace", "owned_by")
                .prefetch_related("labels")
                .annotate(is_favorite=Exists(subquery))
                .annotate(
                    label_ids=Coalesce(
                        ArrayAgg(
                            "page_labels__label_id",
                            distinct=True,
                            filter=~Q(page_labels__label_id__isnull=True),
                        ),
                        Value([], output_field=ArrayField(UUIDField())),
                    ),
                    project_ids=Coalesce(
                        ArrayAgg(
                            "projects__id",
                            distinct=True,
                            filter=~Q(projects__id=True),
                        ),
                        Value([], output_field=ArrayField(UUIDField())),
                    ),
                )
                .order_by("-is_favorite", "-created_at")
                .distinct()
            )
        )

    def list(self, request, slug):
        queryset = self.get_queryset()
        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(description_html__icontains=search)
            )
        pages = PageSerializer(queryset, many=True).data
        return Response(pages, status=status.HTTP_200_OK)

    def create(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)

        serializer = PageSerializer(
            data=request.data,
            context={
                "project_id": None,
                "workspace_id": workspace.id,
                "owned_by_id": request.user.id,
                "description_json": request.data.get("description_json", {}),
                "description_binary": request.data.get(
                    "description_binary", None
                ),
                "description_html": request.data.get(
                    "description_html", "<p></p>"
                ),
            },
        )

        if serializer.is_valid():
            serializer.save()
            # Capture the page transaction
            page_transaction.delay(
                new_description_html=request.data.get(
                    "description_html", "<p></p>"
                ),
                old_description_html=None,
                page_id=serializer.data["id"],
            )
            page = self.get_queryset().get(pk=serializer.data["id"])
            serializer = PageDetailSerializer(page)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, slug, page_id=None):
        page = self.get_queryset().filter(pk=page_id).first()

        if page is None:
            return Response(
                {"error": "Page not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = PageDetailSerializer(page).data

        # Convert description_html to markdown if requested
        response_format = request.query_params.get("response_format", "html").lower()
        if response_format == "markdown" and data.get("description_html"):
            from plane.utils.markdown import html_to_markdown
            data["description_markdown"] = html_to_markdown(data["description_html"])

        return Response(data, status=status.HTTP_200_OK)

    def partial_update(self, request, slug, page_id):
        try:
            page = Page.objects.get(
                pk=page_id,
                workspace__slug=slug,
                is_global=True,
            )

            if page.is_locked:
                return Response(
                    {"error": "Page is locked"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Only update access if the page owner is the requesting user
            if (
                page.access != request.data.get("access", page.access)
                and page.owned_by_id != request.user.id
            ):
                return Response(
                    {
                        "error": "Access cannot be updated since "
                        "this page is owned by someone else"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            serializer = PageDetailSerializer(
                page, data=request.data, partial=True
            )
            page_description = page.description_html
            if serializer.is_valid():
                serializer.save()
                # Capture the page transaction
                if request.data.get("description_html"):
                    page_transaction.delay(
                        new_description_html=request.data.get(
                            "description_html", "<p></p>"
                        ),
                        old_description_html=page_description,
                        page_id=page_id,
                    )
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )
        except Page.DoesNotExist:
            return Response(
                {"error": "Page not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

    def destroy(self, request, slug, page_id):
        page = Page.objects.get(
            pk=page_id,
            workspace__slug=slug,
            is_global=True,
        )

        # Only page owner or workspace admin can delete
        # (permission class already checks this, but double-check)
        if page.owned_by_id != request.user.id and not WorkspaceMember.objects.filter(
            workspace__slug=slug,
            member=request.user,
            role=20,  # Admin
            is_active=True,
        ).exists():
            return Response(
                {"error": "Only admin or owner can delete the page"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Remove parent from children
        Page.objects.filter(
            parent_id=page_id,
            workspace__slug=slug,
            is_global=True,
        ).update(parent=None)

        page.delete()

        # Clean up favorites
        UserFavorite.objects.filter(
            workspace__slug=slug,
            entity_identifier=page_id,
            entity_type="page",
        ).delete()

        # Clean up recent visits
        UserRecentVisit.objects.filter(
            workspace__slug=slug,
            entity_identifier=page_id,
            entity_name="page",
        ).delete(soft=False)

    # ── Description (binary) ────────────────────────────────
    def description_retrieve(self, request, slug, page_id):
        page = Page.objects.get(
            Q(owned_by=self.request.user) | Q(access=0),
            pk=page_id,
            workspace__slug=slug,
            is_global=True,
        )
        binary_data = page.description_binary

        def stream_data():
            if binary_data:
                yield binary_data
            else:
                yield b""

        response = StreamingHttpResponse(
            stream_data(), content_type="application/octet-stream"
        )
        response["Content-Disposition"] = (
            'attachment; filename="page_description.bin"'
        )
        return response

    def description_partial_update(self, request, slug, page_id):
        page = Page.objects.get(
            Q(owned_by=self.request.user) | Q(access=0),
            pk=page_id,
            workspace__slug=slug,
            is_global=True,
        )

        if page.is_locked:
            return Response(
                {"error_code": ERROR_CODES["PAGE_LOCKED"], "error_message": "PAGE_LOCKED"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if page.archived_at:
            return Response(
                {"error_code": ERROR_CODES["PAGE_ARCHIVED"], "error_message": "PAGE_ARCHIVED"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_description_html = page.description_html
        existing_instance = json.dumps(
            {"description_html": old_description_html}, cls=DjangoJSONEncoder
        )

        serializer = PageBinaryUpdateSerializer(page, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            if request.data.get("description_html"):
                page_transaction.delay(
                    new_description_html=request.data.get("description_html", "<p></p>"),
                    old_description_html=old_description_html,
                    page_id=page_id,
                )
            track_page_version.delay(
                page_id=page_id,
                existing_instance=existing_instance,
                user_id=request.user.id,
            )
            return Response({"message": "Updated successfully"})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # ── Lock / Unlock ───────────────────────────────────────
    def lock(self, request, slug, page_id):
        page = Page.objects.get(
            pk=page_id, workspace__slug=slug, is_global=True
        )
        page.is_locked = True
        page.save(update_fields=["is_locked"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    def unlock(self, request, slug, page_id):
        page = Page.objects.get(
            pk=page_id, workspace__slug=slug, is_global=True
        )
        page.is_locked = False
        page.save(update_fields=["is_locked"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ── Archive / Restore ───────────────────────────────────
    def archive(self, request, slug, page_id):
        page = Page.objects.get(
            pk=page_id, workspace__slug=slug, is_global=True
        )
        page.archived_at = datetime.now()
        page.save(update_fields=["archived_at"])
        return Response(
            {"archived_at": str(page.archived_at)},
            status=status.HTTP_200_OK,
        )

    def unarchive(self, request, slug, page_id):
        page = Page.objects.get(
            pk=page_id, workspace__slug=slug, is_global=True
        )
        page.archived_at = None
        page.save(update_fields=["archived_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ── Access ──────────────────────────────────────────────
    def access(self, request, slug, page_id):
        page = Page.objects.get(
            pk=page_id, workspace__slug=slug, is_global=True
        )
        if page.owned_by_id != request.user.id:
            return Response(
                {"error": "Only the owner can change access"},
                status=status.HTTP_403_FORBIDDEN,
            )
        page.access = request.data.get("access", 0)
        page.save(update_fields=["access"])
        return Response(status=status.HTTP_204_NO_CONTENT)
