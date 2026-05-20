# InfraWatch — workspace AI endpoint registration in plane.app URL space
# Session-authenticated (cookie/JWT) — mirrors the v1 API key routes under /api/
# SPDX-License-Identifier: AGPL-3.0-only

from django.urls import include, path

urlpatterns = [
    path(
        "workspaces/<str:slug>/ai/",
        include("plane.ai.urls.iw_ai_workspace"),
    ),
]
