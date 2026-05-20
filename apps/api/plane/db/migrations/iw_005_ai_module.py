# InfraWatch — Create plane.ai tables for the AI Module (PP-80).
#
# Forwards-only. Creates all tables for:
#   - LiteLLMConfig            (instance-level gateway config)
#   - GlobalAgent / WorkspaceAgent
#   - GlobalSkill  / WorkspaceSkill
#   - GlobalTool   / WorkspaceTool   + seeds 7 built-in tools
#   - GlobalMCPConnection / WorkspaceMCPConnection
#   - WorkspaceAISettings
#
# Models live in plane.ai.models but carry app_label="db" so this
# migration (in the db app) owns their schema.

import uuid
import decimal

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

BUILTIN_TOOLS = [
    {
        "slug": "plane.get_work_item",
        "name": "Get Work Item",
        "description": "Retrieve a work item's full context",
        "builtin_ref": "plane.get_work_item",
    },
    {
        "slug": "plane.update_work_item",
        "name": "Update Work Item",
        "description": "Update title, description, or state of a work item",
        "builtin_ref": "plane.update_work_item",
        "is_destructive": True,
    },
    {
        "slug": "plane.create_comment",
        "name": "Create Comment",
        "description": "Post a comment on a work item",
        "builtin_ref": "plane.create_comment",
    },
    {
        "slug": "plane.create_work_item",
        "name": "Create Work Item",
        "description": "Create a new work item",
        "builtin_ref": "plane.create_work_item",
    },
    {
        "slug": "plane.search_work_items",
        "name": "Search Work Items",
        "description": "Search work items by keyword or filter",
        "builtin_ref": "plane.search_work_items",
    },
    {
        "slug": "plane.get_page",
        "name": "Get Page",
        "description": "Read a wiki or project page",
        "builtin_ref": "plane.get_page",
    },
    {
        "slug": "plane.update_page",
        "name": "Update Page",
        "description": "Write content to a wiki or project page",
        "builtin_ref": "plane.update_page",
        "is_destructive": True,
    },
]


