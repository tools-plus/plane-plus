# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Contract tests for ``ProjectBulkAssetEndpoint.post``.

Verifies the fix in 7bf866274 ("restrict NULL-project asset claim to the
uploader"), which is itself a follow-up to 7ae505df9. The endpoint claims
assets (assigns project_id, and for PROJECT_COVER, sweeps them onto the
project's cover_image_asset_id) for a batch of asset_ids in one queryset:

    assets = FileAsset.objects.filter(id__in=asset_ids, workspace__slug=slug).filter(
        Q(project_id=project_id) | Q(project_id__isnull=True, created_by=request.user)
    )

Covers:
  - ALLOW: asset already belongs to the calling project.
  - ALLOW: NULL-project asset uploaded by the caller (project-creation cover flow).
  - DENY: asset belongs to a different project in the same workspace.
  - DENY (the regression this commit fixes): NULL-project asset created by a
    DIFFERENT user in the same workspace must not be claimable by a project
    member.
  - DENY: asset in an entirely different workspace.
  - Mixed batch: a legitimate NULL-project asset (created by caller) alongside
    a foreign NULL-project asset (created by someone else) in the same
    asset_ids batch. Because the PROJECT_COVER branch does
    ``assets.update(project_id=project_id)`` across the WHOLE queryset, the
    foreign asset must be excluded from the queryset itself, not filtered out
    downstream, or it gets swept into the project too.
"""

from uuid import uuid4

import pytest
from rest_framework import status

from plane.db.models import FileAsset, Project, ProjectMember, User, Workspace, WorkspaceMember


@pytest.fixture
def project(db, workspace, create_user):
    """Project P; create_user is an active member (the caller in these tests)."""
    project = Project.objects.create(
        name="Test Project P",
        identifier="TPP",
        workspace=workspace,
        created_by=create_user,
    )
    ProjectMember.objects.create(project=project, member=create_user, workspace=workspace, role=20)
    return project


@pytest.fixture
def other_project(db, workspace, create_user):
    """Project Q — same workspace as P, but create_user is NOT a member of it."""
    return Project.objects.create(
        name="Test Project Q",
        identifier="TPQ",
        workspace=workspace,
        created_by=create_user,
    )


@pytest.fixture
def other_user(db):
    """A different user in the same workspace who uploaded some NULL-project asset."""
    unique_id = uuid4().hex[:8]
    user = User.objects.create(
        email=f"other-{unique_id}@plane.so",
        username=f"other_{unique_id}",
        first_name="Other",
        last_name="User",
    )
    user.set_password("test-password")
    user.save()
    return user


@pytest.fixture
def other_workspace(db, other_user):
    """An entirely different workspace, owned by other_user."""
    ws = Workspace.objects.create(
        name="Other Workspace",
        owner=other_user,
        slug=f"other-ws-{uuid4().hex[:8]}",
    )
    WorkspaceMember.objects.create(workspace=ws, member=other_user, role=20)
    return ws


def bulk_url(slug, project_id, entity_id):
    return f"/api/assets/v2/workspaces/{slug}/projects/{project_id}/{entity_id}/bulk/"


def make_cover_asset(workspace, created_by, project=None):
    """Create a FileAsset with a specific created_by.

    NB: ``FileAsset`` (via ``BaseModel.save``) auto-overwrites ``created_by``
    from crum's thread-local current user unless ``disable_auto_set_user`` or
    ``created_by_id`` (as a save-time kwarg) is used. Outside of a request
    context (i.e. in a fixture) crum's current user is None, which would
    silently null out the field we just set via ``.create(created_by=...)``.
    Use ``.update()`` afterwards to set the real value without going through
    ``save()``'s override.
    """
    asset = FileAsset.objects.create(
        attributes={"name": "cover.png", "type": "image/png", "size": 256},
        asset=f"{workspace.id}/{uuid4().hex}-cover.png",
        size=256,
        workspace=workspace,
        project=project,
        entity_type=FileAsset.EntityTypeContext.PROJECT_COVER,
        is_uploaded=True,
        storage_metadata={"size": 256},
    )
    FileAsset.objects.filter(pk=asset.pk).update(created_by=created_by)
    asset.refresh_from_db()
    return asset


@pytest.mark.contract
class TestProjectBulkAssetClaim:
    @pytest.mark.django_db
    def test_allow_asset_already_in_project(self, session_client, workspace, project, create_user):
        """Case 1: asset already has project_id=P, caller is a member of P."""
        asset = make_cover_asset(workspace, create_user, project=project)

        response = session_client.post(
            bulk_url(workspace.slug, project.id, project.id),
            {"asset_ids": [str(asset.id)]},
            format="json",
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT, (
            f"Got {response.status_code}: {getattr(response, 'data', None)!r}"
        )
        asset.refresh_from_db()
        assert asset.project_id == project.id
        project.refresh_from_db()
        assert project.cover_image_asset_id == asset.id

    @pytest.mark.django_db
    def test_allow_null_project_asset_created_by_caller(self, session_client, workspace, project, create_user):
        """Case 2: project-creation cover flow — project_id NULL, created_by=caller."""
        asset = make_cover_asset(workspace, create_user, project=None)

        response = session_client.post(
            bulk_url(workspace.slug, project.id, project.id),
            {"asset_ids": [str(asset.id)]},
            format="json",
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT, (
            f"Got {response.status_code}: {getattr(response, 'data', None)!r}"
        )
        asset.refresh_from_db()
        assert asset.project_id == project.id
        project.refresh_from_db()
        assert project.cover_image_asset_id == asset.id

    @pytest.mark.django_db
    def test_deny_asset_belongs_to_different_project(
        self, session_client, workspace, project, other_project, create_user
    ):
        """Case 3: asset already belongs to project Q, caller is only a member of P."""
        asset = make_cover_asset(workspace, create_user, project=other_project)

        response = session_client.post(
            bulk_url(workspace.slug, project.id, project.id),
            {"asset_ids": [str(asset.id)]},
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND, (
            f"Got {response.status_code}: {getattr(response, 'data', None)!r}"
        )
        assert response.json() == {"error": "The requested asset could not be found."}
        asset.refresh_from_db()
        assert asset.project_id == other_project.id

    @pytest.mark.django_db
    def test_deny_null_project_asset_created_by_different_user(
        self, session_client, workspace, project, other_user
    ):
        """Case 4 (the regression this commit fixes): project_id NULL, created_by
        is a DIFFERENT user in the same workspace. A member of P must not be
        able to claim it."""
        asset = make_cover_asset(workspace, other_user, project=None)

        response = session_client.post(
            bulk_url(workspace.slug, project.id, project.id),
            {"asset_ids": [str(asset.id)]},
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND, (
            f"Got {response.status_code}: {getattr(response, 'data', None)!r}"
        )
        asset.refresh_from_db()
        assert asset.project_id is None

    @pytest.mark.django_db
    def test_deny_asset_in_different_workspace(
        self, session_client, workspace, project, other_workspace, other_user
    ):
        """Case 5: asset lives in an entirely different workspace."""
        asset = make_cover_asset(other_workspace, other_user, project=None)

        response = session_client.post(
            bulk_url(workspace.slug, project.id, project.id),
            {"asset_ids": [str(asset.id)]},
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND, (
            f"Got {response.status_code}: {getattr(response, 'data', None)!r}"
        )
        asset.refresh_from_db()
        assert asset.project_id is None
        assert asset.workspace_id == other_workspace.id

    @pytest.mark.django_db
    def test_mixed_batch_does_not_sweep_foreign_null_project_asset(
        self, session_client, workspace, project, create_user, other_user
    ):
        """Case 6 — the actual attack in the commit message: a legitimate
        NULL-project cover (created by caller) is batched together with a
        foreign NULL-project asset (created by someone else). The request must
        still succeed for the legitimate asset, but the foreign asset must be
        left completely untouched — not swept into the project by the
        whole-queryset ``assets.update(project_id=project_id)`` call."""
        legit = make_cover_asset(workspace, create_user, project=None)
        foreign = make_cover_asset(workspace, other_user, project=None)

        response = session_client.post(
            bulk_url(workspace.slug, project.id, project.id),
            {"asset_ids": [str(legit.id), str(foreign.id)]},
            format="json",
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT, (
            f"Got {response.status_code}: {getattr(response, 'data', None)!r}"
        )
        legit.refresh_from_db()
        foreign.refresh_from_db()
        assert legit.project_id == project.id
        assert foreign.project_id is None, (
            "Foreign NULL-project asset was swept into the project by the "
            "whole-queryset update — this is the IDOR the commit claims to fix."
        )
        project.refresh_from_db()
        assert project.cover_image_asset_id == legit.id
