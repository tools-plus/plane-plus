# Plane Plus — Workspace Wiki Page Folders API (API key authenticated)
# Exposes workspace-level page folders under /api/v1/ with X-Api-Key auth.
#
# The internal app already has a PageFolderViewSet for cookie/JWT clients.
# This module mirrors it as APIView-based endpoints consistent with the rest
# of plane/iw/views/ so agents can create and manage wiki folders with an
# API key — needed for the "Wiki as Agent Plan Store" pattern where agents
# organize their plan pages under `Wiki > agents > plans`.

from rest_framework import status
from rest_framework.response import Response

from plane.api.views.base import BaseAPIView
from plane.app.serializers import PageFolderSerializer
from plane.db.models import PageFolder, Workspace


class WorkspacePageFolderListCreateAPIEndpoint(BaseAPIView):
    """List and create workspace page folders via API key."""

    def get(self, request, slug):
        queryset = (
            PageFolder.objects.filter(workspace__slug=slug)
            .select_related("workspace", "parent_folder")
            .prefetch_related("children")
        )
        serializer = PageFolderSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, slug):
        try:
            workspace = Workspace.objects.get(slug=slug)
        except Workspace.DoesNotExist:
            return Response(
                {"error": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = PageFolderSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(workspace=workspace)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WorkspacePageFolderDetailAPIEndpoint(BaseAPIView):
    """Retrieve, update, and delete a workspace page folder via API key."""

    def get(self, request, slug, folder_id):
        folder = (
            PageFolder.objects.filter(pk=folder_id, workspace__slug=slug)
            .select_related("workspace", "parent_folder")
            .prefetch_related("children")
            .first()
        )
        if folder is None:
            return Response(
                {"error": "Folder not found"}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(PageFolderSerializer(folder).data, status=status.HTTP_200_OK)

    def patch(self, request, slug, folder_id):
        try:
            folder = PageFolder.objects.get(pk=folder_id, workspace__slug=slug)
        except PageFolder.DoesNotExist:
            return Response(
                {"error": "Folder not found"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = PageFolderSerializer(folder, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, slug, folder_id):
        try:
            folder = PageFolder.objects.get(pk=folder_id, workspace__slug=slug)
        except PageFolder.DoesNotExist:
            return Response(
                {"error": "Folder not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Promote child folders to the deleted folder's parent.
        PageFolder.objects.filter(parent_folder=folder).update(
            parent_folder=folder.parent_folder
        )

        # Unset folder on pages in this folder (move them to root).
        folder.pages.update(folder=None)

        folder.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
