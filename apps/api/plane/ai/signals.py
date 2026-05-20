"""
plane.ai signals — bot User + WorkspaceMember provisioning,
and LiteLLM virtual key lifecycle management.

On WorkspaceAgent creation:
  - Creates a bot User (email=bot_<slug>@eyriehq.com, is_bot=True)
  - Creates a WorkspaceMember linking that user to the agent's workspace
    with role=15 (Member)
  - Provisions a LiteLLM virtual key (if LiteLLM is configured)

On WorkspaceAgent deletion:
  - Deactivates the bot User
  - Deletes the associated WorkspaceMember
  - Revokes the LiteLLM virtual key (if one was provisioned)

On WorkspaceAISettings enable:
  - Provisions a workspace-level LiteLLM virtual key

On WorkspaceAISettings disable:
  - Revokes the workspace-level LiteLLM virtual key
"""

import logging
import uuid

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

logger = logging.getLogger("plane")


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


# ---------------------------------------------------------------------------
# LiteLLM virtual key lifecycle
# ---------------------------------------------------------------------------


@receiver(post_save, sender="db.WorkspaceAISettings")
def provision_workspace_virtual_key(sender, instance, created, **kwargs):
    """Provision or revoke a LiteLLM workspace-level virtual key on enable/disable."""
    from plane.ai.litellm_client import get_litellm_client

    client = get_litellm_client()
    if not client:
        return

    if instance.is_enabled and not instance.litellm_virtual_key:
        # Provision a new workspace-level key
        try:
            key = client.create_key(
                key_alias=f"workspace-{instance.workspace.slug}",
                budget_usd=float(instance.monthly_budget),
                metadata={
                    "workspace_slug": instance.workspace.slug,
                    "type": "workspace",
                },
            )
            # Use queryset update to avoid re-triggering this signal
            sender.objects.filter(pk=instance.pk).update(litellm_virtual_key=key)
        except Exception as exc:
            logger.warning(
                "Failed to provision workspace virtual key for %s: %s",
                instance.workspace.slug,
                exc,
            )

    elif not instance.is_enabled and instance.litellm_virtual_key:
        # Revoke the key when AI is disabled
        try:
            client.delete_key(instance.litellm_virtual_key)
            sender.objects.filter(pk=instance.pk).update(litellm_virtual_key="")
        except Exception as exc:
            logger.warning(
                "Failed to revoke workspace virtual key for %s: %s",
                instance.workspace.slug,
                exc,
            )


@receiver(post_save, sender="db.WorkspaceAgent")
def provision_agent_virtual_key(sender, instance, created, **kwargs):
    """Provision a LiteLLM virtual key for a newly created workspace agent."""
    if not created:
        return  # Budget updates are handled at the view layer (PATCH endpoint)

    from plane.ai.litellm_client import get_litellm_client

    client = get_litellm_client()
    if not client:
        return

    try:
        key = client.create_key(
            key_alias=f"agent-{instance.workspace.slug}-{instance.slug}",
            budget_usd=float(instance.monthly_budget),
            metadata={
                "workspace_slug": instance.workspace.slug,
                "agent_slug": instance.slug,
                "type": "agent",
            },
        )
        # Use queryset update to avoid re-triggering this signal
        sender.objects.filter(pk=instance.pk).update(litellm_virtual_key=key)
    except Exception as exc:
        logger.warning(
            "Failed to provision agent virtual key for %s/%s: %s",
            instance.workspace.slug,
            instance.slug,
            exc,
        )


@receiver(post_delete, sender="db.WorkspaceAgent")
def revoke_agent_virtual_key(sender, instance, **kwargs):
    """Revoke the LiteLLM virtual key when an agent is deleted."""
    if not instance.litellm_virtual_key:
        return

    from plane.ai.litellm_client import get_litellm_client

    client = get_litellm_client()
    if not client:
        return

    try:
        client.delete_key(instance.litellm_virtual_key)
    except Exception as exc:
        logger.warning(
            "Failed to revoke agent virtual key for %s/%s: %s",
            instance.workspace.slug,
            instance.slug,
            exc,
        )
