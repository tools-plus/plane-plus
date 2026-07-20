# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# PP-85 follow-up (F1): the epic *sub-resource* routes mounted under
# /epics/<issue_id>/... -- comments, reactions, issue-links, attachments
# (v1 + v2), and epics-user-properties -- reuse the same shared upstream
# viewsets/endpoints as regular (non-epic) work items. Those shared views
# have no notion of the "Epics" toggle themselves, so plane.app.urls.iw_epic
# wires in epic-specific gated subclasses (Iw*ViewSet/Iw*Endpoint, see
# plane.app.views.issue.iw_epic) that assert epics are enabled before any
# handler runs. With the toggle off, every one of these routes -- reads and
# writes alike -- must return the same clean
# `{"error": "Epics are not enabled for this project"}` 400 and perform no
# write, exactly like the top-level epic endpoints covered by
# test_iw_epic_gate.py.

import uuid

import pytest
from rest_framework import status

from plane.db.models import (
    FileAsset,
    Issue,
    IssueComment,
    IssueLink,
    IssueReaction,
    IssueType,
    Project,
    ProjectMember,
    ProjectUserProperty,
    Workspace,
    WorkspaceMember,
)

EPICS_DISABLED_ERROR = {"error": "Epics are not enabled for this project"}


def comments_url(workspace_slug: str, project_id, issue_id) -> str:
    return f"/api/workspaces/{workspace_slug}/projects/{project_id}/epics/{issue_id}/comments/"


def comment_detail_url(workspace_slug: str, project_id, issue_id, pk) -> str:
    return f"/api/workspaces/{workspace_slug}/projects/{project_id}/epics/{issue_id}/comments/{pk}/"


def reactions_url(workspace_slug: str, project_id, issue_id) -> str:
    return f"/api/workspaces/{workspace_slug}/projects/{project_id}/epics/{issue_id}/reactions/"


def reaction_delete_url(workspace_slug: str, project_id, issue_id, reaction_code) -> str:
    return f"/api/workspaces/{workspace_slug}/projects/{project_id}/epics/{issue_id}/reactions/{reaction_code}/"


def links_url(workspace_slug: str, project_id, issue_id) -> str:
    return f"/api/workspaces/{workspace_slug}/projects/{project_id}/epics/{issue_id}/issue-links/"


def link_detail_url(workspace_slug: str, project_id, issue_id, pk) -> str:
    return f"/api/workspaces/{workspace_slug}/projects/{project_id}/epics/{issue_id}/issue-links/{pk}/"


def attachments_url(workspace_slug: str, project_id, issue_id) -> str:
    return f"/api/workspaces/{workspace_slug}/projects/{project_id}/epics/{issue_id}/issue-attachments/"


def attachment_detail_url(workspace_slug: str, project_id, issue_id, pk) -> str:
    return f"/api/workspaces/{workspace_slug}/projects/{project_id}/epics/{issue_id}/issue-attachments/{pk}/"


def attachments_v2_url(workspace_slug: str, project_id, issue_id) -> str:
    return f"/api/assets/v2/workspaces/{workspace_slug}/projects/{project_id}/epics/{issue_id}/attachments/"


def attachment_v2_detail_url(workspace_slug: str, project_id, issue_id, pk) -> str:
    return f"/api/assets/v2/workspaces/{workspace_slug}/projects/{project_id}/epics/{issue_id}/attachments/{pk}/"


def user_properties_url(workspace_slug: str, project_id) -> str:
    return f"/api/workspaces/{workspace_slug}/projects/{project_id}/epics-user-properties/"


