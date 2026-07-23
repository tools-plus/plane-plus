# Plane Plus — Agent Docs URL patterns (session-authenticated).
#
# Mirror of plane.iw.urls' agent-doc routes, but mounted under /api/ so the
# session-auth web UI can reach them with cookies (the X-Api-Key versions
# stay at /api/v1/ for the SDK / MCP / migration scripts).

from django.urls import path

from plane.app.views.iw_agent_doc import (
    AgentDocListAPIEndpoint,
    AgentDocDetailAPIEndpoint,
)


urlpatterns = [
    # List doc summaries under an optional ?prefix= and/or ?q=
    path(
        "workspaces/<str:slug>/agent-docs/",
        AgentDocListAPIEndpoint.as_view(http_method_names=["get"]),
        name="iw-agent-docs",
    ),
    # Per-doc CRUD. Path comes through as ?path=<full/path.md> — see the
    # rationale in plane.iw.views.agent_doc.
    path(
        "workspaces/<str:slug>/agent-docs/doc/",
        AgentDocDetailAPIEndpoint.as_view(http_method_names=["get", "put", "delete"]),
        name="iw-agent-doc-detail",
    ),
]
