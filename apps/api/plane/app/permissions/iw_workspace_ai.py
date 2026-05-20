# InfraWatch — AI module workspace permissions
# SPDX-License-Identifier: AGPL-3.0-only

from rest_framework.permissions import BasePermission, SAFE_METHODS

from plane.db.models import WorkspaceMember
from plane.app.permissions import ROLE

ADMIN = ROLE.ADMIN.value
MEMBER = ROLE.MEMBER.value


class WorkspaceAISettingsPermission(BasePermission):
    """Settings (enable/disable, budget): admins only for writes, members for reads."""

    def has_permission(self, request, view):
        if request.user.is_anonymous:
            return False

        slug = view.kwargs.get("slug")
        membership = (
            WorkspaceMember.objects.filter(
                member=request.user,
                workspace__slug=slug,
                is_active=True,
            )
            .values_list("role", flat=True)
            .first()
        )

        if membership is None:
            return False

        if request.method in SAFE_METHODS:
            return True

        return membership == ADMIN


class WorkspaceAIPermission(BasePermission):
    """Agent/Skill/Tool/MCP CRUD: any workspace member."""

    def has_permission(self, request, view):
        if request.user.is_anonymous:
            return False

        slug = view.kwargs.get("slug")
        return WorkspaceMember.objects.filter(
            member=request.user,
            workspace__slug=slug,
            is_active=True,
        ).exists()
