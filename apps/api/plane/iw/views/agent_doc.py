# Plane Plus — Agent Docs API (API key authenticated)
#
# Workspace-level markdown notes with optimistic-concurrency single-writer
# semantics. The interface shape mirrors `tools/obsidian/vault.py` so the
# follow-up tooling refactor (PP-73) is a transport-only swap — same
# `get_text(path)`, `put_text(path, content)`, `list_dir(path)`, `delete(path)`
# verbs map cleanly onto these endpoints.
#
# URL shape (adopted from Surya's PP-71 frontend contract):
#   GET    /api/v1/workspaces/<slug>/agent-docs/?prefix=<optional>&q=<optional>
#   GET    /api/v1/workspaces/<slug>/agent-docs/doc/?path=<full/path.md>
#   PUT    /api/v1/workspaces/<slug>/agent-docs/doc/?path=<full/path.md>
#   DELETE /api/v1/workspaces/<slug>/agent-docs/doc/?path=<full/path.md>
#
# Path is passed as a query string, not a URL segment, to avoid double
# URL-encoding paths-with-slashes and to match Plane's existing routing
# convention which uses UUIDs in the URL path, never arbitrary strings.
#
# Concurrency contract (see PP-70 spec):
#   - GET returns body + `ETag: "<version>"` header.
#   - PUT requires `If-Match: "<version>"` to update an existing doc; missing
#     If-Match is treated as create-only (412 if the doc already exists).
#   - DELETE also requires `If-Match` for symmetry — single-writer story is
#     the same for deletes.
#   - The read+compare+write happens inside a transaction with
#     `select_for_update()` so concurrent PUTs against the same prior version
#     can't both win. One commits, the other sees the bumped version on its
#     next read inside the txn and returns 409.
#
# Response body conventions:
#   - Errors use the DRF-standard `{"detail": "<msg>"}` shape.
#   - 409 conflicts additionally carry `server_version: <int>` so the UI can
#     show the user "your version was N+1" without a follow-up GET.
#   - List response wraps the array as `{"docs": [...]}` so we can add
#     pagination/cursor fields later without a breaking change.

import re

from django.db import transaction
from rest_framework import status
from rest_framework.response import Response

from plane.api.views.base import BaseAPIView
from plane.db.models import AgentDoc, Workspace


# ----------------------------------------------------------- path validation --

# v1 only allows .md. Folder structure is encoded in the path itself.
# - Letters, digits, dots, underscores, hyphens, forward slashes.
# - Must end in `.md` (case-sensitive — keep it boring).
# - No leading slash, no `..`, no double slashes.
# - Max 256 chars (matches the column).
_PATH_RE = re.compile(r"^[a-zA-Z0-9._\-/]+\.md$")
_MAX_PATH_LEN = 256


def _validate_path(path: str) -> str | None:
    """Return an error message if the path is invalid, else None.

    Centralised so list-by-prefix and per-doc endpoints reject the same set
    of inputs identically.
    """
    if not path or len(path) > _MAX_PATH_LEN:
        return f"path must be 1..{_MAX_PATH_LEN} chars"
    if path.startswith("/"):
        return "path must not start with /"
    if not path.endswith(".md"):
        return "path must end with .md"
    if ".." in path.split("/"):
        return "path must not contain .. segments"
    if "//" in path:
        return "path must not contain // (empty segments)"
    if not _PATH_RE.match(path):
        return "path must match ^[a-zA-Z0-9._\\-/]+\\.md$"
    return None


def _validate_prefix(prefix: str) -> str | None:
    """Prefix is more permissive than a full path — it doesn't need .md and
    can be empty or a directory-style string. We still reject the obvious
    abuse vectors."""
    if len(prefix) > _MAX_PATH_LEN:
        return f"prefix must be <= {_MAX_PATH_LEN} chars"
    if prefix.startswith("/"):
        return "prefix must not start with /"
    if ".." in prefix.split("/"):
        return "prefix must not contain .. segments"
    if "//" in prefix:
        return "prefix must not contain //"
    # Only the character class — no `.md` requirement.
    if not re.match(r"^[a-zA-Z0-9._\-/]*$", prefix):
        return "prefix must match ^[a-zA-Z0-9._\\-/]*$"
    return None


