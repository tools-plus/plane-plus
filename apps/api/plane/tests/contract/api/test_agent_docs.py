# Plane Plus — PP-70 Agent Docs API contract tests.
#
# Covers the optimistic-concurrency single-writer protocol end-to-end:
#   - basic CRUD via api_key_client
#   - path validation (400s)
#   - list with prefix and ?q= icontains FTS
#   - ETag header on reads/writes
#   - 412 (If-Match missing) and 409 (stale If-Match) edge cases
#   - **true concurrency**: two threaded PUTs from the same prior version
#     race against the row-level lock, exactly one wins
#
# The concurrency test uses pytest-django's `transactional_db` so the
# `transaction.atomic() + select_for_update()` block in the view actually
# serializes against a real Postgres lock instead of being collapsed into
# the pytest-managed test transaction.

import threading

import pytest
from rest_framework import status

from plane.db.models import AgentDoc


# Path-as-query helper. Tests pass `path=<doc_path>` in `data` for queries
# rather than embedding it in the URL — DRF's APIClient encodes it correctly.
LIST_URL = "/api/v1/workspaces/{slug}/agent-docs/"
DOC_URL = "/api/v1/workspaces/{slug}/agent-docs/doc/"


def _list_url(slug: str) -> str:
    return LIST_URL.format(slug=slug)


def _doc_url(slug: str, path: str) -> str:
    # DRF APIClient passes query params via the `data` kwarg on GET/DELETE,
    # so we don't need to URL-encode here. PUT can't use `data` for query
    # params (it's the body) — see _put_doc below.
    return DOC_URL.format(slug=slug)


def _put_doc(client, slug, path, content, if_match=None):
    """PUT helper — the path goes on the URL as a query param because DRF's
    `data` kwarg becomes the request body on PUT."""
    url = f"{DOC_URL.format(slug=slug)}?path={path}"
    extra = {}
    if if_match is not None:
        extra["HTTP_IF_MATCH"] = if_match
    return client.put(url, {"content": content}, format="json", **extra)


# ----------------------------------------------------------- Basic CRUD --


