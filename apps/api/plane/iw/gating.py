# InfraWatch — Epics feature gate
#
# PP-85: "epics enabled for a project" == Project.is_issue_type_enabled (the
# project-settings "Epics" toggle; there is no separate is_epic_enabled
# field). Every epic endpoint -- web (plane.app.views.issue.iw_epic) and
# external SDK/MCP (plane.iw.views.epic) -- must reject both reads and
# writes with a clean error when that flag is off. Existing epic data is
# left untouched (gated, not deleted); re-enabling the flag restores access
# without any further action, since plane.iw.signals provisions the
# workspace Epic IssueType on every save where the flag is True.
#
# Shared here so both plane.app.views.base.BaseViewSet/BaseAPIView and
# plane.api.views.base.BaseAPIView pick it up the same way: both wrap DRF's
# default exception handling in handle_exception(), so raising DRF's
# rest_framework.exceptions.ValidationError with a dict detail turns into a
# plain `{"error": "..."}` 400 response either way (their `except
# ValidationError` branches only special-case *Django's*
# django.core.exceptions.ValidationError, which this is not).

from rest_framework.exceptions import ValidationError

from plane.db.models import Project

EPICS_DISABLED_ERROR = "Epics are not enabled for this project"


def assert_epics_enabled(project):
    """Raise a DRF ValidationError (-> HTTP 400) unless `project` has epics enabled."""
    if not project.is_issue_type_enabled:
        raise ValidationError({"error": EPICS_DISABLED_ERROR})


def assert_project_epics_enabled(slug, project_id):
    """Fetch the project by slug/project_id and assert it has epics enabled.

    Convenience for handlers that don't already hold a `Project` instance.
    Raises `Project.DoesNotExist` (-> 404 via the base view's
    `handle_exception`, matching how the rest of the codebase resolves
    projects) if the project itself doesn't exist, or `ValidationError`
    (-> 400) if epics are disabled for it.
    """
    project = Project.objects.only("id", "is_issue_type_enabled").get(pk=project_id, workspace__slug=slug)
    assert_epics_enabled(project)
    return project
