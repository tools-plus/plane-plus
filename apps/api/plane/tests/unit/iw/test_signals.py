# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# PP-85 follow-up (provisioning, Part A): plane.iw.signals.provision_epic_type_on_enable
# is a Project post_save receiver -- the single source of truth for
# provisioning the workspace Epic IssueType whenever a project is saved with
# is_issue_type_enabled=True. This covers every path that can flip the flag
# on (app create/patch, API-v1 create/patch, bulk/shell saves, ...) in one
# place; the HTTP-level paths are covered by
# plane.tests.contract.app.test_iw_project_epic_provisioning and
# plane.tests.contract.api.test_iw_project_epic_provisioning. This file
# exercises the signal directly at the ORM layer.

import uuid

import pytest

from plane.db.models import IssueType, Project, ProjectIssueType, Workspace, WorkspaceMember


@pytest.mark.unit
@pytest.mark.django_db
class TestProvisionEpicTypeOnEnableSignal:
    def _make_workspace(self, create_user):
        workspace = Workspace.objects.create(
            name="PP-85 signal workspace",
            owner=create_user,
            slug=f"pp-85-signal-ws-{uuid.uuid4().hex[:8]}",
        )
        WorkspaceMember.objects.create(workspace=workspace, member=create_user, role=20)
        return workspace

    def test_project_created_with_flag_on_provisions_type_and_link(self, create_user):
        workspace = self._make_workspace(create_user)

        project = Project.objects.create(
            name="Flag on at create",
            identifier="FOC",
            workspace=workspace,
            is_issue_type_enabled=True,
        )

        epic_types = IssueType.objects.filter(workspace=workspace, is_epic=True)
        assert epic_types.count() == 1
        assert ProjectIssueType.objects.filter(project=project, issue_type=epic_types.first()).exists()

    def test_project_created_with_flag_off_provisions_nothing(self, create_user):
        workspace = self._make_workspace(create_user)

        Project.objects.create(
            name="Flag off at create",
            identifier="FOFC",
            workspace=workspace,
            is_issue_type_enabled=False,
        )

        assert IssueType.objects.filter(workspace=workspace, is_epic=True).count() == 0

    def test_flipping_flag_on_via_save_provisions_type(self, create_user):
        workspace = self._make_workspace(create_user)
        project = Project.objects.create(
            name="Flip on",
            identifier="FLO",
            workspace=workspace,
            is_issue_type_enabled=False,
        )
        assert IssueType.objects.filter(workspace=workspace, is_epic=True).count() == 0

        project.is_issue_type_enabled = True
        project.save()

        assert IssueType.objects.filter(workspace=workspace, is_epic=True).count() == 1
        assert ProjectIssueType.objects.filter(project=project).count() == 1

    def test_repeated_saves_with_flag_on_are_idempotent(self, create_user):
        workspace = self._make_workspace(create_user)
        project = Project.objects.create(
            name="Repeat saves",
            identifier="RPS",
            workspace=workspace,
            is_issue_type_enabled=True,
        )

        for _ in range(3):
            project.save()

        assert IssueType.objects.filter(workspace=workspace, is_epic=True).count() == 1
        assert ProjectIssueType.objects.filter(project=project).count() == 1

    def test_multiple_projects_in_same_workspace_share_one_epic_type(self, create_user):
        workspace = self._make_workspace(create_user)

        project_a = Project.objects.create(
            name="Project A", identifier="PSA", workspace=workspace, is_issue_type_enabled=True
        )
        project_b = Project.objects.create(
            name="Project B", identifier="PSB", workspace=workspace, is_issue_type_enabled=True
        )

        epic_types = IssueType.objects.filter(workspace=workspace, is_epic=True)
        assert epic_types.count() == 1
        epic_type = epic_types.first()
        assert ProjectIssueType.objects.filter(project=project_a, issue_type=epic_type).exists()
        assert ProjectIssueType.objects.filter(project=project_b, issue_type=epic_type).exists()
