# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# PP-85 follow-up: gate every epic endpoint (web) behind the project's
# "Epics" toggle (Project.is_issue_type_enabled). With the toggle off, every
# epic endpoint -- reads and writes alike -- must return a clean
# `{"error": "Epics are not enabled for this project"}` 400 instead of
# operating on (or exposing) epic data. Existing epics are left in the
# database untouched; only access is gated.

import uuid

import pytest
from rest_framework import status

from plane.db.models import Issue, IssueType, Project, ProjectMember, Workspace, WorkspaceMember

EPICS_DISABLED_ERROR = {"error": "Epics are not enabled for this project"}


def epics_url(workspace_slug: str, project_id) -> str:
    return f"/api/workspaces/{workspace_slug}/projects/{project_id}/epics/"


def epic_detail_url(workspace_slug: str, project_id, epic_id) -> str:
    return f"/api/workspaces/{workspace_slug}/projects/{project_id}/epics/{epic_id}/"


def epic_analytics_url(workspace_slug: str, project_id, epic_id) -> str:
    return f"/api/workspaces/{workspace_slug}/projects/{project_id}/epics/{epic_id}/analytics/"


def epic_list_endpoint_url(workspace_slug: str, project_id) -> str:
    return f"/api/workspaces/{workspace_slug}/projects/{project_id}/epics/list/"


def epic_sub_issues_url(workspace_slug: str, project_id, epic_id) -> str:
    return f"/api/workspaces/{workspace_slug}/projects/{project_id}/epics/{epic_id}/sub-issues/"


def epic_issues_url(workspace_slug: str, project_id, epic_id) -> str:
    return f"/api/workspaces/{workspace_slug}/projects/{project_id}/epics/{epic_id}/issues/"


def epic_history_url(workspace_slug: str, project_id, epic_id) -> str:
    return f"/api/workspaces/{workspace_slug}/projects/{project_id}/epics/{epic_id}/history/"


@pytest.fixture
def gate_workspace(create_user):
    workspace = Workspace.objects.create(
        name="PP-85 gate workspace",
        owner=create_user,
        slug=f"pp-85-gate-ws-{uuid.uuid4().hex[:8]}",
    )
    WorkspaceMember.objects.create(workspace=workspace, member=create_user, role=20)
    return workspace