# ------------------------------------------------------- If-Match parsing --


def _parse_if_match(header_value: str | None) -> int | None:
    """Parse an `If-Match: "<n>"` header into the integer version, or None.

    Accepts both quoted ("12") and unquoted (12) forms — agents writing the
    client are likely to be sloppy about quoting, and rejecting a write
    purely on quote style would be infuriating to debug. Returns None if the
    header is missing or unparseable; callers decide whether None means
    "create-only" (PUT) or "fail" (DELETE).
    """
    if not header_value:
        return None
    v = header_value.strip().strip('"').strip()
    if v == "*":
        # `If-Match: *` is RFC-7232 for "any current version" — we honour it
        # to mean "force write, don't care about version". Matches what
        # `tools/obsidian/vault.py` effectively does today (no version check).
        return -1
    try:
        return int(v)
    except ValueError:
        return None


def _etag(version: int) -> str:
    """Format a version as an HTTP ETag value (always quoted)."""
    return f'"{version}"'


def _err400(detail: str) -> Response:
    return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)


# -------------------------------------------------------------- endpoints --


class AgentDocListAPIEndpoint(BaseAPIView):
    """GET /api/v1/workspaces/<slug>/agent-docs/?prefix=<path>&q=<query>

    List doc summaries (no body). Optional `?prefix=` filters to paths starting
    with that string — supports the tree-navigation use case where the client
    asks for everything under `plans/` or `memory/vikrant/`. Optional `?q=`
    filters by case-insensitive substring match against `content` (Postgres
    `ILIKE` via Django's `icontains`). MGupta accepted this as the v1 search
    surface — we'll graduate to a tsvector + GIN index when the doc count
    or query latency warrants it.
    """

    def get(self, request, slug):
        prefix = request.query_params.get("prefix", "")
        q = request.query_params.get("q", "").strip()

        if prefix:
            err = _validate_prefix(prefix)
            if err:
                return _err400(err)

        # `q` has no length-limit-driven security risk (it's bound to a
        # parameterised LIKE), but cap it to keep pathological queries off
        # the box. 256 chars matches the path cap and is plenty for FTS.
        if len(q) > _MAX_PATH_LEN:
            return _err400(f"q must be <= {_MAX_PATH_LEN} chars")

        qs = AgentDoc.objects.filter(workspace__slug=slug)
        if prefix:
            qs = qs.filter(path__startswith=prefix)
        if q:
            qs = qs.filter(content__icontains=q)
        rows = qs.order_by("path").values("path", "version", "updated_at")

        return Response({"docs": list(rows)}, status=status.HTTP_200_OK)


