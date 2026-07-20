# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# PP-85 regression tests: epic creation used to 500 when a workspace had no
# Epic IssueType provisioned (IwEpicViewSet.create set request.data["type"]
# only when an epic type was found, silently falling through to a typeless
# Issue create whose subsequent re-fetch -- filtered on type__is_epic=True --
# returned nothing, which then blew up user_timezone_converter on a None
# queryset). The fix:
#   - returns a clean 400 instead of a 500 when no epic type exists
#   - wraps the create in transaction.atomic() so no orphan Issue row is left
#   - succeeds (201) with the issue's `type` set to the epic type otherwise
#
# PP-85 follow-up (provisioning + gating): `epic_project` below is created
# with is_issue_type_enabled=True, so plane.iw.signals now auto-provisions
# the workspace's Epic IssueType as soon as the fixture is created (see
# plane.tests.unit.iw.test_provisioning and
# plane.tests.contract.app.test_iw_project_epic_provisioning for direct
# coverage of that signal). That makes "no epic type configured" unreachable
# through this fixture in the happy path -- TestIwEpicCreateMissingEpicTypeGuard
# below now explicitly deletes the auto-provisioned type first to exercise
# IwEpicViewSet.create's guard as the safety net it's meant to be.

import json
import uuid

import pytest
from rest_framework import status

from plane.db.models import Issue, IssueType, Project, ProjectMember, State, Workspace, WorkspaceMember


def epics_url(workspace_slug: str, project_id) -> str:
    return f"/api/workspaces/{workspace_slug}/projects/{project_id}/epics/"


@pytest.fixture
def epic_workspace(create_user):
    """A workspace the test user administers, with no Epic IssueType yet."""
    workspace = Workspace.objects.create(
        name="PP-85 epic workspace",
        owner=create_user,
        slug=f"pp-85-epic-ws-{uuid.uuid4().hex[:8]}",
    )
    WorkspaceMember.objects.create(workspace=workspace, member=create_user, role=20)
    return workspace


@pytest.fixture
def epic_project(epic_workspace, create_user):
    """A project in epic_workspace, with a default state so Issue.save() has something to attach to."""
    project = Project.objects.create(
        name="PP-85 epic project",
        identifier="PP85E",
        workspace=epic_workspace,
        is_issue_type_enabled=True,
        created_by=create_user,
        updated_by=create_user,
    )
    ProjectMember.objects.create(project=project, workspace=epic_workspace, member=create_user, role=20)
    State.objects.create(
        name="Backlog",
        group="backlog",
        project=project,
        workspace=epic_workspace,
        default=True,
        created_by=create_user,
    )
    return project


@pytest.mark.contract
@pytest.mark.django_db
class TestIwEpicCreateHappyPath:
    def test_create_epic_returns_201_with_epic_type(self, session_client, epic_workspace, epic_project, create_user):
        """With an Epic IssueType provisioned, epic creation succeeds and is tagged with that type."""
        # epic_project is created with is_issue_type_enabled=True, so
        # plane.iw.signals has already provisioned the workspace Epic type.
        epic_type = IssueType.objects.get(workspace=epic_workspace, is_epic=True)

        url = epics_url(epic_workspace.slug, epic_project.id)
        response = session_client.post(url, {"name": "My PP-85 Epic"}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        issue = Issue.objects.get(id=data["id"])
        assert issue.type_id == epic_type.id
        assert issue.type.is_epic is True
        assert issue.name == "My PP-85 Epic"

    def test_created_epic_is_visible_via_list(self, session_client, epic_workspace, epic_project, create_user):
        # epic_project already has an auto-provisioned Epic type (see above).
        url = epics_url(epic_workspace.slug, epic_project.id)
        create_resp = session_client.post(url, {"name": "Listed Epic"}, format="json")
        assert create_resp.status_code == status.HTTP_201_CREATED
        new_id = str(create_resp.json()["id"])

        list_resp = session_client.get(url)
        assert list_resp.status_code == status.HTTP_200_OK
        # The list endpoint's response shape varies with grouping/pagination params;
        # just assert the created epic's id shows up somewhere in the payload.
        assert new_id in json.dumps(list_resp.json())


@pytest.mark.contract
@pytest.mark.django_db
class TestIwEpicCreateMissingEpicTypeGuard:
    """
    PP-85 follow-up: with provisioning now happening automatically via
    plane.iw.signals on every project save with is_issue_type_enabled=True,
    epic_project's Epic type is already provisioned by fixture time -- so
    each test here explicitly removes it first to simulate the type
    genuinely being missing (e.g. a pre-provisioning-fix project, or manual
    data tampering) and confirm IwEpicViewSet.create's guard is still a
    working safety net.
    """

    def test_missing_epic_type_returns_400(self, session_client, epic_workspace, epic_project):
        """PP-85: no Epic IssueType configured -> clean 400, not a 500."""
        IssueType.objects.filter(workspace=epic_workspace, is_epic=True).delete()
        assert IssueType.objects.filter(workspace=epic_workspace, is_epic=True).count() == 0

        url = epics_url(epic_workspace.slug, epic_project.id)
        response = session_client.post(url, {"name": "Orphan epic attempt"}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {"error": "No epic issue type configured for this workspace"}

    def test_missing_epic_type_creates_no_orphan_issue(self, session_client, epic_workspace, epic_project):
        """PP-85 orphan regression: a rejected epic create must not leave a typeless Issue row behind."""
        IssueType.objects.filter(workspace=epic_workspace, is_epic=True).delete()
        before_count = Issue.all_objects.filter(project=epic_project).count()
        assert before_count == 0

        url = epics_url(epic_workspace.slug, epic_project.id)
        response = session_client.post(url, {"name": "Orphan epic attempt"}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        after_count = Issue.all_objects.filter(project=epic_project).count()
        assert after_count == before_count == 0

    def test_missing_epic_type_multiple_attempts_create_no_orphans(
        self, session_client, epic_workspace, epic_project
    ):
        """Regression for the exact repro: several failed attempts must not accumulate orphan rows."""
        IssueType.objects.filter(workspace=epic_workspace, is_epic=True).delete()
        url = epics_url(epic_workspace.slug, epic_project.id)

        for i in range(3):
            response = session_client.post(url, {"name": f"Orphan attempt {i}"}, format="json")
            assert response.status_code == status.HTTP_400_BAD_REQUEST

        assert Issue.all_objects.filter(project=epic_project).count() == 0
