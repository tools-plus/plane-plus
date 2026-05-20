from django.db import models

from plane.db.models.base import BaseModel

from .skill import GlobalSkill, WorkspaceSkill
from .tool import GlobalTool, WorkspaceTool
from .mcp import GlobalMCPConnection, WorkspaceMCPConnection


class GlobalAgent(BaseModel):
    """
    Platform-defined AI agent template. Workspace admins instantiate
    these as WorkspaceAgents; the platform owner defines the base set.
    """

    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    instructions = models.TextField()  # system prompt
    model_pref = models.CharField(max_length=100, default="claude-sonnet-4-5")
    avatar_url = models.URLField(blank=True)
    default_monthly_budget = models.DecimalField(
        max_digits=8, decimal_places=2, default=5.00
    )
    is_active = models.BooleanField(default=True)
    skills = models.ManyToManyField(
        GlobalSkill,
        blank=True,
        related_name="agents",
    )
    tools = models.ManyToManyField(
        GlobalTool,
        blank=True,
        related_name="agents",
    )
    mcp_connections = models.ManyToManyField(
        GlobalMCPConnection,
        blank=True,
        related_name="agents",
    )

    class Meta:
        app_label = "db"
        db_table = "ai_global_agent"
        verbose_name = "Global Agent"
        verbose_name_plural = "Global Agents"

    def __str__(self):
        return self.name


class WorkspaceAgent(BaseModel):
    """
    Workspace-scoped AI agent. May be instantiated from a GlobalAgent
    (source='global') or created entirely within a workspace
    (source='workspace').

    On creation, a signal provisions:
      - a bot User (email=bot_<slug>@eyriehq.com, is_bot=True)
      - a WorkspaceMember linking that user to this workspace
    """

    workspace = models.ForeignKey(
        "db.Workspace",
        on_delete=models.CASCADE,
        related_name="ai_agents",
    )
    source = models.CharField(
        max_length=20,
        choices=[("global", "Global"), ("workspace", "Workspace")],
    )
    global_agent = models.ForeignKey(
        GlobalAgent,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="workspace_agents",
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField()
    description = models.TextField(blank=True)
    instructions = models.TextField()
    model_pref = models.CharField(max_length=100, default="claude-sonnet-4-5")
    avatar_url = models.URLField(blank=True)
    monthly_budget = models.DecimalField(
        max_digits=8, decimal_places=2, default=5.00
    )
    litellm_virtual_key = models.TextField(blank=True)  # provisioned by signal
    is_active = models.BooleanField(default=True)
    bot_user = models.OneToOneField(
        "db.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="workspace_agent",
    )
    skills = models.ManyToManyField(WorkspaceSkill, blank=True)
    tools = models.ManyToManyField(WorkspaceTool, blank=True)
    mcp_connections = models.ManyToManyField(WorkspaceMCPConnection, blank=True)

    class Meta:
        app_label = "db"
        db_table = "ai_workspace_agent"
        unique_together = [("workspace", "slug")]
        verbose_name = "Workspace Agent"
        verbose_name_plural = "Workspace Agents"

    def __str__(self):
        return f"{self.workspace_id} / {self.name}"