class AgentDocDetailAPIEndpoint(BaseAPIView):
    """GET / PUT / DELETE /api/v1/workspaces/<slug>/agent-docs/doc/?path=<path>

    `path` is a query parameter rather than a URL segment so we don't have
    to deal with double URL-encoding the slashes inside agent-doc paths
    (e.g. `plans/vikrant.md`). The DRF query-params layer URL-decodes once,
    which is exactly what we want.
    """

    def _read_path(self, request) -> tuple[str | None, Response | None]:
        """Pull `path` off the query string and validate. Returns
        `(path, None)` on success or `(None, error_response)` on failure."""
        doc_path = request.query_params.get("path", "")
        if not doc_path:
            return None, _err400("path query parameter required")
        err = _validate_path(doc_path)
        if err:
            return None, _err400(err)
        return doc_path, None

    def get(self, request, slug):
        doc_path, err_resp = self._read_path(request)
        if err_resp is not None:
            return err_resp

        try:
            doc = AgentDoc.objects.get(workspace__slug=slug, path=doc_path)
        except AgentDoc.DoesNotExist:
            return Response(
                {"detail": "not found"}, status=status.HTTP_404_NOT_FOUND
            )

        resp = Response(
            {
                "path": doc.path,
                "content": doc.content,
                "version": doc.version,
                "updated_at": doc.updated_at,
                "created_at": doc.created_at,
                "updated_by": str(doc.updated_by_id) if doc.updated_by_id else None,
                "created_by": str(doc.created_by_id) if doc.created_by_id else None,
            },
            status=status.HTTP_200_OK,
        )
        resp["ETag"] = _etag(doc.version)
        return resp

    def put(self, request, slug):
        doc_path, err_resp = self._read_path(request)
        if err_resp is not None:
            return err_resp

        content = request.data.get("content", "")
        if not isinstance(content, str):
            return _err400("content must be a string")

        if_match = _parse_if_match(request.headers.get("If-Match"))

        # Resolve the workspace once — 404 here means the slug is wrong, not
        # that the doc is missing.
        try:
            workspace = Workspace.objects.get(slug=slug)
        except Workspace.DoesNotExist:
            return Response(
                {"detail": "workspace not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # The whole read+compare+write is one transaction with
        # select_for_update so concurrent PUTs serialize on the row.
        with transaction.atomic():
            existing = (
                AgentDoc.objects.select_for_update()
                .filter(workspace=workspace, path=doc_path)
                .first()
            )

            if existing is None:
                # Create path. If-Match must be absent (or `*`); a real
                # version on a non-existent doc is nonsense and we 412 it.
                if if_match is not None and if_match != -1:
                    return Response(
                        {
                            "detail": "If-Match present but doc does not exist",
                            "server_version": None,
                        },
                        status=status.HTTP_412_PRECONDITION_FAILED,
                    )
                doc = AgentDoc.objects.create(
                    workspace=workspace,
                    path=doc_path,
                    content=content,
                    version=1,
                )
                resp = Response(
                    self._serialize_full(doc),
                    status=status.HTTP_201_CREATED,
                )
                resp["ETag"] = _etag(doc.version)
                return resp

            # Update path. If-Match required (matches the spec — no silent
            # overwrites). Missing → 412. Mismatch → 409 with the current
            # version so the client can refetch and retry.
            if if_match is None:
                return Response(
                    {
                        "detail": "If-Match required for update",
                        "server_version": existing.version,
                    },
                    status=status.HTTP_412_PRECONDITION_FAILED,
                )
            if if_match != -1 and if_match != existing.version:
                resp = Response(
                    {
                        "detail": "stale version",
                        "server_version": existing.version,
                    },
                    status=status.HTTP_409_CONFLICT,
                )
                resp["ETag"] = _etag(existing.version)
                return resp

            existing.content = content
            existing.version = existing.version + 1
            existing.save(update_fields=["content", "version", "updated_at", "updated_by"])

        resp = Response(
            self._serialize_full(existing),
            status=status.HTTP_200_OK,
        )
        resp["ETag"] = _etag(existing.version)
        return resp

    def delete(self, request, slug):
        doc_path, err_resp = self._read_path(request)
        if err_resp is not None:
            return err_resp

        if_match = _parse_if_match(request.headers.get("If-Match"))

        with transaction.atomic():
            existing = (
                AgentDoc.objects.select_for_update()
                .filter(workspace__slug=slug, path=doc_path)
                .first()
            )
            if existing is None:
                # Idempotent delete — same as the Obsidian client today.
                return Response(status=status.HTTP_204_NO_CONTENT)

            if if_match is None:
                return Response(
                    {
                        "detail": "If-Match required for delete",
                        "server_version": existing.version,
                    },
                    status=status.HTTP_412_PRECONDITION_FAILED,
                )
            if if_match != -1 and if_match != existing.version:
                resp = Response(
                    {
                        "detail": "stale version",
                        "server_version": existing.version,
                    },
                    status=status.HTTP_409_CONFLICT,
                )
                resp["ETag"] = _etag(existing.version)
                return resp

            existing.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def _serialize_full(doc: AgentDoc) -> dict:
        """Match the shape returned by GET so write responses can be used
        directly to refresh client-side caches (matches Surya's mock)."""
        return {
            "path": doc.path,
            "content": doc.content,
            "version": doc.version,
            "updated_at": doc.updated_at,
            "created_at": doc.created_at,
            "updated_by": str(doc.updated_by_id) if doc.updated_by_id else None,
            "created_by": str(doc.created_by_id) if doc.created_by_id else None,
        }