@pytest.fixture
def epics_disabled_project(gate_workspace, create_user):
    """A project with the Epics toggle off, in a workspace that already has an Epic type
    (e.g. left over from before the toggle was turned off) -- proving the gate, not the
    type-presence check, is what blocks access."""
    project = Project.objects.create(
        name="Epics disabled project",
        identifier="EDP",
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
    """An epic created while epics were enabled, then the project's toggle was flipped off.
    Existing epic data must be gated, not deleted -- see PP-85 contract."""
    return Issue.objects.create(
        name="Pre-existing epic",
        project=epics_disabled_project,
        workspace=gate_workspace,
        type=epic_type,
        created_by=create_user,
    )


@pytest.mark.contract
@pytest.mark.django_db
class TestIwEpicViewSetGatedWhenDisabled:
    def test_list_returns_400(self, session_client, gate_workspace, epics_disabled_project):
        response = session_client.get(epics_url(gate_workspace.slug, epics_disabled_project.id))
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == EPICS_DISABLED_ERROR

    def test_create_returns_400_and_performs_no_write(
        self, session_client, gate_workspace, epics_disabled_project
    ):
        before_count = Issue.all_objects.filter(project=epics_disabled_project).count()

        response = session_client.post(
            epics_url(gate_workspace.slug, epics_disabled_project.id),
            {"name": "Should not be created"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == EPICS_DISABLED_ERROR
        assert Issue.all_objects.filter(project=epics_disabled_project).count() == before_count

    def test_retrieve_returns_400(self, session_client, gate_workspace, epics_disabled_project, existing_epic):
        response = session_client.get(
            epic_detail_url(gate_workspace.slug, epics_disabled_project.id, existing_epic.id)
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == EPICS_DISABLED_ERROR

    def test_update_returns_400_and_performs_no_write(
        self, session_client, gate_workspace, epics_disabled_project, existing_epic
    ):
        response = session_client.patch(
            epic_detail_url(gate_workspace.slug, epics_disabled_project.id, existing_epic.id),
            {"name": "Renamed while disabled"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == EPICS_DISABLED_ERROR
        existing_epic.refresh_from_db()
        assert existing_epic.name == "Pre-existing epic"

    def test_delete_returns_400_and_performs_no_write(
        self, session_client, gate_workspace, epics_disabled_project, existing_epic
    ):
        response = session_client.delete(
            epic_detail_url(gate_workspace.slug, epics_disabled_project.id, existing_epic.id)
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == EPICS_DISABLED_ERROR
        assert Issue.all_objects.filter(pk=existing_epic.id).exists()

    def test_analytics_returns_400(self, session_client, gate_workspace, epics_disabled_project, existing_epic):
        response = session_client.get(
            epic_analytics_url(gate_workspace.slug, epics_disabled_project.id, existing_epic.id)
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == EPICS_DISABLED_ERROR


@pytest.mark.contract
@pytest.mark.django_db
class TestIwEpicListEndpointGatedWhenDisabled:
    def test_non_paginated_list_returns_400(self, session_client, gate_workspace, epics_disabled_project):
        response = session_client.get(epic_list_endpoint_url(gate_workspace.slug, epics_disabled_project.id))
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == EPICS_DISABLED_ERROR


@pytest.mark.contract
@pytest.mark.django_db
class TestIwEpicSubIssuesAndHistoryGatedWhenDisabled:
    """The sub-issues, child-issues, and history routes under /epics/ reuse the
    generic SubIssuesEndpoint / IssueActivityEndpoint views (see
    plane.app.urls.iw_epic) via epic-specific gated subclasses
    (IwEpicSubIssuesEndpoint / IwEpicActivityEndpoint)."""

    def test_sub_issues_get_returns_400(self, session_client, gate_workspace, epics_disabled_project, existing_epic):
        response = session_client.get(
            epic_sub_issues_url(gate_workspace.slug, epics_disabled_project.id, existing_epic.id)
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == EPICS_DISABLED_ERROR

    def test_sub_issues_post_returns_400_and_performs_no_write(
        self, session_client, gate_workspace, epics_disabled_project, existing_epic, create_user
    ):
        other_issue = Issue.objects.create(
            name="Would-be child",
            project=epics_disabled_project,
            workspace=gate_workspace,
            created_by=create_user,
        )

        response = session_client.post(
            epic_sub_issues_url(gate_workspace.slug, epics_disabled_project.id, existing_epic.id),
            {"sub_issue_ids": [str(other_issue.id)]},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == EPICS_DISABLED_ERROR
        other_issue.refresh_from_db()
        assert other_issue.parent_id is None

    def test_epic_child_issues_get_returns_400(
        self, session_client, gate_workspace, epics_disabled_project, existing_epic
    ):
        response = session_client.get(
            epic_issues_url(gate_workspace.slug, epics_disabled_project.id, existing_epic.id)
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == EPICS_DISABLED_ERROR

    def test_history_get_returns_400(self, session_client, gate_workspace, epics_disabled_project, existing_epic):
        response = session_client.get(
            epic_history_url(gate_workspace.slug, epics_disabled_project.id, existing_epic.id)
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == EPICS_DISABLED_ERROR


@pytest.mark.contract
@pytest.mark.django_db
class TestIwEpicGateRestoredOnReEnable:
    def test_re_enabling_epics_restores_access_to_existing_epic(
        self, session_client, gate_workspace, epics_disabled_project, existing_epic
    ):
        """Gating never deletes epic data -- flipping the toggle back on must immediately
        restore access to epics that existed the whole time."""
        blocked = session_client.get(
            epic_detail_url(gate_workspace.slug, epics_disabled_project.id, existing_epic.id)
        )
        assert blocked.status_code == status.HTTP_400_BAD_REQUEST

        epics_disabled_project.is_issue_type_enabled = True
        epics_disabled_project.save()

        restored = session_client.get(
            epic_detail_url(gate_workspace.slug, epics_disabled_project.id, existing_epic.id)
        )
        assert restored.status_code == status.HTTP_200_OK
        assert restored.json()["id"] == str(existing_epic.id)
