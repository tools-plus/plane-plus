# Plane Plus — AgentDoc model: workspace-level markdown notes with
# optimistic-concurrency single-writer semantics.
#
# Replaces MGupta's local Obsidian vault (plans/, memory/, learnings/, specs/,
# blogs/drafts/, inbox/, curations/) with an in-Plane store that all agents can
# reach over the existing PAT auth path.
#
# Hard constraint: SEPARATE table from `Page`. NO Yjs, NO browser CRDT, NO
# realtime collab. The whole reason this feature exists is that we got burned
# by Yjs+IndexedDB clobbering REST writes (see specs/plane-live-race-guard.md
# in the vault, and PP-68). The version field below is the ETag we serve to
# clients; writers MUST send `If-Match` and we reject stale writes with 409.

from django.db import models

from .base import BaseModel


class AgentDoc(BaseModel):
    """A pure-markdown workspace-level note with an optimistic-lock version.

    Path is treated as the natural key (unique within a workspace). The folder
    structure clients see (`plans/`, `memory/<agent>/`, etc.) is encoded in the
    path itself — there is no separate "folder" table.

    Concurrency: every write increments `version`. Clients PUT with
    `If-Match: "<n>"` carrying the version they think is current; if the
    server's version doesn't match, we 409. The read+compare+write happens
    inside a transaction with `SELECT ... FOR UPDATE` (see views) so two
    concurrent PUTs cannot both succeed against the same prior version.
    """

    workspace = models.ForeignKey(
        "db.Workspace",
        on_delete=models.CASCADE,
        related_name="agent_docs",
    )
    path = models.CharField(max_length=256)
    content = models.TextField(blank=True, default="")
    # Monotonic counter; bumped on every successful write. Used as the ETag
    # value in HTTP headers. Starts at 1 on create.
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "agent_docs"
        ordering = ["path"]
        verbose_name = "Agent Doc"
        verbose_name_plural = "Agent Docs"
        constraints = [
            # Hard guarantee: one row per (workspace, path). The optimistic-
            # lock protocol assumes this — without it concurrent creates could
            # produce duplicates.
            models.UniqueConstraint(
                fields=["workspace", "path"],
                name="agent_doc_workspace_path_uniq",
            ),
        ]
        indexes = [
            # List-by-prefix queries (`?prefix=plans/`) — workspace_id is
            # always present in the predicate; path is leading-anchor matched.
            models.Index(
                fields=["workspace", "path"],
                name="agent_doc_ws_path_idx",
            ),
            # Sidebar/recent-edited views.
            models.Index(
                fields=["workspace", "-updated_at"],
                name="agent_doc_ws_updated_idx",
            ),
        ]

    def __str__(self):
        return f"{self.path} (v{self.version}, {self.workspace})"
