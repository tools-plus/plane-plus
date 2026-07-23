# Plane Plus — Custom API v1 endpoints
# All endpoints use API key authentication (X-Api-Key header)

from django.urls import path

from .views import (
    PageListCreateAPIEndpoint,
    PageDetailAPIEndpoint,
    PageDescriptionAPIEndpoint,
    EpicListCreateAPIEndpoint,
    EpicDetailAPIEndpoint,
    EpicAnalyticsAPIEndpoint,
    WorkspacePageFolderListCreateAPIEndpoint,
    WorkspacePageFolderDetailAPIEndpoint,
    AgentDocListAPIEndpoint,
    AgentDocDetailAPIEndpoint,
)
from .views.workspace_page import (
    WorkspacePageListCreateAPIEndpoint,
    WorkspacePageDetailAPIEndpoint,
    WorkspacePageDescriptionAPIEndpoint,
)

urlpatterns = [
    # Project Pages
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/pages/",
        PageListCreateAPIEndpoint.as_view(http_method_names=["get", "post"]),
        name="iw-project-pages",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/pages/<uuid:page_id>/",
        PageDetailAPIEndpoint.as_view(http_method_names=["get", "patch", "delete"]),
        name="iw-project-page-detail",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/pages/<uuid:page_id>/description/",
        PageDescriptionAPIEndpoint.as_view(http_method_names=["get", "patch"]),
        name="iw-project-page-description",
    ),
    # Workspace Pages (Wiki)
    path(
        "workspaces/<str:slug>/pages/",
        WorkspacePageListCreateAPIEndpoint.as_view(http_method_names=["get", "post"]),
        name="iw-workspace-pages",
    ),
    path(
        "workspaces/<str:slug>/pages/<uuid:page_id>/",
        WorkspacePageDetailAPIEndpoint.as_view(http_method_names=["get", "patch", "delete"]),
        name="iw-workspace-page-detail",
    ),
    path(
        "workspaces/<str:slug>/pages/<uuid:page_id>/description/",
        WorkspacePageDescriptionAPIEndpoint.as_view(http_method_names=["patch"]),
        name="iw-workspace-page-description",
    ),
    # Workspace Wiki Page Folders
    path(
        "workspaces/<str:slug>/page-folders/",
        WorkspacePageFolderListCreateAPIEndpoint.as_view(http_method_names=["get", "post"]),
        name="iw-workspace-page-folders",
    ),
    path(
        "workspaces/<str:slug>/page-folders/<uuid:folder_id>/",
        WorkspacePageFolderDetailAPIEndpoint.as_view(http_method_names=["get", "patch", "delete"]),
        name="iw-workspace-page-folder-detail",
    ),
    # Epics
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/iw-epics/",
        EpicListCreateAPIEndpoint.as_view(http_method_names=["get", "post"]),
        name="iw-epics",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/iw-epics/<uuid:pk>/",
        EpicDetailAPIEndpoint.as_view(http_method_names=["get", "patch", "delete"]),
        name="iw-epic-detail",
    ),
    # Epic analytics
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/iw-epics/<uuid:pk>/analytics/",
        EpicAnalyticsAPIEndpoint.as_view(http_method_names=["get"]),
        name="iw-epic-analytics",
    ),
    # Agent Docs (PP-70) — workspace-level markdown notes with optimistic
    # concurrency. Path is passed as a `?path=` query string (NOT a URL
    # segment) so the route works for arbitrary nested doc paths like
    # `plans/vikrant.md` without double URL-encoding pain. This matches
    # Surya's PP-71 frontend client. Frontend renders preview client-side,
    # so there is intentionally no `/preview` endpoint here.
    path(
        "workspaces/<str:slug>/agent-docs/",
        AgentDocListAPIEndpoint.as_view(http_method_names=["get"]),
        name="iw-agent-docs",
    ),
    path(
        "workspaces/<str:slug>/agent-docs/doc/",
        AgentDocDetailAPIEndpoint.as_view(http_method_names=["get", "put", "delete"]),
        name="iw-agent-doc-detail",
    ),
]
