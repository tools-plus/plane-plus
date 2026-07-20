# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# PP-85 follow-up (F2): a workspace must have at most one *active*
# (is_epic=True, deleted_at__isnull=True) IssueType -- enforced at the DB
# layer by a partial unique constraint
# (issue_type_unique_epic_per_workspace, see plane.db.models.issue_type and
# migration db.iw_006_unique_epic_issue_type). This covers:
#   - the constraint itself rejecting a second active epic type per
#     workspace, while allowing it once the first is soft-deleted, and
#     allowing one active epic type per *different* workspace;
#   - the iw_006 migration's dedup RunPython, which must run before the
#     constraint is added so it doesn't fail against pre-existing
#     duplicates -- keeping the earliest-created type and repointing
#     ProjectIssueType links and Issue.type FKs onto it before soft-deleting
#     the rest.

import uuid
from contextlib import contextmanager

import pytest
from django.db import IntegrityError, connection, transaction
from django.utils import timezone

from plane.db.migrations.iw_006_unique_epic_issue_type import dedupe_epic_issue_types
from plane.db.models import Issue, IssueType, Project, ProjectIssueType, ProjectMember, Workspace, WorkspaceMember

EPIC_TYPE_CONSTRAINT_NAME = "issue_type_unique_epic_per_workspace"


@contextmanager
def _epic_type_constraint_temporarily_dropped():
    """Simulate the pre-iw_006 DB state (no constraint yet) so duplicate active epic
    types -- the exact situation dedupe_epic_issue_types exists to clean up -- can be
    set up for the tests below. Real workspaces can only reach this state via data that
    predates the migration; the migration itself runs the dedup RunPython before
    AddConstraint for the same reason."""
    constraint = next(c for c in IssueType._meta.constraints if c.name == EPIC_TYPE_CONSTRAINT_NAME)
    with connection.schema_editor() as schema_editor:
        schema_editor.remove_constraint(IssueType, constraint)
    try:
        yield
    finally:
        with connection.schema_editor() as schema_editor:
            schema_editor.add_constraint(IssueType, constraint)


def _make_workspace(create_user, label):
    workspace = Workspace.objects.create(
        name=f"PP-85 {label} workspace",
        owner=create_user,
        slug=f"pp-85-{label}-ws-{uuid.uuid4().hex[:8]}",
    )
    WorkspaceMember.objects.create(workspace=workspace, member=create_user, role=20)
    return workspace


@pytest.mark.unit
@pytest.mark.django_db
class TestIssueTypeUniqueEpicPerWorkspaceConstraint:
    def test_second_active_epic_type_in_same_workspace_is_rejected(self, create_user):
        workspace = _make_workspace(create_user, "constraint")
        IssueType.objects.create(workspace=workspace, name="Epic", is_epic=True)

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                IssueType.objects.create(workspace=workspace, name="Epic (dup)", is_epic=True)

    def test_second_epic_type_allowed_once_first_is_soft_deleted(self, create_user):
        workspace = _make_workspace(create_user, "constraint-softdel")
        first = IssueType.objects.create(workspace=workspace, name="Epic", is_epic=True)
        first.deleted_at = timezone.now()
        first.save(update_fields=["deleted_at"])

        second = IssueType.objects.create(workspace=workspace, name="Epic (new)", is_epic=True)
        assert second.pk is not None

    def test_non_epic_types_are_not_constrained(self, create_user):
        workspace = _make_workspace(create_user, "constraint-nonepic")
        IssueType.objects.create(workspace=workspace, name="Task", is_epic=False)
        # A second, third non-epic type in the same workspace is unaffected.
        IssueType.objects.create(workspace=workspace, name="Bug", is_epic=False)

    def test_each_workspace_may_have_its_own_active_epic_type(self, create_user):
        workspace_a = _make_workspace(create_user, "constraint-ws-a")
        workspace_b = _make_workspace(create_user, "constraint-ws-b")

        IssueType.objects.create(workspace=workspace_a, name="Epic", is_epic=True)
        IssueType.objects.create(workspace=workspace_b, name="Epic", is_epic=True)

        assert IssueType.objects.filter(workspace=workspace_a, is_epic=True).count() == 1
        assert IssueType.objects.filter(workspace=workspace_b, is_epic=True).count() == 1


