# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# PP-85 follow-up: gate every epic endpoint (external SDK/MCP, API-key
# authenticated) behind the project's "Epics" toggle
# (Project.is_issue_type_enabled). Mirrors
# plane.tests.contract.app.test_iw_epic_gate for the web endpoints.

import uuid

import pytest
from rest_framework import status

from plane.db.models import Issue, IssueType, Project, ProjectMember, Workspace, WorkspaceMember

EPICS_DISABLED_ERROR = {"error": "Epics are not enabled for this project"}


def epics_url(workspace_slug: str, project_id) -> str:
    return f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}/iw-epics/"


def epic_detail_url(workspace_slug: str, project_id, epic_id) -> str:
    return f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}/iw-epics/{epic_id}/"


def epic_analytics_url(workspace_slug: str, project_id, epic_id) -> str:
    return f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}/iw-epics/{epic_id}/analytics/"


@pytest.fixture
def gate_workspace(create_user):
    workspace = Workspace.objects.create(
        name="PP-85 API gate workspace",
        owner=create_user,
        slug=f"pp-85-api-gate-ws-{uuid.uuid4().hex[:8]}",
    )
    WorkspaceMember.objects.create(workspace=workspace, member=create_user, role=20)
    return workspace


@pytest.fixture
def epics_disabled_project(gate_workspace, create_user):
    project = Project.objects.create(
        name="API epics disabled project",
        identifier="AEDP",
        workspace=gate_workspace,
        is_issue_type_enabled=False,
        created_by=create_user,
        updated_by=create_user,
    )
    ProjectMember.objects.create(project=project, workspace=gate_workspace, member=create_user, role=20)
    return project


@pytest.fixture
def epic_type(gate_workspace):
    return IssueType.objects.create(workspace=gate_workspace, name="Epic", is_epic=True)


@pytest.fixture
def existing_epic(epics_disabled_project, gate_workspace, epic_type, create_user):
    return Issue.objects.create(
        name="Pre-existing API epic",
        project=epics_disabled_project,
        workspace=gate_workspace,
        type=epic_type,
        created_by=create_user,
    )


@pytest.mark.contract
@pytest.mark.django_db
class TestEpicListCreateAPIEndpointGatedWhenDisabled:
    def test_list_returns_400(self, api_key_client, gate_workspace, epics_disabled_project):
        response = api_key_client.get(epics_url(gate_workspace.slug, epics_disabled_project.id))
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == EPICS_DISABLED_ERROR

    def test_create_returns_400_and_performs_no_write(
        self, api_key_client, gate_workspace, epics_disabled_project
    ):
        before_count = Issue.all_objects.filter(project=epics_disabled_project).count()

        response = api_key_client.post(
            epics_url(gate_workspace.slug, epics_disabled_project.id),
            {"name": "Should not be created via API"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == EPICS_DISABLED_ERROR
        assert Issue.all_objects.filter(project=epics_disabled_project).count() == before_count


@pytest.mark.contract
@pytest.mark.django_db
class TestEpicDetailAPIEndpointGatedWhenDisabled:
    def test_retrieve_returns_400(self, api_key_client, gate_workspace, epics_disabled_project, existing_epic):
        response = api_key_client.get(
            epic_detail_url(gate_workspace.slug, epics_disabled_project.id, existing_epic.id)
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == EPICS_DISABLED_ERROR

    def test_update_returns_400_and_performs_no_write(
        self, api_key_client, gate_workspace, epics_disabled_project, existing_epic
    ):
        response = api_key_client.patch(
            epic_detail_url(gate_workspace.slug, epics_disabled_project.id, existing_epic.id),
            {"name": "Renamed via API while disabled"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == EPICS_DISABLED_ERROR
        existing_epic.refresh_from_db()
        assert existing_epic.name == "Pre-existing API epic"

    def test_delete_returns_400_and_performs_no_write(
        self, api_key_client, gate_workspace, epics_disabled_project, existing_epic
    ):
        response = api_key_client.delete(
            epic_detail_url(gate_workspace.slug, epics_disabled_project.id, existing_epic.id)
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == EPICS_DISABLED_ERROR
        assert Issue.all_objects.filter(pk=existing_epic.id).exists()


@pytest.mark.contract
@pytest.mark.django_db
class TestEpicAnalyticsAPIEndpointGatedWhenDisabled:
    def test_analytics_returns_400(self, api_key_client, gate_workspace, epics_disabled_project, existing_epic):
        response = api_key_client.get(
            epic_analytics_url(gate_workspace.slug, epics_disabled_project.id, existing_epic.id)
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == EPICS_DISABLED_ERROR


@pytest.mark.contract
@pytest.mark.django_db
class TestEpicAPIHappyPathWhenEnabled:
    def test_create_returns_201_with_epic_type_when_enabled(self, api_key_client, gate_workspace, create_user):
        project = Project.objects.create(
            name="API epics enabled project",
            identifier="AEEP",
            workspace=gate_workspace,
            is_issue_type_enabled=True,
            created_by=create_user,
            updated_by=create_user,
        )
        ProjectMember.objects.create(project=project, workspace=gate_workspace, member=create_user, role=20)
        # Provisioned automatically by plane.iw.signals when the project was created above.
        epic_type = IssueType.objects.get(workspace=gate_workspace, is_epic=True)

        response = api_key_client.post(
            epics_url(gate_workspace.slug, project.id),
            {"name": "Enabled API epic"},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        issue = Issue.objects.get(id=response.json()["id"])
        assert issue.type_id == epic_type.id
