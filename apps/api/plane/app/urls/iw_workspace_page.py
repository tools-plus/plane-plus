# Plane Plus-specific URL patterns — isolated to avoid upstream merge conflicts.

from django.urls import path

from plane.app.views import WorkspacePageViewSet

urlpatterns = [
    # Workspace-level pages (is_global=True)
    path(
        "workspaces/<str:slug>/pages/",
        WorkspacePageViewSet.as_view({"get": "list", "post": "create"}),
        name="workspace-pages",
    ),
    path(
        "workspaces/<str:slug>/pages/<uuid:page_id>/",
        WorkspacePageViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="workspace-pages-detail",
    ),
    path(
        "workspaces/<str:slug>/pages/<uuid:page_id>/description/",
        WorkspacePageViewSet.as_view(
            {"get": "description_retrieve", "patch": "description_partial_update"}
        ),
        name="workspace-pages-description",
    ),
    path(
        "workspaces/<str:slug>/pages/<uuid:page_id>/lock/",
        WorkspacePageViewSet.as_view({"post": "lock", "delete": "unlock"}),
        name="workspace-pages-lock",
    ),
    path(
        "workspaces/<str:slug>/pages/<uuid:page_id>/archive/",
        WorkspacePageViewSet.as_view({"post": "archive", "delete": "unarchive"}),
        name="workspace-pages-archive",
    ),
    path(
        "workspaces/<str:slug>/pages/<uuid:page_id>/access/",
        WorkspacePageViewSet.as_view({"post": "access"}),
        name="workspace-pages-access",
    ),
]
