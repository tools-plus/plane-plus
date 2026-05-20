from django.db import models

from plane.db.models.base import BaseModel


class WorkspaceAISettings(BaseModel):
    """
    Per-workspace AI feature toggle and budget configuration.
    Created on demand when a workspace admin enables the AI module.
    """

    workspace = models.OneToOneField(
        "db.Workspace",
        on_delete=models.CASCADE,
        related_name="ai_settings",
    )
    is_enabled = models.BooleanField(default=False)
    monthly_budget = models.DecimalField(
        max_digits=8, decimal_places=2, default=20.00
    )
    litellm_virtual_key = models.TextField(blank=True)  # workspace-level virtual key

    class Meta:
        app_label = "db"
        db_table = "ai_workspace_settings"
        verbose_name = "Workspace AI Settings"
        verbose_name_plural = "Workspace AI Settings"

    def __str__(self):
        return f"AISettings(workspace={self.workspace_id}, enabled={self.is_enabled})"
