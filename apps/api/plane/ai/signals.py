"""
plane.ai signals — bot User + WorkspaceMember provisioning.

On WorkspaceAgent creation:
  - Creates a bot User (email=bot_<slug>@eyriehq.com, is_bot=True)
  - Creates a WorkspaceMember linking that user to the agent's workspace
    with role=15 (Member)

On WorkspaceAgent deletion:
  - Deactivates the bot User
  - Deletes the associated WorkspaceMember
"""

import uuid

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver


@receiver(post_save, sender="db.WorkspaceAgent")
def provision_bot_user(sender, instance, created, **kwargs):
    """Provision a bot User and WorkspaceMember when a WorkspaceAgent is created."""
    if not created:
        return

    # Import here to avoid circular imports at module load time
    from django.contrib.auth import get_user_model
    from plane.db.models import WorkspaceMember

    User = get_user_model()

    bot_email = f"bot_{instance.slug}@eyriehq.com"

    # Create or resurrect the bot user for this agent slug
    bot_user, _ = User.objects.get_or_create(
        email=bot_email,
        defaults={
            "username": f"bot_{instance.slug}_{uuid.uuid4().hex[:8]}",
            "display_name": instance.name,
            "is_bot": True,
            "is_active": True,
            "is_email_verified": True,
            "is_email_valid": True,
        },
    )

    # Re-activate in case a prior deletion deactivated it
    if not bot_user.is_active:
        User.objects.filter(pk=bot_user.pk).update(
            is_active=True, display_name=instance.name
        )

    # Link agent → bot user
    # Use queryset update to avoid triggering WorkspaceAgent's own post_save again
    sender.objects.filter(pk=instance.pk).update(bot_user=bot_user)
    instance.bot_user = bot_user

    # Create workspace membership if not already present
    WorkspaceMember.objects.get_or_create(
        workspace=instance.workspace,
        member=bot_user,
        defaults={
            "role": 15,  # Member
            "is_active": True,
        },
    )


@receiver(post_delete, sender="db.WorkspaceAgent")
def deprovision_bot_user(sender, instance, **kwargs):
    """Deactivate bot User and remove WorkspaceMember when a WorkspaceAgent is deleted."""
    if not instance.bot_user_id:
        return

    from django.contrib.auth import get_user_model
    from plane.db.models import WorkspaceMember

    User = get_user_model()

    # Deactivate bot user rather than hard-deleting (preserves audit trail)
    User.objects.filter(pk=instance.bot_user_id).update(is_active=False)

    # Remove workspace membership
    WorkspaceMember.objects.filter(
        workspace=instance.workspace,
        member_id=instance.bot_user_id,
    ).delete()
