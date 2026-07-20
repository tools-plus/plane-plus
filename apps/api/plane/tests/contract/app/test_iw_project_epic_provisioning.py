# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# PP-85 regression: turning on the "Epics" project setting
# (Project.is_issue_type_enabled=True) must provision a workspace Epic
# IssueType (and link it to the project) so that a subsequent epic creation
# on that project has a type to attach to. Before the fix, projects/
# workspaces created (or toggled on) after the original iw_002 seed
# migration ran never got an Epic type, and epic creation 500'd.
#
# PP-85 follow-up (Part A): provisioning is now handled by a single Project
# post_save signal (plane.iw.signals.provision_epic_type_on_enable), so it
# fires for every path that can flip is_issue_type_enabled on -- not just
# ProjectViewSet.partial_update (tested below) but also ProjectViewSet.create
# (TestProjectCreateProvisionsEpicType below) and the API-v1 endpoints
# (see plane.tests.contract.api.test_iw_project_epic_provisioning).

import uuid

import pytest
from rest_framework import status

from plane.db.models import IssueType, Project, ProjectIssueType, ProjectMember, Workspace, WorkspaceMember


def project_list_create_url(workspace_slug: str) -> str:
    return f"/api/workspaces/{workspace_slug}/projects/"


def project_detail_url(workspace_slug: str, project_id) -> str:
    return f"/api/workspaces/{workspace_slug}/projects/{project_id}/"


@pytest.fixture
def provisioning_workspace(create_user):
    workspace = Workspace.objects.create(
        name="PP-85 provisioning workspace",
        owner=create_user,
        slug=f"pp-85-provision-ws-{uuid.uuid4().hex[:8]}",
    )
    WorkspaceMember.objects.create(workspace=workspace, member=create_user, role=20)
    return workspace


@pytest.mark.contract
@pytest.mark.django_db
class TestProjectPartialUpdateProvisionsEpicType:
    def test_enabling_epics_toggle_provisions_epic_type_and_link(
        self, session_client, provisioning_workspace, create_user
    ):
        project = Project.objects.create(
            name="Toggle Epics Project",
            identifier="TEP",
            workspace=provisioning_workspace,
            is_issue_type_enabled=False,
        )
        ProjectMember.objects.create(
            project=project, workspace=provisioning_workspace, member=create_user, role=20, is_active=True
        )

        assert IssueType.objects.filter(workspace=provisioning_workspace, is_epic=True).count() == 0

        url = project_detail_url(provisioning_workspace.slug, project.id)
        response = session_client.patch(url, {"is_issue_type_enabled": True}, format="json")

        assert response.status_code == status.HTTP_200_OK

        epic_types = IssueType.objects.filter(workspace=provisioning_workspace, is_epic=True)
        assert epic_types.count() == 1
        epic_type = epic_types.first()
        assert ProjectIssueType.objects.filter(project=project, issue_type=epic_type).count() == 1

    def test_re_saving_with_toggle_already_on_does_not_duplicate(
        self, session_client, provisioning_workspace, create_user
    ):
        """Idempotency at the HTTP layer: patching twice with is_issue_type_enabled=True must not duplicate rows."""
        project = Project.objects.create(
            name="Idempotent Epics Project",
            identifier="IEP",
            workspace=provisioning_workspace,
            is_issue_type_enabled=False,
        )
        ProjectMember.objects.create(
            project=project, workspace=provisioning_workspace, member=create_user, role=20, is_active=True
        )

        url = project_detail_url(provisioning_workspace.slug, project.id)
        first = session_client.patch(url, {"is_issue_type_enabled": True}, format="json")
        assert first.status_code == status.HTTP_200_OK

        second = session_client.patch(url, {"is_issue_type_enabled": True, "description": "second save"}, format="json")
        assert second.status_code == status.HTTP_200_OK

        assert IssueType.objects.filter(workspace=provisioning_workspace, is_epic=True).count() == 1
        assert ProjectIssueType.objects.filter(project=project).count() == 1

    def test_toggle_left_off_does_not_provision_epic_type(
        self, session_client, provisioning_workspace, create_user
    ):
        """Sanity check: only the True path provisions -- untouched/False projects get nothing."""
        project = Project.objects.create(
            name="No Epics Project",
            identifier="NEP",
            workspace=provisioning_workspace,
            is_issue_type_enabled=False,
        )
        ProjectMember.objects.create(
            project=project, workspace=provisioning_workspace, member=create_user, role=20, is_active=True
        )

        url = project_detail_url(provisioning_workspace.slug, project.id)
        response = session_client.patch(url, {"description": "no epics here"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert IssueType.objects.filter(workspace=provisioning_workspace, is_epic=True).count() == 0


@pytest.mark.contract
@pytest.mark.django_db
class TestProjectCreateProvisionsEpicType:
    """PP-85 Finding 1: ProjectViewSet.create can also set is_issue_type_enabled=True
    on the initial payload -- it must provision the epic type too, not just partial_update."""

    def test_creating_project_with_epics_enabled_provisions_epic_type_and_link(
        self, session_client, provisioning_workspace
    ):
        assert IssueType.objects.filter(workspace=provisioning_workspace, is_epic=True).count() == 0

        url = project_list_create_url(provisioning_workspace.slug)
        response = session_client.post(
            url,
            {
                "name": "Epics On At Create",
                "identifier": "EOAC",
                "is_issue_type_enabled": True,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        project_id = response.json()["id"]

        epic_types = IssueType.objects.filter(workspace=provisioning_workspace, is_epic=True)
        assert epic_types.count() == 1
        assert ProjectIssueType.objects.filter(project_id=project_id, issue_type=epic_types.first()).count() == 1

    def test_creating_project_with_epics_disabled_provisions_nothing(
        self, session_client, provisioning_workspace
    ):
        url = project_list_create_url(provisioning_workspace.slug)
        response = session_client.post(
            url,
            {"name": "Epics Off At Create", "identifier": "EOFC"},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert IssueType.objects.filter(workspace=provisioning_workspace, is_epic=True).count() == 0