@pytest.mark.contract
@pytest.mark.django_db
class TestAgentDocCRUD:
    """Cover the create/read/update/delete happy path and the small 400s."""

    def test_list_empty_returns_wrapped_object(self, api_key_client, workspace):
        """List response must be `{docs: [...]}` even when empty — clients
        that destructure response.docs would break on a bare array."""
        resp = api_key_client.get(_list_url(workspace.slug))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == {"docs": []}

    def test_create_returns_201_with_etag(self, api_key_client, workspace):
        resp = _put_doc(
            api_key_client,
            workspace.slug,
            "plans/vikrant.md",
            "# Plan\n",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        body = resp.json()
        assert body["path"] == "plans/vikrant.md"
        assert body["version"] == 1
        assert body["content"] == "# Plan\n"
        assert resp.headers["ETag"] == '"1"'

    def test_get_returns_doc_with_etag(self, api_key_client, workspace):
        _put_doc(api_key_client, workspace.slug, "plans/x.md", "hi")
        resp = api_key_client.get(_doc_url(workspace.slug, "plans/x.md"), {"path": "plans/x.md"})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["content"] == "hi"
        # APIClient lower-cases header keys via Werkzeug-ish behaviour;
        # rest-framework returns them via response['ETag'] reliably.
        assert resp["ETag"] == '"1"'

    def test_get_missing_returns_404_with_detail(self, api_key_client, workspace):
        resp = api_key_client.get(_doc_url(workspace.slug, "plans/x.md"), {"path": "plans/missing.md"})
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert resp.json() == {"detail": "not found"}

    def test_delete_idempotent_for_missing(self, api_key_client, workspace):
        """DELETE on a non-existent doc returns 204 — matches the Obsidian
        client's behaviour today and keeps the migration script simple."""
        url = f"{DOC_URL.format(slug=workspace.slug)}?path=plans/never.md"
        resp = api_key_client.delete(url, HTTP_IF_MATCH='"*"')
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_existing_with_if_match(self, api_key_client, workspace):
        _put_doc(api_key_client, workspace.slug, "plans/x.md", "hi")
        url = f"{DOC_URL.format(slug=workspace.slug)}?path=plans/x.md"
        resp = api_key_client.delete(url, HTTP_IF_MATCH='"1"')
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not AgentDoc.objects.filter(path="plans/x.md").exists()


# ------------------------------------------------------ Path validation --


@pytest.mark.contract
@pytest.mark.django_db
class TestAgentDocPathValidation:
    """Every reject path returns 400 with `{detail: <msg>}`."""

    BAD_PATHS = [
        ("/foo.md", "path must not start with /"),
        ("foo.txt", "path must end with .md"),
        ("../foo.md", "path must not contain .. segments"),
        ("foo//bar.md", "path must not contain // (empty segments)"),
        ("foo bar.md", "path must match"),  # space — fails regex
    ]

    @pytest.mark.parametrize("bad_path,err_fragment", BAD_PATHS)
    def test_get_rejects_bad_path(
        self, api_key_client, workspace, bad_path, err_fragment
    ):
        url = f"{DOC_URL.format(slug=workspace.slug)}?path={bad_path}"
        resp = api_key_client.get(url)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "detail" in resp.json()
        assert err_fragment in resp.json()["detail"]

    def test_missing_path_query_returns_400(self, api_key_client, workspace):
        resp = api_key_client.get(DOC_URL.format(slug=workspace.slug))
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.json() == {"detail": "path query parameter required"}


# --------------------------------------------------- List filters: prefix + q --


@pytest.mark.contract
@pytest.mark.django_db
class TestAgentDocListFilters:
    """Prefix filter is path-startswith; ?q= is content icontains. Both
    can be combined."""

    def _seed(self, client, workspace):
        _put_doc(client, workspace.slug, "plans/vikrant.md", "PP-70 backend tracking")
        _put_doc(
            client,
            workspace.slug,
            "memory/vikrant/2026-04-26.md",
            "memory mentioning HOCUSPOCUS race",
        )
        _put_doc(
            client, workspace.slug, "blogs/drafts/agent-docs.md", "draft about agent docs"
        )

    def test_list_no_filter_returns_all(self, api_key_client, workspace):
        self._seed(api_key_client, workspace)
        resp = api_key_client.get(_list_url(workspace.slug))
        paths = [d["path"] for d in resp.json()["docs"]]
        assert paths == sorted(paths)
        assert len(paths) == 3

    def test_list_prefix_narrows_to_subtree(self, api_key_client, workspace):
        self._seed(api_key_client, workspace)
        resp = api_key_client.get(_list_url(workspace.slug), {"prefix": "plans/"})
        paths = [d["path"] for d in resp.json()["docs"]]
        assert paths == ["plans/vikrant.md"]

    def test_list_q_is_case_insensitive_substring(self, api_key_client, workspace):
        self._seed(api_key_client, workspace)
        resp = api_key_client.get(_list_url(workspace.slug), {"q": "race"})
        paths = [d["path"] for d in resp.json()["docs"]]
        assert paths == ["memory/vikrant/2026-04-26.md"]

    def test_list_prefix_and_q_combined(self, api_key_client, workspace):
        self._seed(api_key_client, workspace)
        # Same q matches under memory/ but not under plans/
        resp = api_key_client.get(
            _list_url(workspace.slug), {"prefix": "plans/", "q": "race"}
        )
        assert resp.json() == {"docs": []}

    def test_list_summary_omits_content_and_actor_fields(
        self, api_key_client, workspace
    ):
        """Summary rows must contain only `path/version/updated_at` so the
        list endpoint stays cheap to render in the navigator."""
        self._seed(api_key_client, workspace)
        resp = api_key_client.get(_list_url(workspace.slug))
        for row in resp.json()["docs"]:
            assert set(row.keys()) == {"path", "version", "updated_at"}


# --------------------------------------------- Optimistic concurrency: 412/409 --


@pytest.mark.contract
@pytest.mark.django_db
class TestAgentDocOptimisticLock:
    """Sequential coverage of the protocol: missing/stale If-Match cases."""

    def test_put_update_without_if_match_returns_412(
        self, api_key_client, workspace
    ):
        _put_doc(api_key_client, workspace.slug, "plans/x.md", "v1")
        resp = _put_doc(api_key_client, workspace.slug, "plans/x.md", "v2")
        assert resp.status_code == status.HTTP_412_PRECONDITION_FAILED
        body = resp.json()
        assert body["detail"] == "If-Match required for update"
        assert body["server_version"] == 1

    def test_put_update_with_stale_if_match_returns_409(
        self, api_key_client, workspace
    ):
        _put_doc(api_key_client, workspace.slug, "plans/x.md", "v1")
        # Bump server to v2 by writing successfully...
        _put_doc(
            api_key_client, workspace.slug, "plans/x.md", "v2", if_match='"1"'
        )
        # ...then try to write from the stale v1 perspective.
        resp = _put_doc(
            api_key_client, workspace.slug, "plans/x.md", "stale", if_match='"1"'
        )
        assert resp.status_code == status.HTTP_409_CONFLICT
        body = resp.json()
        assert body == {"detail": "stale version", "server_version": 2}
        assert resp["ETag"] == '"2"'

    def test_put_create_with_if_match_returns_412(self, api_key_client, workspace):
        """If-Match: "5" on a non-existent doc is nonsense — reject."""
        resp = _put_doc(
            api_key_client, workspace.slug, "plans/new.md", "x", if_match='"5"'
        )
        assert resp.status_code == status.HTTP_412_PRECONDITION_FAILED

    def test_force_write_with_if_match_star(self, api_key_client, workspace):
        """`If-Match: *` overrides version check (used by migration script)."""
        _put_doc(api_key_client, workspace.slug, "plans/x.md", "v1")
        resp = _put_doc(
            api_key_client, workspace.slug, "plans/x.md", "forced", if_match='"*"'
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["version"] == 2


# -------------------------- True concurrency: two writers, one prior version --


@pytest.mark.contract
@pytest.mark.django_db(transaction=True)
class TestAgentDocConcurrentWrites:
    """The hard part of the contract: when two clients both PUT
    `If-Match: "1"` against the same doc at roughly the same time, exactly
    one of them must win and the other must get 409.

    We need `transaction=True` (TransactionTestCase semantics) so the
    `transaction.atomic() + select_for_update()` inside the view actually
    runs against the database — pytest-django's default fixture wraps each
    test in an outer transaction that would mask the real lock behaviour.

    Strategy:
      1. Seed v1 of `plans/race.md`.
      2. Spawn N threads that each try to PUT `If-Match: "1"`.
      3. Assert exactly one returns 200 (or 201) and the rest return 409.
      4. Final DB version is exactly 2 — the lock prevented multiple wins.
    """

    def test_two_writers_one_wins(self, workspace, api_token):
        # Arrange: seed v1.
        from rest_framework.test import APIClient

        seed = APIClient()
        seed.credentials(HTTP_X_API_KEY=api_token.token)
        r = _put_doc(seed, workspace.slug, "plans/race.md", "v1")
        assert r.status_code == status.HTTP_201_CREATED

        # Each thread gets its own APIClient (and thus its own request
        # cycle / db connection) — sharing one across threads would
        # serialise them at the client layer and the test would pass for
        # the wrong reason.
        N = 4
        results: list[int] = []
        bodies: list[dict] = []
        results_lock = threading.Lock()
        barrier = threading.Barrier(N)

        def writer(idx: int):
            from django.db import connection

            client = APIClient()
            client.credentials(HTTP_X_API_KEY=api_token.token)
            barrier.wait()  # release all writers ~simultaneously
            try:
                resp = _put_doc(
                    client,
                    workspace.slug,
                    "plans/race.md",
                    f"writer-{idx}",
                    if_match='"1"',
                )
                with results_lock:
                    results.append(resp.status_code)
                    try:
                        bodies.append(resp.json())
                    except Exception:
                        bodies.append({})
            finally:
                # Each thread opened its own connection — close it so the
                # test teardown doesn't leak.
                connection.close()

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(N)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        # Exactly one writer succeeds; the rest 409.
        wins = [s for s in results if s == status.HTTP_200_OK]
        conflicts = [s for s in results if s == status.HTTP_409_CONFLICT]
        assert len(results) == N, f"expected {N} responses, got {results}"
        assert len(wins) == 1, f"expected exactly 1 winner, got {results}"
        assert len(conflicts) == N - 1, (
            f"expected {N - 1} conflicts, got {results}"
        )

        # All conflict bodies report server_version=2 (the post-winner value)
        # — that's how the UI knows what version to refetch against.
        for status_code, body in zip(results, bodies):
            if status_code == status.HTTP_409_CONFLICT:
                assert body.get("detail") == "stale version"
                assert body.get("server_version") == 2

        # And the DB row landed at exactly v2 — no double-bump.
        doc = AgentDoc.objects.get(workspace=workspace, path="plans/race.md")
        assert doc.version == 2
