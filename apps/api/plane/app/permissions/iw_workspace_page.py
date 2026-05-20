# InfraWatch-specific permissions — isolated to avoid upstream merge conflicts.

from plane.db.models import WorkspaceMember, Page
from plane.app.permissions import ROLE

from rest_framework.permissions import BasePermission, SAFE_METHODS

# Permission Mappings for workspace members
ADMIN = ROLE.ADMIN.value
MEMBER = ROLE.MEMBER.value
GUEST = ROLE.GUEST.value


class WorkspacePagePermission(BasePermission):
    """
    Permission class for workspace-level pages (is_global=True).
    - All workspace members can list, retrieve, create, and edit.
    - Only page owner or workspace admin can delete.
    """

    def has_permission(self, request, view):
        if request.user.is_anonymous:
            return False

        slug = view.kwargs.get("slug")
        page_id = view.kwargs.get("page_id")

        # Check workspace membership
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

        # Safe methods — all workspace members can view
        if request.method in SAFE_METHODS:
            return True

        # POST (create), PUT/PATCH (update) — all workspace members allowed
        if request.method in ["POST", "PUT", "PATCH"]:
            return True

        if request.method == "DELETE":
            # Page delete — only the owner or a workspace admin
            if page_id:
                page = Page.objects.filter(
                    pk=page_id, workspace__slug=slug, is_global=True
                ).first()
                if page is None:
                    return False
                if page.owned_by_id == request.user.id:
                    return True
                return membership == ADMIN

            # Folder delete — folders have no ownership; any member or admin can delete
            return membership in [MEMBER, ADMIN]

        return False