@pytest.mark.unit
class TestDedupeEpicIssueTypesMigration:
    """Exercises db.iw_006_unique_epic_issue_type's dedupe_epic_issue_types RunPython
    directly against real (non-historical) models -- adequate for the pure data-shuffling
    logic under test; applying cleanly against a real DB is additionally verified via
    `manage.py migrate` (see PP-85 report).

    Uses `django_db(transaction=True)` (real commits, no wrapping test transaction)
    rather than the plain `django_db` marker: schema_editor's DROP/re-CREATE of the
    partial unique index around the duplicate setup below would otherwise hit
    Postgres' "cannot CREATE INDEX because it has pending trigger events" when run in
    the same transaction as the preceding writes to the same table.
    """

    @pytest.mark.django_db(transaction=True)
    def test_noop_when_workspace_has_zero_or_one_active_epic_type(self, create_user):
        workspace = _make_workspace(create_user, "dedup-noop")
        epic_type = IssueType.objects.create(workspace=workspace, name="Epic", is_epic=True)

        from django.apps import apps as real_apps

        dedupe_epic_issue_types(real_apps, None)

        assert IssueType.objects.filter(workspace=workspace, is_epic=True).count() == 1
        assert IssueType.objects.get(pk=epic_type.pk).deleted_at is None

    @pytest.mark.django_db(transaction=True)
    def test_keeps_earliest_and_repoints_project_and_issue_links(self, create_user):
        workspace = _make_workspace(create_user, "dedup")

        kept = IssueType.objects.create(workspace=workspace, name="Epic (first)", is_epic=True)
        # Force an unambiguous created_at ordering regardless of clock resolution.
        IssueType.objects.filter(pk=kept.pk).update(created_at=timezone.now() - timezone.timedelta(days=1))

        from django.apps import apps as real_apps

        # The constraint added alongside this dedup migration is what makes a second
        # active epic type impossible going forward -- drop it temporarily to recreate
        # the pre-migration duplicate state the dedup logic is meant to clean up, then
        # run the dedup itself (which must clear the duplicates before the constraint
        # can be re-added, exactly like the migration's own operation ordering).
        with _epic_type_constraint_temporarily_dropped():
            dup = IssueType.objects.create(workspace=workspace, name="Epic (second)", is_epic=True)

            project_on_dup_only = Project.objects.create(
                name="Project on dup only", identifier="PDO", workspace=workspace, is_issue_type_enabled=False
            )
            ProjectMember.objects.create(
                project=project_on_dup_only, workspace=workspace, member=create_user, role=20
            )
            dup_only_link = ProjectIssueType.objects.create(
                project=project_on_dup_only, issue_type=dup, workspace=workspace
            )

            project_on_both = Project.objects.create(
                name="Project on both", identifier="PBO", workspace=workspace, is_issue_type_enabled=False
            )
            ProjectMember.objects.create(project=project_on_both, workspace=workspace, member=create_user, role=20)
            kept_link_on_both = ProjectIssueType.objects.create(
                project=project_on_both, issue_type=kept, workspace=workspace
            )
            dup_link_on_both = ProjectIssueType.objects.create(
                project=project_on_both, issue_type=dup, workspace=workspace
            )

            epic_on_dup = Issue.objects.create(
                name="Epic typed with dup",
                project=project_on_dup_only,
                workspace=workspace,
                type=dup,
                created_by=create_user,
            )

            dedupe_epic_issue_types(real_apps, None)

        # Exactly one active epic type remains for the workspace, and it's the earliest one.
        remaining = IssueType.objects.filter(workspace=workspace, is_epic=True)
        assert remaining.count() == 1
        assert remaining.first().pk == kept.pk

        # The duplicate itself is soft-deleted, not hard-deleted.
        dup.refresh_from_db()
        assert dup.deleted_at is not None

        # The project that only linked to the dup now links to the kept type instead.
        dup_only_link.refresh_from_db()
        assert dup_only_link.issue_type_id == kept.pk
        assert dup_only_link.deleted_at is None

        # The project that already had an active link to the kept type keeps that link
        # untouched, and its now-redundant link to the dup is soft-deleted rather than
        # repointed (which would have collided with the (project, issue_type) unique
        # constraint on ProjectIssueType).
        kept_link_on_both.refresh_from_db()
        assert kept_link_on_both.issue_type_id == kept.pk
        assert kept_link_on_both.deleted_at is None

        dup_link_on_both.refresh_from_db()
        assert dup_link_on_both.deleted_at is not None

        # Any issue typed with the duplicate is repointed onto the kept type.
        epic_on_dup.refresh_from_db()
        assert epic_on_dup.type_id == kept.pk

    @pytest.mark.django_db(transaction=True)
    def test_is_idempotent_on_repeated_runs(self, create_user):
        workspace = _make_workspace(create_user, "dedup-idempotent")

        kept = IssueType.objects.create(workspace=workspace, name="Epic (first)", is_epic=True)
        IssueType.objects.filter(pk=kept.pk).update(created_at=timezone.now() - timezone.timedelta(days=1))

        from django.apps import apps as real_apps

        with _epic_type_constraint_temporarily_dropped():
            IssueType.objects.create(workspace=workspace, name="Epic (second)", is_epic=True)
            dedupe_epic_issue_types(real_apps, None)

        # Running it again once the constraint is back (the workspace is already deduped)
        # must be a safe no-op.
        dedupe_epic_issue_types(real_apps, None)

        assert IssueType.objects.filter(workspace=workspace, is_epic=True).count() == 1
        assert IssueType.objects.filter(workspace=workspace, is_epic=True).first().pk == kept.pk
