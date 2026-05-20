# InfraWatch-specific permissions — isolated to avoid upstream merge conflicts.

from rest_framework.permissions import BasePermission, SAFE_METHODS

from plane.db.models import WorkspaceMember
from plane.app.permissions import ROLE

ADMIN = ROLE.ADMIN.value
MEMBER = ROLE.MEMBER.value


class WorkspaceAISettingsPermission(BasePermission):
    """
    Permission for workspace AI settings (singleton).
    - GET: any workspace member.
    - PATCH: workspace admin only.
    """

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

        # PATCH — admin only
        return membership == ADMIN


class WorkspaceAIPermission(BasePermission):
    """
    Permission for workspace AI entities (agents, skills, tools, MCP connections).
    - Safe methods (GET, HEAD, OPTIONS): any active workspace member.
    - Write methods (POST, PATCH, DELETE): member or admin (role >= MEMBER).
    """

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

        return membership >= MEMBER
