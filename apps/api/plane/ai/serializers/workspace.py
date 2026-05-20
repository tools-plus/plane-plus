# InfraWatch — serializers for workspace-scoped AI entities
# SPDX-License-Identifier: AGPL-3.0-only

from rest_framework import serializers

from plane.ai.models import (
    WorkspaceAISettings,
    WorkspaceAgent,
    WorkspaceSkill,
    WorkspaceTool,
    WorkspaceMCPConnection,
)


class WorkspaceAISettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkspaceAISettings
        fields = ["id", "is_enabled", "monthly_budget"]


class WorkspaceAgentSerializer(serializers.ModelSerializer):
    litellm_virtual_key = serializers.CharField(read_only=True)
    bot_user_email = serializers.SerializerMethodField()

    def get_bot_user_email(self, obj):
        return obj.bot_user.email if obj.bot_user else None

    class Meta:
        model = WorkspaceAgent
        fields = [
            "id",
            "source",
            "global_agent",
            "name",
            "slug",
            "description",
            "instructions",
            "model_pref",
            "avatar_url",
            "monthly_budget",
            "is_active",
            "litellm_virtual_key",
            "bot_user_email",
            "skills",
            "tools",
            "mcp_connections",
        ]


class WorkspaceSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkspaceSkill
        fields = [
            "id",
            "source",
            "global_skill",
            "name",
            "slug",
            "description",
            "knowledge",
            "category",
            "is_active",
        ]


class WorkspaceToolSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkspaceTool
        fields = [
            "id",
            "source",
            "global_tool",
            "name",
            "slug",
            "description",
            "implementation_type",
            "builtin_ref",
            "input_schema",
            "is_destructive",
            "is_active",
        ]


class WorkspaceMCPConnectionSerializer(serializers.ModelSerializer):
    auth_config = serializers.JSONField(write_only=True, required=False)
    env_vars = serializers.JSONField(write_only=True, required=False)

    class Meta:
        model = WorkspaceMCPConnection
        fields = [
            "id",
            "source",
            "global_mcp",
            "name",
            "slug",
            "server_url",
            "auth_type",
            "auth_config",
            "env_vars",
            "tool_manifest",
            "is_active",
        ]
