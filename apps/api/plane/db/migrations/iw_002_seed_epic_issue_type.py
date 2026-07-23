# Plane Plus — Seed Epic IssueType for all workspaces

from django.db import migrations


def seed_epic_type(apps, schema_editor):
    IssueType = apps.get_model("db", "IssueType")
    ProjectIssueType = apps.get_model("db", "ProjectIssueType")
    Workspace = apps.get_model("db", "Workspace")
    Project = apps.get_model("db", "Project")

    for workspace in Workspace.objects.all():
        # Skip if already has an Epic type
        if IssueType.objects.filter(workspace=workspace, is_epic=True).exists():
            continue

        epic_type = IssueType.objects.create(
            workspace=workspace,
            name="Epic",
            description="Large feature or initiative spanning multiple work items",
            is_epic=True,
            is_default=False,
            is_active=True,
            level=1,
            logo_props={"in_use": "emoji", "emoji": {"value": "⚡"}},
        )

        # Link to all projects and enable issue types
        for project in Project.objects.filter(workspace=workspace):
            ProjectIssueType.objects.get_or_create(
                project=project,
                issue_type=epic_type,
                defaults={"level": 0, "is_default": False, "workspace": workspace},
            )
            # Enable issue types on the project
            if not project.is_issue_type_enabled:
                project.is_issue_type_enabled = True
                project.save(update_fields=["is_issue_type_enabled"])


def reverse_seed(apps, schema_editor):
    IssueType = apps.get_model("db", "IssueType")
    IssueType.objects.filter(is_epic=True, name="Epic").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("db", "iw_001_page_workspace_is_global_idx"),
    ]

    operations = [
        migrations.RunPython(seed_epic_type, reverse_seed),
    ]
