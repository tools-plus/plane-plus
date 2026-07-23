# Plane Plus — Enforce at most one active Epic IssueType per workspace
#
# PP-85: nothing previously stopped a workspace from ending up with more
# than one active (is_epic=True, deleted_at__isnull=True) IssueType — e.g.
# two concurrent Project saves racing plane.iw.signals'
# provision_epic_type_on_enable before either commit — which would silently
# fragment epics across two types. This adds a partial unique constraint to
# make that a DB-level invariant.
#
# Since the constraint can't be added while duplicates already exist, this
# migration first deduplicates any workspace that currently has more than
# one active Epic IssueType: it keeps the earliest-created one, repoints
# ProjectIssueType links and Issue.type FKs from the duplicates onto it,
# then soft-deletes the duplicate IssueType rows. This is a no-op if every
# workspace already has at most one (which is the expected steady state).
#
# Logic is intentionally inlined against historical models (apps.get_model),
# not plane.iw.provisioning, since migrations must not depend on current
# app code / custom managers.

from django.db import migrations, models
from django.db.models import Q


def dedupe_epic_issue_types(apps, schema_editor):
    IssueType = apps.get_model("db", "IssueType")
    ProjectIssueType = apps.get_model("db", "ProjectIssueType")
    Issue = apps.get_model("db", "Issue")

    from django.utils import timezone

    now = timezone.now()

    by_workspace = {}
    for epic_type in IssueType.objects.filter(is_epic=True, deleted_at__isnull=True).order_by(
        "workspace_id", "created_at"
    ):
        by_workspace.setdefault(epic_type.workspace_id, []).append(epic_type)

    for workspace_id, epic_types in by_workspace.items():
        if len(epic_types) <= 1:
            continue

        # Keep the earliest-created active Epic IssueType for this
        # workspace; repoint everything else onto it.
        kept, *duplicates = epic_types

        for dup in duplicates:
            for pit in ProjectIssueType.objects.filter(issue_type=dup):
                already_linked_to_kept = (
                    ProjectIssueType.objects.filter(
                        project_id=pit.project_id,
                        issue_type=kept,
                        deleted_at__isnull=True,
                    )
                    .exclude(pk=pit.pk)
                    .exists()
                )
                if pit.deleted_at is None and already_linked_to_kept:
                    # The project already has an active link to the kept
                    # type — repointing this one too would collide with
                    # project_issue_type_unique_project_issue_type_when_deleted_at_null.
                    # Soft-delete the now-redundant duplicate link instead.
                    pit.deleted_at = now
                    pit.save(update_fields=["deleted_at"])
                else:
                    pit.issue_type = kept
                    pit.save(update_fields=["issue_type"])

            # Repoint any issues typed with the duplicate onto the kept type.
            Issue.objects.filter(type=dup).update(type=kept)

            # Soft-delete the duplicate IssueType itself.
            dup.deleted_at = now
            dup.save(update_fields=["deleted_at"])


def noop_reverse(apps, schema_editor):
    # Dedup is a data cleanup with no meaningful undo (there's no reliable
    # way to know which soft-deleted rows this migration produced vs. ones
    # that were already soft-deleted). RemoveConstraint below is the actual
    # reversible part of this migration.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("db", "iw_005_backfill_epic_issue_type"),
    ]

    operations = [
        # Dedup must run before the constraint is added, or AddConstraint
        # fails against any workspace with existing duplicates.
        migrations.RunPython(dedupe_epic_issue_types, noop_reverse),
        migrations.AddConstraint(
            model_name="issuetype",
            constraint=models.UniqueConstraint(
                fields=["workspace"],
                condition=Q(is_epic=True, deleted_at__isnull=True),
                name="issue_type_unique_epic_per_workspace",
            ),
        ),
    ]