@pytest.fixture
def gate_workspace(create_user):
    workspace = Workspace.objects.create(
        name="PP-85 sub-resource gate workspace",
        owner=create_user,
        slug=f"pp-85-subres-gate-ws-{uuid.uuid4().hex[:8]}",
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
        identifier="SRG",
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
    """An epic created while epics were enabled, then the project's toggle was flipped off."""
    return Issue.objects.create(
        name="Pre-existing epic",
        project=epics_disabled_project,
        workspace=gate_workspace,
        type=epic_type,
        created_by=create_user,
    )


@pytest.mark.contract
@pytest.mark.django_db
class TestIwEpicCommentsGatedWhenDisabled:
    def test_list_returns_400(self, session_client, gate_workspace, epics_disabled_project, existing_epic):
        response = session_client.get(comments_url(gate_workspace.slug, epics_disabled_project.id, existing_epic.id))
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == EPICS_DISABLED_ERROR

    def test_create_returns_400_and_performs_no_write(
        self, session_client, gate_workspace, epics_disabled_project, existing_epic
    ):
        before_count = IssueComment.objects.filter(issue=existing_epic).count()

        response = session_client.post(
            comments_url(gate_workspace.slug, epics_disabled_project.id, existing_epic.id),
            {"comment_html": "<p>Should not be created</p>"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == EPICS_DISABLED_ERROR
        assert IssueComment.objects.filter(issue=existing_epic).count() == before_count

    def test_delete_returns_400_and_performs_no_write(
        self, session_client, gate_workspace, epics_disabled_project, existing_epic, create_user
    ):
        comment = IssueComment.objects.create(
            issue=existing_epic,
            project=epics_disabled_project,
            workspace=gate_workspace,
            actor=create_user,
            comment_html="<p>Existing comment</p>",
            created_by=create_user,
        )

        response = session_client.delete(
            comment_detail_url(gate_workspace.slug, epics_disabled_project.id, existing_epic.id, comment.id)
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == EPICS_DISABLED_ERROR
        assert IssueComment.objects.filter(pk=comment.id).exists()


@pytest.mark.contract
@pytest.mark.django_db
class TestIwEpicReactionsGatedWhenDisabled:
    def test_list_returns_400(self, session_client, gate_workspace, epics_disabled_project, existing_epic):
        response = session_client.get(reactions_url(gate_workspace.slug, epics_disabled_project.id, existing_epic.id))
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == EPICS_DISABLED_ERROR

    def test_create_returns_400_and_performs_no_write(
        self, session_client, gate_workspace, epics_disabled_project, existing_epic
    ):
        before_count = IssueReaction.objects.filter(issue=existing_epic).count()

        response = session_client.post(
            reactions_url(gate_workspace.slug, epics_disabled_project.id, existing_epic.id),
            {"reaction": "\U0001F600"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == EPICS_DISABLED_ERROR
        assert IssueReaction.objects.filter(issue=existing_epic).count() == before_count

    def test_delete_returns_400_and_performs_no_write(
        self, session_client, gate_workspace, epics_disabled_project, existing_epic, create_user
    ):
        reaction = IssueReaction.objects.create(
            issue=existing_epic,
            project=epics_disabled_project,
            workspace=gate_workspace,
            actor=create_user,
            reaction="\U0001F600",
            created_by=create_user,
        )

        response = session_client.delete(
            reaction_delete_url(
                gate_workspace.slug, epics_disabled_project.id, existing_epic.id, reaction.reaction
            )
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == EPICS_DISABLED_ERROR
        assert IssueReaction.objects.filter(pk=reaction.id).exists()


@pytest.mark.contract
@pytest.mark.django_db
class TestIwEpicLinksGatedWhenDisabled:
    def test_list_returns_400(self, session_client, gate_workspace, epics_disabled_project, existing_epic):
        response = session_client.get(links_url(gate_workspace.slug, epics_disabled_project.id, existing_epic.id))
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == EPICS_DISABLED_ERROR

    def test_create_returns_400_and_performs_no_write(
        self, session_client, gate_workspace, epics_disabled_project, existing_epic
    ):
        before_count = IssueLink.objects.filter(issue=existing_epic).count()

        response = session_client.post(
            links_url(gate_workspace.slug, epics_disabled_project.id, existing_epic.id),
            {"url": "https://example.com/should-not-be-created"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == EPICS_DISABLED_ERROR
        assert IssueLink.objects.filter(issue=existing_epic).count() == before_count

    def test_update_returns_400_and_performs_no_write(
        self, session_client, gate_workspace, epics_disabled_project, existing_epic, create_user
    ):
        link = IssueLink.objects.create(
            issue=existing_epic,
            project=epics_disabled_project,
            workspace=gate_workspace,
            url="https://example.com/original",
            created_by=create_user,
        )

        response = session_client.patch(
            link_detail_url(gate_workspace.slug, epics_disabled_project.id, existing_epic.id, link.id),
            {"url": "https://example.com/renamed-while-disabled"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == EPICS_DISABLED_ERROR
        link.refresh_from_db()
        assert link.url == "https://example.com/original"

    def test_delete_returns_400_and_performs_no_write(
        self, session_client, gate_workspace, epics_disabled_project, existing_epic, create_user
    ):
        link = IssueLink.objects.create(
            issue=existing_epic,
            project=epics_disabled_project,
            workspace=gate_workspace,
            url="https://example.com/original",
            created_by=create_user,
        )

        response = session_client.delete(
            link_detail_url(gate_workspace.slug, epics_disabled_project.id, existing_epic.id, link.id)
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == EPICS_DISABLED_ERROR
        assert IssueLink.objects.filter(pk=link.id).exists()


@pytest.mark.contract
@pytest.mark.django_db
class TestIwEpicAttachmentsGatedWhenDisabled:
    def test_get_returns_400(self, session_client, gate_workspace, epics_disabled_project, existing_epic):
        response = session_client.get(
            attachments_url(gate_workspace.slug, epics_disabled_project.id, existing_epic.id)
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == EPICS_DISABLED_ERROR

    def test_post_returns_400_and_performs_no_write(
        self, session_client, gate_workspace, epics_disabled_project, existing_epic
    ):
        before_count = FileAsset.objects.filter(issue_id=existing_epic.id).count()

        response = session_client.post(
            attachments_url(gate_workspace.slug, epics_disabled_project.id, existing_epic.id),
            {"asset": "should-not-be-created.txt", "attributes": {}},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == EPICS_DISABLED_ERROR
        assert FileAsset.objects.filter(issue_id=existing_epic.id).count() == before_count

    def test_delete_returns_400_and_performs_no_write(
        self, session_client, gate_workspace, epics_disabled_project, existing_epic, create_user
    ):
        attachment = FileAsset.objects.create(
            issue_id=existing_epic.id,
            project=epics_disabled_project,
            workspace=gate_workspace,
            asset="pre-existing.txt",
            entity_type=FileAsset.EntityTypeContext.ISSUE_ATTACHMENT,
            created_by=create_user,
        )

        response = session_client.delete(
            attachment_detail_url(
                gate_workspace.slug, epics_disabled_project.id, existing_epic.id, attachment.id
            )
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == EPICS_DISABLED_ERROR
        assert FileAsset.objects.filter(pk=attachment.id).exists()


@pytest.mark.contract
@pytest.mark.django_db
class TestIwEpicAttachmentsV2GatedWhenDisabled:
    def test_get_returns_400(self, session_client, gate_workspace, epics_disabled_project, existing_epic):
        response = session_client.get(
            attachments_v2_url(gate_workspace.slug, epics_disabled_project.id, existing_epic.id)
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == EPICS_DISABLED_ERROR

    def test_post_returns_400_and_performs_no_write(
        self, session_client, gate_workspace, epics_disabled_project, existing_epic
    ):
        before_count = FileAsset.objects.filter(issue_id=existing_epic.id).count()

        response = session_client.post(
            attachments_v2_url(gate_workspace.slug, epics_disabled_project.id, existing_epic.id),
            {"name": "should-not-be-created.txt", "type": "text/plain", "size": 10},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == EPICS_DISABLED_ERROR
        assert FileAsset.objects.filter(issue_id=existing_epic.id).count() == before_count

    def test_delete_returns_400_and_performs_no_write(
        self, session_client, gate_workspace, epics_disabled_project, existing_epic, create_user
    ):
        attachment = FileAsset.objects.create(
            issue_id=existing_epic.id,
            project=epics_disabled_project,
            workspace=gate_workspace,
            asset="pre-existing.txt",
            entity_type=FileAsset.EntityTypeContext.ISSUE_ATTACHMENT,
            created_by=create_user,
        )

        response = session_client.delete(
            attachment_v2_detail_url(
                gate_workspace.slug, epics_disabled_project.id, existing_epic.id, attachment.id
            )
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == EPICS_DISABLED_ERROR
        attachment.refresh_from_db()
        assert attachment.is_deleted is False


@pytest.mark.contract
@pytest.mark.django_db
class TestIwEpicUserDisplayPropertiesGatedWhenDisabled:
    def test_get_returns_400(self, session_client, gate_workspace, epics_disabled_project):
        response = session_client.get(user_properties_url(gate_workspace.slug, epics_disabled_project.id))
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == EPICS_DISABLED_ERROR

    def test_patch_returns_400_and_performs_no_write(
        self, session_client, gate_workspace, epics_disabled_project, create_user
    ):
        before_count = ProjectUserProperty.objects.filter(
            user=create_user, project=epics_disabled_project
        ).count()

        response = session_client.patch(
            user_properties_url(gate_workspace.slug, epics_disabled_project.id),
            {"filters": {}},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == EPICS_DISABLED_ERROR
        assert (
            ProjectUserProperty.objects.filter(user=create_user, project=epics_disabled_project).count()
            == before_count
        )
