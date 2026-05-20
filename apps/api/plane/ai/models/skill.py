from django.db import models

from plane.db.models.base import BaseModel


class GlobalSkill(BaseModel):
    """
    Platform-defined skill that can be attached to any agent.
    Skills inject structured knowledge (markdown) into the agent's context window.
    """

    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    knowledge = models.TextField()  # markdown injected into agent context
    category = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "db"
        db_table = "ai_global_skill"
        verbose_name = "Global Skill"
        verbose_name_plural = "Global Skills"

    def __str__(self):
        return self.name


class WorkspaceSkill(BaseModel):
    """
    Workspace-scoped skill. May mirror a GlobalSkill (source='global')
    or be defined entirely within a workspace (source='workspace').
    """

    workspace = models.ForeignKey(
        "db.Workspace",
        on_delete=models.CASCADE,
        related_name="ai_skills",
    )
    source = models.CharField(
        max_length=20,
        choices=[("global", "Global"), ("workspace", "Workspace")],
    )
    global_skill = models.ForeignKey(
        GlobalSkill,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="workspace_skills",
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField()
    description = models.TextField(blank=True)
    knowledge = models.TextField()
    category = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "db"
        db_table = "ai_workspace_skill"
        unique_together = [("workspace", "slug")]
        verbose_name = "Workspace Skill"
        verbose_name_plural = "Workspace Skills"

    def __str__(self):
        return f"{self.workspace_id} / {self.name}"
