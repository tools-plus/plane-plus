# Plane Plus — Workspace Wiki Pages API (API key authenticated)
# Exposes workspace-level pages under /api/v1/ with X-Api-Key auth

import json

from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import (
    Exists,
    OuterRef,
    Q,
    Value,
    UUIDField,
)
from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.postgres.fields import ArrayField
from django.db.models.functions import Coalesce

from rest_framework import status
from rest_framework.response import Response

from plane.api.views.base import BaseAPIView
from plane.app.serializers import (
    PageSerializer,
    PageDetailSerializer,
    PageBinaryUpdateSerializer,
)
from plane.db.models import (
    Page,
    Workspace,
    UserFavorite,
    WorkspaceMember,
)
from plane.bgtasks.page_transaction_task import page_transaction
from plane.bgtasks.page_version_task import track_page_version


def _workspace_page_queryset(user, slug):
    """Shared queryset for workspace-level (global) pages."""
    subquery = UserFavorite.objects.filter(
        user=user,
        entity_type="page",
        entity_identifier=OuterRef("pk"),
        workspace__slug=slug,
    )
    return (
        Page.objects.filter(
            workspace__slug=slug,
            is_global=True,
        )
        .filter(parent__isnull=True)
        .filter(Q(owned_by=user) | Q(access=0))
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


class WorkspacePageListCreateAPIEndpoint(BaseAPIView):
    """List and create workspace wiki pages via API key."""

    def get(self, request, slug):
        queryset = _workspace_page_queryset(request.user, slug)
        serializer = PageSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)
        serializer = PageSerializer(
            data=request.data,
            context={
                "project_id": None,
                "workspace_id": workspace.id,
                "owned_by_id": request.user.id,
                "description_json": request.data.get("description_json", {}),
                "description_binary": request.data.get("description_binary", None),
                "description_html": request.data.get("description_html", "<p></p>"),
            },
        )
        if serializer.is_valid():
            serializer.save()
            page_transaction.delay(
                new_description_html=request.data.get("description_html", "<p></p>"),
                old_description_html=None,
                page_id=serializer.data["id"],
            )
            page = _workspace_page_queryset(request.user, slug).filter(pk=serializer.data["id"]).first()
            return Response(PageDetailSerializer(page).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WorkspacePageDetailAPIEndpoint(BaseAPIView):
    """Retrieve, update, and delete a workspace wiki page via API key."""

    def get(self, request, slug, page_id):
        page = _workspace_page_queryset(request.user, slug).filter(pk=page_id).first()
        if page is None:
            return Response({"error": "Page not found"}, status=status.HTTP_404_NOT_FOUND)

        data = PageDetailSerializer(page).data

        # Support ?response_format=markdown (not "format" — DRF reserves that for content negotiation)
        if request.query_params.get("response_format") == "markdown" and data.get("description_html"):
            from plane.utils.markdown import html_to_markdown
            data["description_markdown"] = html_to_markdown(data["description_html"])

        return Response(data, status=status.HTTP_200_OK)

    def patch(self, request, slug, page_id):
        try:
            page = Page.objects.get(
                pk=page_id,
                workspace__slug=slug,
                is_global=True,
            )
        except Page.DoesNotExist:
            return Response({"error": "Page not found"}, status=status.HTTP_404_NOT_FOUND)

        if page.is_locked:
            return Response({"error": "Page is locked"}, status=status.HTTP_400_BAD_REQUEST)

        if page.access != request.data.get("access", page.access) and page.owned_by_id != request.user.id:
            return Response(
                {"error": "Access cannot be updated since this page is owned by someone else"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        page_description = page.description_html
        serializer = PageDetailSerializer(page, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            if request.data.get("description_html"):
                page_transaction.delay(
                    new_description_html=request.data.get("description_html", "<p></p>"),
                    old_description_html=page_description,
                    page_id=page_id,
                )
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, slug, page_id):
        try:
            page = Page.objects.get(
                pk=page_id,
                workspace__slug=slug,
                is_global=True,
            )
        except Page.DoesNotExist:
            return Response({"error": "Page not found"}, status=status.HTTP_404_NOT_FOUND)

        if page.owned_by_id != request.user.id and not WorkspaceMember.objects.filter(
            workspace__slug=slug,
            member=request.user,
            role=20,
            is_active=True,
        ).exists():
            return Response(
                {"error": "Only admin or owner can delete the page"},
                status=status.HTTP_403_FORBIDDEN,
            )

        Page.objects.filter(
            parent_id=page_id,
            workspace__slug=slug,
            is_global=True,
        ).update(parent=None)

        page.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WorkspacePageDescriptionAPIEndpoint(BaseAPIView):
    """Get and update workspace page description via API key."""

    def patch(self, request, slug, page_id):
        try:
            page = Page.objects.get(
                Q(owned_by=request.user) | Q(access=0),
                pk=page_id,
                workspace__slug=slug,
                is_global=True,
            )
        except Page.DoesNotExist:
            return Response({"error": "Page not found"}, status=status.HTTP_404_NOT_FOUND)

        if page.is_locked:
            return Response({"error": "Page is locked"}, status=status.HTTP_400_BAD_REQUEST)

        if page.archived_at:
            return Response({"error": "Page is archived"}, status=status.HTTP_400_BAD_REQUEST)

        old_description_html = page.description_html
        existing_instance = json.dumps(
            {"description_html": old_description_html}, cls=DjangoJSONEncoder
        )

        # When only HTML is provided (API usage), clear binary and json
        data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
        if "description_html" in data and "description_binary" not in data:
            page.description_binary = None
            page.description_json = {}

        serializer = PageBinaryUpdateSerializer(page, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            if data.get("description_html"):
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
