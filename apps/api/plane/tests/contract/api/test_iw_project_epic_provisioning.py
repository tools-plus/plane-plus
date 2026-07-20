# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# PP-85 follow-up (Part A, Finding 1): provisioning the workspace Epic
# IssueType is handled by a single Project post_save signal
# (plane.iw.signals.provision_epic_type_on_enable), which fires regardless
# of which HTTP path saved the project. This file covers the two API-v1
# (external, API-key authenticated) paths that can flip
# Project.is_issue_type_enabled on: ProjectListCreateAPIEndpoint.post and
# ProjectDetailAPIEndpoint.patch. The app-side paths (ProjectViewSet.create
# / partial_update) are covered by
# plane.tests.contract.app.test_iw_project_epic_provisioning.

import uuid

import pytest
from rest_framework import status

from plane.db.models import IssueType, Project, ProjectIssueType, ProjectMember, Workspace, WorkspaceMember


def project_list_create_url(workspace_slug: str) -> str:
    return f"/api/v1/workspaces/{workspace_slug}/projects/"


def project_detail_url(workspace_slug: str, project_id) -> str:
    return f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}/"


@pytest.fixture
def provisioning_workspace(create_user):
    workspace = Workspace.objects.create(
        name="PP-85 API provisioning workspace",
        owner=create_user,
        slug=f"pp-85-api-provision-ws-{uuid.uuid4().hex[:8]}",
    )
    WorkspaceMember.objects.create(workspace=workspace, member=create_user, role=20)
    return workspace


@pytest.mark.contract
@pytest.mark.django_db
class TestProjectCreateAPIEndpointProvisionsEpicType:
    def test_creating_project_with_epics_enabled_provisions_epic_type_and_link(
        self, api_key_client, provisioning_workspace
    ):
        assert IssueType.objects.filter(workspace=provisioning_workspace, is_epic=True).count() == 0

        url = project_list_create_url(provisioning_workspace.slug)
        response = api_key_client.post(
            url,
            {
                "name": "API Epics On At Create",
                "identifier": "AEOAC",
                "is_issue_type_enabled": True,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        project_id = response.json()["id"]

        epic_types = IssueType.objects.filter(workspace=provisioning_workspace, is_epic=True)
        assert epic_types.count() == 1
        assert ProjectIssueType.objects.filter(project_id=project_id, issue_type=epic_types.first()).count() == 1

    def test_creating_project_with_epics_disabled_provisions_nothing(self, api_key_client, provisioning_workspace):
        url = project_list_create_url(provisioning_workspace.slug)
        response = api_key_client.post(
            url,
            {"name": "API Epics Off At Create", "identifier": "AEOFC"},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert IssueType.objects.filter(workspace=provisioning_workspace, is_epic=True).count() == 0


@pytest.mark.contract
@pytest.mark.django_db
class TestProjectUpdateAPIEndpointProvisionsEpicType:
    def test_enabling_epics_toggle_provisions_epic_type_and_link(
        self, api_key_client, provisioning_workspace, create_user
    ):
        project = Project.objects.create(
            name="API Toggle Epics Project",
            identifier="ATEP",
            workspace=provisioning_workspace,
            is_issue_type_enabled=False,
        )
        ProjectMember.objects.create(
            project=project, workspace=provisioning_workspace, member=create_user, role=20, is_active=True
        )

        assert IssueType.objects.filter(workspace=provisioning_workspace, is_epic=True).count() == 0

        url = project_detail_url(provisioning_workspace.slug, project.id)
        response = api_key_client.patch(url, {"is_issue_type_enabled": True}, format="json")

        assert response.status_code == status.HTTP_200_OK

        epic_types = IssueType.objects.filter(workspace=provisioning_workspace, is_epic=True)
        assert epic_types.count() == 1
        assert ProjectIssueType.objects.filter(project=project, issue_type=epic_types.first()).count() == 1

    def test_re_saving_with_toggle_already_on_does_not_duplicate(
        self, api_key_client, provisioning_workspace, create_user
    ):
        project = Project.objects.create(
            name="API Idempotent Epics Project",
            identifier="AIEP",
            workspace=provisioning_workspace,
            is_issue_type_enabled=False,
        )
        ProjectMember.objects.create(
            project=project, workspace=provisioning_workspace, member=create_user, role=20, is_active=True
        )

        url = project_detail_url(provisioning_workspace.slug, project.id)
        first = api_key_client.patch(url, {"is_issue_type_enabled": True}, format="json")
        assert first.status_code == status.HTTP_200_OK

        second = api_key_client.patch(
            url, {"is_issue_type_enabled": True, "description": "second save"}, format="json"
        )
        assert second.status_code == status.HTTP_200_OK

        assert IssueType.objects.filter(workspace=provisioning_workspace, is_epic=True).count() == 1
        assert ProjectIssueType.objects.filter(project=project).count() == 1

    def test_toggle_left_off_does_not_provision_epic_type(
        self, api_key_client, provisioning_workspace, create_user
    ):
        project = Project.objects.create(
            name="API No Epics Project",
            identifier="ANEP",
            workspace=provisioning_workspace,
            is_issue_type_enabled=False,
        )
        ProjectMember.objects.create(
            project=project, workspace=provisioning_workspace, member=create_user, role=20, is_active=True
        )

        url = project_detail_url(provisioning_workspace.slug, project.id)
        response = api_key_client.patch(url, {"description": "no epics here via api"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert IssueType.objects.filter(workspace=provisioning_workspace, is_epic=True).count() == 0
