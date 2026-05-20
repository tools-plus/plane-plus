from django.db import models

from plane.db.models.base import BaseModel


class LiteLLMConfig(BaseModel):
    """
    Singleton-per-instance configuration for the LiteLLM gateway.
    Controls routing, budget caps, and the master key used to provision
    virtual keys for workspace and agent accounts.
    """

    endpoint = models.URLField(default="http://plane-litellm:4000")
    master_key = models.TextField()  # encrypted at rest
    provider = models.CharField(max_length=50, default="anthropic")
    model_routing = models.JSONField(default=dict)
    default_workspace_budget = models.DecimalField(
        max_digits=8, decimal_places=2, default=20.00
    )
    max_workspace_budget = models.DecimalField(
        max_digits=8, decimal_places=2, default=100.00
    )
    default_agent_budget = models.DecimalField(
        max_digits=8, decimal_places=2, default=5.00
    )
    max_agent_budget = models.DecimalField(
        max_digits=8, decimal_places=2, default=20.00
    )
    is_active = models.BooleanField(default=False)

    class Meta:
        app_label = "db"
        db_table = "ai_litellm_config"
        verbose_name = "LiteLLM Config"
        verbose_name_plural = "LiteLLM Configs"

    def __str__(self):
        return f"LiteLLMConfig(provider={self.provider}, active={self.is_active})"
