from django.db import models

from plane.db.models.base import BaseModel


IMPLEMENTATION_TYPES = [("builtin", "Built-in"), ("custom", "Custom")]


class GlobalTool(BaseModel):
    """
    Platform-defined tool available to all agents.
    Built-in tools map to first-class Plane SDK calls; custom tools
    use an arbitrary function reference or HTTP endpoint.
    """

    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    implementation_type = models.CharField(
        max_length=20,
        choices=IMPLEMENTATION_TYPES,
        default="builtin",
    )
    builtin_ref = models.CharField(
        max_length=255,
        blank=True,
    )  # e.g. "plane.get_work_item"
    input_schema = models.JSONField(default=dict)
    is_destructive = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "db"
        db_table = "ai_global_tool"
        verbose_name = "Global Tool"
        verbose_name_plural = "Global Tools"

    def __str__(self):
        return self.name


class WorkspaceTool(BaseModel):
    """
    Workspace-scoped tool. May mirror a GlobalTool (source='global')
    or be workspace-custom (source='workspace').
    """

    workspace = models.ForeignKey(
        "db.Workspace",
        on_delete=models.CASCADE,
        related_name="ai_tools",
    )
    source = models.CharField(
        max_length=20,
        choices=[("global", "Global"), ("workspace", "Workspace")],
    )
    global_tool = models.ForeignKey(
        GlobalTool,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="workspace_tools",
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField()
    description = models.TextField()
    implementation_type = models.CharField(
        max_length=20,
        choices=IMPLEMENTATION_TYPES,
        default="builtin",
    )
    builtin_ref = models.CharField(max_length=255, blank=True)
    input_schema = models.JSONField(default=dict)
    is_destructive = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "db"
        db_table = "ai_workspace_tool"
        unique_together = [("workspace", "slug")]
        verbose_name = "Workspace Tool"
        verbose_name_plural = "Workspace Tools"

    def __str__(self):
        return f"{self.workspace_id} / {self.name}"
