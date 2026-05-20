# InfraWatch — Workspace AI URL registration
# SPDX-License-Identifier: AGPL-3.0-only
#
# Mounts all workspace AI endpoints under /api/v1/workspaces/<slug>/ai/

from django.urls import include, path

urlpatterns = [
    path(
        "workspaces/<str:slug>/ai/",
        include("plane.ai.urls.workspace"),
    ),
]
