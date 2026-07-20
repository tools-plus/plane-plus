# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# PP-85 regression: plane.iw.provisioning.ensure_workspace_epic_type must be
# idempotent -- it is called on every project save where
# is_issue_type_enabled=True, so calling it twice (or once per project save)
# must not create duplicate Epic IssueType rows or duplicate
# ProjectIssueType links.

import pytest

from plane.db.models import IssueType, Project, ProjectIssueType, Workspace, WorkspaceMember
from plane.iw.provisioning import ensure_workspace_epic_type


@pytest.mark.unit
@pytest.mark.django_db
class TestEnsureWorkspaceEpicType:
    def _make_workspace(self, create_user):
        workspace = Workspace.objects.create(
            name="PP-85 provisioning workspace",
            owner=create_user,
            slug="pp-85-provisioning-ws",
        )
        WorkspaceMember.objects.create(workspace=workspace, member=create_user, role=20)
        return workspace

    def test_creates_epic_type_when_missing(self, create_user):
        workspace = self._make_workspace(create_user)
        assert IssueType.objects.filter(workspace=workspace, is_epic=True).count() == 0

        epic_type = ensure_workspace_epic_type(workspace)

        assert epic_type.is_epic is True
        assert epic_type.workspace_id == workspace.id
        assert IssueType.objects.filter(workspace=workspace, is_epic=True).count() == 1

    def test_idempotent_without_project_two_calls_one_type(self, create_user):
        workspace = self._make_workspace(create_user)

        first = ensure_workspace_epic_type(workspace)
        second = ensure_workspace_epic_type(workspace)

        assert first.id == second.id
        assert IssueType.objects.filter(workspace=workspace, is_epic=True).count() == 1

    def test_idempotent_with_project_link_created_once(self, create_user):
        workspace = self._make_workspace(create_user)
        project = Project.objects.create(
            name="PP-85 provisioning project",
            identifier="PP85P",
            workspace=workspace,
        )

        ensure_workspace_epic_type(workspace, project=project)
        ensure_workspace_epic_type(workspace, project=project)

        assert IssueType.objects.filter(workspace=workspace, is_epic=True).count() == 1
        assert ProjectIssueType.objects.filter(project=project).count() == 1

    def test_returns_existing_type_when_already_seeded(self, create_user):
        """If an Epic type already exists (e.g. seeded by iw_002), reuse it -- don't create a second one."""
        workspace = self._make_workspace(create_user)
        existing = IssueType.objects.create(
            workspace=workspace,
            name="Epic",
            is_epic=True,
        )

        result = ensure_workspace_epic_type(workspace)

        assert result.id == existing.id
        assert IssueType.objects.filter(workspace=workspace, is_epic=True).count() == 1

    def test_project_link_uses_existing_workspace_epic_type(self, create_user):
        """Two different projects in the same workspace should share one Epic type."""
        workspace = self._make_workspace(create_user)
        project_a = Project.objects.create(name="Project A", identifier="PA", workspace=workspace)
        project_b = Project.objects.create(name="Project B", identifier="PB", workspace=workspace)

        type_a = ensure_workspace_epic_type(workspace, project=project_a)
        type_b = ensure_workspace_epic_type(workspace, project=project_b)

        assert type_a.id == type_b.id
        assert IssueType.objects.filter(workspace=workspace, is_epic=True).count() == 1
        assert ProjectIssueType.objects.filter(issue_type=type_a).count() == 2
