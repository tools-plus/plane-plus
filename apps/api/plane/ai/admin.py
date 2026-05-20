from django.contrib import admin

from .models import (
    LiteLLMConfig,
    GlobalAgent,
    WorkspaceAgent,
    GlobalSkill,
    WorkspaceSkill,
    GlobalTool,
    WorkspaceTool,
    GlobalMCPConnection,
    WorkspaceMCPConnection,
    WorkspaceAISettings,
)


@admin.register(LiteLLMConfig)
class LiteLLMConfigAdmin(admin.ModelAdmin):
    list_display = ("provider", "endpoint", "is_active", "created_at")
    list_filter = ("is_active", "provider")


@admin.register(GlobalAgent)
class GlobalAgentAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "model_pref", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")


@admin.register(WorkspaceAgent)
class WorkspaceAgentAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "workspace", "source", "is_active")
    list_filter = ("is_active", "source")
    search_fields = ("name", "slug")
    raw_id_fields = ("workspace", "global_agent", "bot_user")


@admin.register(GlobalSkill)
class GlobalSkillAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "category", "is_active")
    list_filter = ("is_active", "category")
    search_fields = ("name", "slug")


@admin.register(WorkspaceSkill)
class WorkspaceSkillAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "workspace", "source", "is_active")
    list_filter = ("is_active", "source")
    search_fields = ("name", "slug")
    raw_id_fields = ("workspace", "global_skill")


@admin.register(GlobalTool)
class GlobalToolAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "implementation_type", "is_destructive", "is_active")
    list_filter = ("is_active", "implementation_type", "is_destructive")
    search_fields = ("name", "slug", "builtin_ref")


@admin.register(WorkspaceTool)
class WorkspaceToolAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "workspace", "source", "is_destructive", "is_active")
    list_filter = ("is_active", "source", "is_destructive")
    search_fields = ("name", "slug")
    raw_id_fields = ("workspace", "global_tool")


@admin.register(GlobalMCPConnection)
class GlobalMCPConnectionAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "server_url", "auth_type", "is_active")
    list_filter = ("is_active", "auth_type")
    search_fields = ("name", "slug")


@admin.register(WorkspaceMCPConnection)
class WorkspaceMCPConnectionAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "workspace", "source", "auth_type", "is_active")
    list_filter = ("is_active", "source", "auth_type")
    search_fields = ("name", "slug")
    raw_id_fields = ("workspace", "global_mcp")


@admin.register(WorkspaceAISettings)
class WorkspaceAISettingsAdmin(admin.ModelAdmin):
    list_display = ("workspace", "is_enabled", "monthly_budget", "created_at")
    list_filter = ("is_enabled",)
    raw_id_fields = ("workspace",)
