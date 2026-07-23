# Plane Plus — Agent Docs API (session-authenticated mirror).
#
# Same logic as plane.iw.views.agent_doc — only the auth surface differs:
#   - plane.iw.views.agent_doc → /api/v1/...   (X-Api-Key, for SDK / MCP / scripts)
#   - this module               → /api/...      (session cookie, for the web UI)
#
# We mix the API-key endpoints' methods into a session-auth base so the
# read+compare+write logic, validation, and error shapes can never drift
# between the two transports. PP-71 (Surya, frontend) calls this mirror;
# PP-70 / PP-72 (SDK + migration script) hit the X-Api-Key surface.
#
# Permission rule for v1: any active workspace member can list / read /
# write / delete. Tighten if/when MGupta wants per-doc ownership semantics.

from plane.app.views.base import BaseAPIView
from plane.app.permissions import WorkspaceUserPermission
from plane.iw.views.agent_doc import (
    AgentDocListAPIEndpoint as _IwListAPIEndpoint,
    AgentDocDetailAPIEndpoint as _IwDetailAPIEndpoint,
)


class AgentDocListAPIEndpoint(BaseAPIView):
    """GET /api/workspaces/<slug>/agent-docs/?prefix=&q=

    Session-authenticated wrapper around plane.iw.views.agent_doc.
    """

    permission_classes = [WorkspaceUserPermission]

    def get(self, request, slug):
        return _IwListAPIEndpoint.get(self, request, slug)


class AgentDocDetailAPIEndpoint(BaseAPIView):
    """GET / PUT / DELETE /api/workspaces/<slug>/agent-docs/doc/?path=<path>

    Session-authenticated wrapper around plane.iw.views.agent_doc.
    """

    permission_classes = [WorkspaceUserPermission]

    # Reuse helpers verbatim — they only touch request, never auth state.
    # Class-attribute access on _IwDetailAPIEndpoint already unwraps the
    # staticmethod descriptor into the underlying function, so we re-wrap
    # in staticmethod() to keep the same semantics on the mirror class.
    _read_path = _IwDetailAPIEndpoint._read_path
    _serialize_full = staticmethod(_IwDetailAPIEndpoint._serialize_full)

    def get(self, request, slug):
        return _IwDetailAPIEndpoint.get(self, request, slug)

    def put(self, request, slug):
        return _IwDetailAPIEndpoint.put(self, request, slug)

    def delete(self, request, slug):
        return _IwDetailAPIEndpoint.delete(self, request, slug)
