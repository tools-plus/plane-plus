# InfraWatch — Backfill Epic IssueType for projects with Epics already enabled
#
# PP-85: iw_002 seeded an Epic IssueType for every workspace that existed at
# that time, but projects/workspaces created afterwards (or projects that
# turned on the "Epics" toggle, i.e. is_issue_type_enabled=True, after that
# seed ran) never got one — causing epic creation to 500. This backfills any
# project that currently has is_issue_type_enabled=True but whose workspace
# still lacks an Epic type, plus the ProjectIssueType link.
#
# Logic is intentionally inlined (not imported from plane.iw.provisioning)
# since migrations must use historical models, not the current app code.
#
# NOTE — naming collision risk: PP-80 (a separate in-flight branch) also
# plans to add an "iw_005_*" migration. If PP-80 merges first, this file
# must be renumbered to iw_006 (and `dependencies` below updated) before
# this branch merges.

from django.db import migrations

EPIC_TYPE_DEFAULTS = {
    "name": "Epic",
    "description": "Large feature or initiative spanning multiple work items",
    "is_default": False,
    "is_active": True,
    "level": 1,
    "logo_props": {"in_use": "emoji", "emoji": {"value": "⚡"}},
}


def backfill_epic_type(apps, schema_editor):
    Project = apps.get_model("db", "Project")
    IssueType = apps.get_model("db", "IssueType")
    ProjectIssueType = apps.get_model("db", "ProjectIssueType")

    workspace_epic_types = {}

    for project in Project.objects.filter(is_issue_type_enabled=True).select_related("workspace"):
        workspace = project.workspace

        epic_type = workspace_epic_types.get(workspace.id)
        if epic_type is None:
            epic_type, _ = IssueType.objects.get_or_create(
                workspace=workspace,
                is_epic=True,
                defaults=EPIC_TYPE_DEFAULTS,
            )
            workspace_epic_types[workspace.id] = epic_type

        ProjectIssueType.objects.get_or_create(
            project=project,
            issue_type=epic_type,
            defaults={"level": 0, "is_default": False, "workspace": workspace},
        )


def noop_reverse(apps, schema_editor):
    # Backfill is additive and idempotent to re-run forward; there's nothing
    # safe to undo here (iw_002's reverse_seed already covers deleting
    # seeded Epic types wholesale).
    pass


class Migration(migrations.Migration):
    # Merges the two parallel migration leaves (iw_004_agent_doc and
    # 0121_alter_estimate_type) so this becomes the sole graph head.
    dependencies = [
        ("db", "iw_004_agent_doc"),
        ("db", "0121_alter_estimate_type"),
    ]

    operations = [
        migrations.RunPython(backfill_epic_type, noop_reverse),
    ]
