# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# PP-85 follow-up: unit coverage for plane.iw.gating, the shared helper that
# every epic endpoint (web and external SDK/MCP) calls to enforce "epics
# enabled for a project" == Project.is_issue_type_enabled.

import uuid

import pytest
from rest_framework.exceptions import ValidationError

from plane.db.models import Project, Workspace, WorkspaceMember
from plane.iw.gating import EPICS_DISABLED_ERROR, assert_epics_enabled, assert_project_epics_enabled


@pytest.mark.unit
@pytest.mark.django_db
class TestAssertEpicsEnabled:
    def _make_workspace(self, create_user):
        workspace = Workspace.objects.create(
            name="PP-85 gating workspace",
            owner=create_user,
            slug=f"pp-85-gating-unit-ws-{uuid.uuid4().hex[:8]}",
        )
        WorkspaceMember.objects.create(workspace=workspace, member=create_user, role=20)
        return workspace

    def test_does_not_raise_when_enabled(self, create_user):
        workspace = self._make_workspace(create_user)
        project = Project.objects.create(
            name="Enabled", identifier="EN1", workspace=workspace, is_issue_type_enabled=True
        )
        assert assert_epics_enabled(project) is None

    def test_raises_validation_error_when_disabled(self, create_user):
        workspace = self._make_workspace(create_user)
        project = Project.objects.create(
            name="Disabled", identifier="DI1", workspace=workspace, is_issue_type_enabled=False
        )
        with pytest.raises(ValidationError) as exc_info:
            assert_epics_enabled(project)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == {"error": EPICS_DISABLED_ERROR}


@pytest.mark.unit
@pytest.mark.django_db
class TestAssertProjectEpicsEnabled:
    def _make_workspace(self, create_user):
        workspace = Workspace.objects.create(
            name="PP-85 gating fetch workspace",
            owner=create_user,
            slug=f"pp-85-gating-fetch-ws-{uuid.uuid4().hex[:8]}",
        )
        WorkspaceMember.objects.create(workspace=workspace, member=create_user, role=20)
        return workspace

    def test_returns_project_when_enabled(self, create_user):
        workspace = self._make_workspace(create_user)
        project = Project.objects.create(
            name="Enabled fetch", identifier="EN2", workspace=workspace, is_issue_type_enabled=True
        )

        result = assert_project_epics_enabled(workspace.slug, project.id)

        assert result.id == project.id

    def test_raises_validation_error_when_disabled(self, create_user):
        workspace = self._make_workspace(create_user)
        project = Project.objects.create(
            name="Disabled fetch", identifier="DI2", workspace=workspace, is_issue_type_enabled=False
        )

        with pytest.raises(ValidationError):
            assert_project_epics_enabled(workspace.slug, project.id)

    def test_missing_project_raises_does_not_exist(self, create_user):
        workspace = self._make_workspace(create_user)

        with pytest.raises(Project.DoesNotExist):
            assert_project_epics_enabled(workspace.slug, uuid.uuid4())