def seed_builtin_tools(apps, schema_editor):
    GlobalTool = apps.get_model("db", "GlobalTool")
    for tool_data in BUILTIN_TOOLS:
        GlobalTool.objects.get_or_create(
            slug=tool_data["slug"],
            defaults={
                "name": tool_data["name"],
                "description": tool_data["description"],
                "implementation_type": "builtin",
                "builtin_ref": tool_data["builtin_ref"],
                "input_schema": {},
                "is_destructive": tool_data.get("is_destructive", False),
                "is_active": True,
            },
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("db", "iw_004_agent_doc"),
    ]

    operations = [
        # ------------------------------------------------------------------ #
        # LiteLLMConfig                                                        #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name="LiteLLMConfig",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Last Modified At"),
                ),
                (
                    "deleted_at",
                    models.DateTimeField(blank=True, null=True, verbose_name="Deleted At"),
                ),
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                ("endpoint", models.URLField(default="http://plane-litellm:4000")),
                ("master_key", models.TextField()),
                ("provider", models.CharField(default="anthropic", max_length=50)),
                ("model_routing", models.JSONField(default=dict)),
                (
                    "default_workspace_budget",
                    models.DecimalField(decimal_places=2, default=decimal.Decimal("20.00"), max_digits=8),
                ),
                (
                    "max_workspace_budget",
                    models.DecimalField(decimal_places=2, default=decimal.Decimal("100.00"), max_digits=8),
                ),
                (
                    "default_agent_budget",
                    models.DecimalField(decimal_places=2, default=decimal.Decimal("5.00"), max_digits=8),
                ),
                (
                    "max_agent_budget",
                    models.DecimalField(decimal_places=2, default=decimal.Decimal("20.00"), max_digits=8),
                ),
                ("is_active", models.BooleanField(default=False)),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created By",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Last Modified By",
                    ),
                ),
            ],
            options={
                "db_table": "ai_litellm_config",
                "verbose_name": "LiteLLM Config",
            },
        ),
        # ------------------------------------------------------------------ #
        # GlobalSkill                                                          #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name="GlobalSkill",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Last Modified At"),
                ),
                (
                    "deleted_at",
                    models.DateTimeField(blank=True, null=True, verbose_name="Deleted At"),
                ),
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("slug", models.SlugField(unique=True)),
                ("description", models.TextField(blank=True)),
                ("knowledge", models.TextField()),
                ("category", models.CharField(blank=True, max_length=100)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created By",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Last Modified By",
                    ),
                ),
            ],
            options={
                "db_table": "ai_global_skill",
                "verbose_name": "Global Skill",
            },
        ),
        # ------------------------------------------------------------------ #
        # GlobalTool                                                           #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name="GlobalTool",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Last Modified At"),
                ),
                (
                    "deleted_at",
                    models.DateTimeField(blank=True, null=True, verbose_name="Deleted At"),
                ),
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("slug", models.SlugField(unique=True)),
                ("description", models.TextField()),
                (
                    "implementation_type",
                    models.CharField(
                        choices=[("builtin", "Built-in"), ("custom", "Custom")],
                        default="builtin",
                        max_length=20,
                    ),
                ),
                ("builtin_ref", models.CharField(blank=True, max_length=255)),
                ("input_schema", models.JSONField(default=dict)),
                ("is_destructive", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created By",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Last Modified By",
                    ),
                ),
            ],
            options={
                "db_table": "ai_global_tool",
                "verbose_name": "Global Tool",
            },
        ),
        # ------------------------------------------------------------------ #
        # GlobalMCPConnection                                                  #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name="GlobalMCPConnection",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Last Modified At"),
                ),
                (
                    "deleted_at",
                    models.DateTimeField(blank=True, null=True, verbose_name="Deleted At"),
                ),
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("slug", models.SlugField(unique=True)),
                ("server_url", models.URLField()),
                (
                    "auth_type",
                    models.CharField(
                        choices=[("none", "None"), ("api_key", "API Key"), ("oauth", "OAuth")],
                        default="none",
                        max_length=20,
                    ),
                ),
                ("auth_config", models.JSONField(default=dict)),
                ("env_vars", models.JSONField(default=dict)),
                ("tool_manifest", models.JSONField(default=list)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created By",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Last Modified By",
                    ),
                ),
            ],
            options={
                "db_table": "ai_global_mcp_connection",
                "verbose_name": "Global MCP Connection",
            },
        ),
        # ------------------------------------------------------------------ #
        # GlobalAgent  (depends on GlobalSkill, GlobalTool, GlobalMCPConnection)
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name="GlobalAgent",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Last Modified At"),
                ),
                (
                    "deleted_at",
                    models.DateTimeField(blank=True, null=True, verbose_name="Deleted At"),
                ),
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("slug", models.SlugField(unique=True)),
                ("description", models.TextField(blank=True)),
                ("instructions", models.TextField()),
                ("model_pref", models.CharField(default="claude-sonnet-4-5", max_length=100)),
                ("avatar_url", models.URLField(blank=True)),
                (
                    "default_monthly_budget",
                    models.DecimalField(decimal_places=2, default=decimal.Decimal("5.00"), max_digits=8),
                ),
                ("is_active", models.BooleanField(default=True)),
                (
                    "skills",
                    models.ManyToManyField(
                        blank=True,
                        related_name="agents",
                        to="db.GlobalSkill",
                    ),
                ),
                (
                    "tools",
                    models.ManyToManyField(
                        blank=True,
                        related_name="agents",
                        to="db.GlobalTool",
                    ),
                ),
                (
                    "mcp_connections",
                    models.ManyToManyField(
                        blank=True,
                        related_name="agents",
                        to="db.GlobalMCPConnection",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created By",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Last Modified By",
                    ),
                ),
            ],
            options={
                "db_table": "ai_global_agent",
                "verbose_name": "Global Agent",
            },
        ),
        # ------------------------------------------------------------------ #
        # WorkspaceSkill                                                       #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name="WorkspaceSkill",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Last Modified At"),
                ),
                (
                    "deleted_at",
                    models.DateTimeField(blank=True, null=True, verbose_name="Deleted At"),
                ),
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                (
                    "workspace",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ai_skills",
                        to="db.workspace",
                    ),
                ),
                (
                    "source",
                    models.CharField(
                        choices=[("global", "Global"), ("workspace", "Workspace")],
                        max_length=20,
                    ),
                ),
                (
                    "global_skill",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="workspace_skills",
                        to="db.GlobalSkill",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("slug", models.SlugField()),
                ("description", models.TextField(blank=True)),
                ("knowledge", models.TextField()),
                ("category", models.CharField(blank=True, max_length=100)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created By",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Last Modified By",
                    ),
                ),
            ],
            options={
                "db_table": "ai_workspace_skill",
                "verbose_name": "Workspace Skill",
            },
        ),
        migrations.AlterUniqueTogether(
            name="workspaceskill",
            unique_together={("workspace", "slug")},
        ),
        # ------------------------------------------------------------------ #
        # WorkspaceTool                                                        #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name="WorkspaceTool",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Last Modified At"),
                ),
                (
                    "deleted_at",
                    models.DateTimeField(blank=True, null=True, verbose_name="Deleted At"),
                ),
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                (
                    "workspace",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ai_tools",
                        to="db.workspace",
                    ),
                ),
                (
                    "source",
                    models.CharField(
                        choices=[("global", "Global"), ("workspace", "Workspace")],
                        max_length=20,
                    ),
                ),
                (
                    "global_tool",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="workspace_tools",
                        to="db.GlobalTool",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("slug", models.SlugField()),
                ("description", models.TextField()),
                (
                    "implementation_type",
                    models.CharField(
                        choices=[("builtin", "Built-in"), ("custom", "Custom")],
                        default="builtin",
                        max_length=20,
                    ),
                ),
                ("builtin_ref", models.CharField(blank=True, max_length=255)),
                ("input_schema", models.JSONField(default=dict)),
                ("is_destructive", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created By",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Last Modified By",
                    ),
                ),
            ],
            options={
                "db_table": "ai_workspace_tool",
                "verbose_name": "Workspace Tool",
            },
        ),
        migrations.AlterUniqueTogether(
            name="workspacetool",
            unique_together={("workspace", "slug")},
        ),
        # ------------------------------------------------------------------ #
        # WorkspaceMCPConnection                                               #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name="WorkspaceMCPConnection",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Last Modified At"),
                ),
                (
                    "deleted_at",
                    models.DateTimeField(blank=True, null=True, verbose_name="Deleted At"),
                ),
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                (
                    "workspace",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ai_mcp_connections",
                        to="db.workspace",
                    ),
                ),
                (
                    "source",
                    models.CharField(
                        choices=[("global", "Global"), ("workspace", "Workspace")],
                        max_length=20,
                    ),
                ),
                (
                    "global_mcp",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="workspace_mcp_connections",
                        to="db.GlobalMCPConnection",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("slug", models.SlugField()),
                ("server_url", models.URLField()),
                (
                    "auth_type",
                    models.CharField(
                        choices=[("none", "None"), ("api_key", "API Key"), ("oauth", "OAuth")],
                        default="none",
                        max_length=20,
                    ),
                ),
                ("auth_config", models.JSONField(default=dict)),
                ("env_vars", models.JSONField(default=dict)),
                ("tool_manifest", models.JSONField(default=list)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created By",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Last Modified By",
                    ),
                ),
            ],
            options={
                "db_table": "ai_workspace_mcp_connection",
                "verbose_name": "Workspace MCP Connection",
            },
        ),
        migrations.AlterUniqueTogether(
            name="workspacemcpconnection",
            unique_together={("workspace", "slug")},
        ),
        # ------------------------------------------------------------------ #
        # WorkspaceAgent  (depends on Workspace*, GlobalAgent, User)          #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name="WorkspaceAgent",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Last Modified At"),
                ),
                (
                    "deleted_at",
                    models.DateTimeField(blank=True, null=True, verbose_name="Deleted At"),
                ),
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                (
                    "workspace",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ai_agents",
                        to="db.workspace",
                    ),
                ),
                (
                    "source",
                    models.CharField(
                        choices=[("global", "Global"), ("workspace", "Workspace")],
                        max_length=20,
                    ),
                ),
                (
                    "global_agent",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="workspace_agents",
                        to="db.GlobalAgent",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("slug", models.SlugField()),
                ("description", models.TextField(blank=True)),
                ("instructions", models.TextField()),
                ("model_pref", models.CharField(default="claude-sonnet-4-5", max_length=100)),
                ("avatar_url", models.URLField(blank=True)),
                (
                    "monthly_budget",
                    models.DecimalField(decimal_places=2, default=decimal.Decimal("5.00"), max_digits=8),
                ),
                ("litellm_virtual_key", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "bot_user",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="workspace_agent",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "skills",
                    models.ManyToManyField(
                        blank=True,
                        to="db.WorkspaceSkill",
                    ),
                ),
                (
                    "tools",
                    models.ManyToManyField(
                        blank=True,
                        to="db.WorkspaceTool",
                    ),
                ),
                (
                    "mcp_connections",
                    models.ManyToManyField(
                        blank=True,
                        to="db.WorkspaceMCPConnection",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created By",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Last Modified By",
                    ),
                ),
            ],
            options={
                "db_table": "ai_workspace_agent",
                "verbose_name": "Workspace Agent",
            },
        ),
        migrations.AlterUniqueTogether(
            name="workspaceagent",
            unique_together={("workspace", "slug")},
        ),
        # ------------------------------------------------------------------ #
        # WorkspaceAISettings                                                  #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name="WorkspaceAISettings",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Last Modified At"),
                ),
                (
                    "deleted_at",
                    models.DateTimeField(blank=True, null=True, verbose_name="Deleted At"),
                ),
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                (
                    "workspace",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ai_settings",
                        to="db.workspace",
                    ),
                ),
                ("is_enabled", models.BooleanField(default=False)),
                (
                    "monthly_budget",
                    models.DecimalField(decimal_places=2, default=decimal.Decimal("20.00"), max_digits=8),
                ),
                ("litellm_virtual_key", models.TextField(blank=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created By",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Last Modified By",
                    ),
                ),
            ],
            options={
                "db_table": "ai_workspace_settings",
                "verbose_name": "Workspace AI Settings",
            },
        ),
        # ------------------------------------------------------------------ #
        # Seed built-in GlobalTool records                                    #
        # ------------------------------------------------------------------ #
        migrations.RunPython(seed_builtin_tools, reverse_code=noop),
    ]
