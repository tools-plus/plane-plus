# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Plane Plus — Epic URL patterns

from django.urls import path

from plane.app.views import (
    IwEpicViewSet,
    IwEpicListEndpoint,
    IwEpicSubIssuesEndpoint,
    IwEpicActivityEndpoint,
    IwEpicAttachmentEndpoint,
    IwEpicAttachmentV2Endpoint,
    IwEpicCommentViewSet,
    IwEpicLinkViewSet,
    IwEpicReactionViewSet,
    IwEpicUserDisplayPropertyEndpoint,
)

urlpatterns = [
    # Epic list (paginated)
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/epics/",
        IwEpicViewSet.as_view({"get": "list", "post": "create"}),
        name="project-epics",
    ),
    # Epic detail
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/epics/<uuid:pk>/",
        IwEpicViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="project-epics-detail",
    ),
    # Epic analytics
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/epics/<uuid:pk>/analytics/",
        IwEpicViewSet.as_view({"get": "analytics"}),
        name="project-epics-analytics",
    ),
    # Epic list (non-paginated)
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/epics/list/",
        IwEpicListEndpoint.as_view(),
        name="project-epics-list",
    ),
    # Epic sub-issues (child work items)
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/epics/<uuid:issue_id>/sub-issues/",
        IwEpicSubIssuesEndpoint.as_view(),
        name="project-epics-sub-issues",
    ),
    # Epic activity/history
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/epics/<uuid:issue_id>/history/",
        IwEpicActivityEndpoint.as_view(),
        name="project-epic-history",
    ),
    # Epic child work items (issues parented to this epic)
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/epics/<uuid:issue_id>/issues/",
        IwEpicSubIssuesEndpoint.as_view(),
        name="project-epic-issues",
    ),
    # Epic comments
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/epics/<uuid:issue_id>/comments/",
        IwEpicCommentViewSet.as_view({"get": "list", "post": "create"}),
        name="project-epic-comments",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/epics/<uuid:issue_id>/comments/<uuid:pk>/",
        IwEpicCommentViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="project-epic-comment-detail",
    ),
    # Epic reactions
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/epics/<uuid:issue_id>/reactions/",
        IwEpicReactionViewSet.as_view({"get": "list", "post": "create"}),
        name="project-epic-reactions",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/epics/<uuid:issue_id>/reactions/<str:reaction_code>/",
        IwEpicReactionViewSet.as_view({"delete": "destroy"}),
        name="project-epic-reaction-delete",
    ),
    # Comment reactions (shared — comments have their own IDs, not scoped to epics)
    # Note: comment reactions use /comments/<id>/reactions/ which is already defined globally
    # Epic links
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/epics/<uuid:issue_id>/issue-links/",
        IwEpicLinkViewSet.as_view({"get": "list", "post": "create"}),
        name="project-epic-links",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/epics/<uuid:issue_id>/issue-links/<uuid:pk>/",
        IwEpicLinkViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="project-epic-link-detail",
    ),
    # Epic attachments
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/epics/<uuid:issue_id>/issue-attachments/",
        IwEpicAttachmentEndpoint.as_view(),
        name="project-epic-attachments",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/epics/<uuid:issue_id>/issue-attachments/<uuid:pk>/",
        IwEpicAttachmentEndpoint.as_view(),
        name="project-epic-attachment-detail",
    ),
    # Epic attachments v2
    path(
        "assets/v2/workspaces/<str:slug>/projects/<uuid:project_id>/epics/<uuid:issue_id>/attachments/",
        IwEpicAttachmentV2Endpoint.as_view(),
        name="project-epic-attachments-v2",
    ),
    path(
        "assets/v2/workspaces/<str:slug>/projects/<uuid:project_id>/epics/<uuid:issue_id>/attachments/<uuid:pk>/",
        IwEpicAttachmentV2Endpoint.as_view(),
        name="project-epic-attachment-v2-detail",
    ),
    # Epic user display properties
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/epics-user-properties/",
        IwEpicUserDisplayPropertyEndpoint.as_view(),
        name="project-epics-user-properties",
    ),
    # v2 epic list (cursor-based pagination)
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/v2/epics/",
        IwEpicViewSet.as_view({"get": "v2_list"}),
        name="project-epics-v2",
    ),
    # Epic detail (extended)
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/epics-detail/",
        IwEpicViewSet.as_view({"get": "retrieve_list"}),
        name="project-epics-detail-list",
    ),
]
