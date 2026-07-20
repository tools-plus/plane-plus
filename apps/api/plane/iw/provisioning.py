# InfraWatch — Epic IssueType provisioning
#
# The "Epics" toggle in project settings maps to Project.is_issue_type_enabled
# (there is no separate is_epic_enabled field). Whenever a project turns that
# toggle on, the workspace needs an Epic-flagged IssueType (and a link
# between that type and the project) so that epic creation
# (IwEpicViewSet.create) has a type to attach to new issues.
#
# Defaults mirror plane/db/migrations/iw_002_seed_epic_issue_type.py — keep
# them in sync if that seed data ever changes.

from plane.db.models import IssueType, ProjectIssueType

EPIC_TYPE_DEFAULTS = {
    "name": "Epic",
    "description": "Large feature or initiative spanning multiple work items",
    "is_default": False,
    "is_active": True,
    "level": 1,
    "logo_props": {"in_use": "emoji", "emoji": {"value": "⚡"}},
}


def ensure_workspace_epic_type(workspace, project=None):
    """Ensure `workspace` has an Epic IssueType, optionally linked to `project`.

    Fully idempotent — safe to call on every project save where
    is_issue_type_enabled is True.
    """
    epic_type, _ = IssueType.objects.get_or_create(
        workspace=workspace,
        is_epic=True,
        defaults=EPIC_TYPE_DEFAULTS,
    )

    if project is not None:
        ProjectIssueType.objects.get_or_create(
            project=project,
            issue_type=epic_type,
            defaults={"level": 0, "is_default": False, "workspace": workspace},
        )

    return epic_type
