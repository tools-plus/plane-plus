from django.db import models

from plane.db.models.base import BaseModel


AUTH_TYPE_CHOICES = [
    ("none", "None"),
    ("api_key", "API Key"),
    ("oauth", "OAuth"),
]


class GlobalMCPConnection(BaseModel):
    """
    Platform-level MCP server connection. Credentials are stored
    encrypted; the tool_manifest is a cached copy of the server's
    available tools, refreshed on registration or on demand.
    """

    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    server_url = models.URLField()
    auth_type = models.CharField(
        max_length=20,
        choices=AUTH_TYPE_CHOICES,
        default="none",
    )
    auth_config = models.JSONField(default=dict)  # encrypted
    env_vars = models.JSONField(default=dict)  # encrypted, injected at runtime
    tool_manifest = models.JSONField(default=list)  # cached from MCP server
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "db"
        db_table = "ai_global_mcp_connection"
        verbose_name = "Global MCP Connection"
        verbose_name_plural = "Global MCP Connections"

    def __str__(self):
        return self.name


class WorkspaceMCPConnection(BaseModel):
    """
    Workspace-scoped MCP connection. May mirror a GlobalMCPConnection
    (source='global') or be workspace-defined (source='workspace').
    """

    workspace = models.ForeignKey(
        "db.Workspace",
        on_delete=models.CASCADE,
        related_name="ai_mcp_connections",
    )
    source = models.CharField(
        max_length=20,
        choices=[("global", "Global"), ("workspace", "Workspace")],
    )
    global_mcp = models.ForeignKey(
        GlobalMCPConnection,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="workspace_mcp_connections",
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField()
    server_url = models.URLField()
    auth_type = models.CharField(
        max_length=20,
        choices=AUTH_TYPE_CHOICES,
        default="none",
    )
    auth_config = models.JSONField(default=dict)
    env_vars = models.JSONField(default=dict)
    tool_manifest = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "db"
        db_table = "ai_workspace_mcp_connection"
        unique_together = [("workspace", "slug")]
        verbose_name = "Workspace MCP Connection"
        verbose_name_plural = "Workspace MCP Connections"

    def __str__(self):
        return f"{self.workspace_id} / {self.name}"
