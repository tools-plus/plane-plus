# InfraWatch — serializers for god-mode global AI entities
# SPDX-License-Identifier: AGPL-3.0-only

from rest_framework import serializers

from plane.ai.models import (
    LiteLLMConfig,
    GlobalAgent,
    GlobalSkill,
    GlobalTool,
    GlobalMCPConnection,
)


class LiteLLMConfigSerializer(serializers.ModelSerializer):
    master_key = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = LiteLLMConfig
        fields = [
            "id",
            "endpoint",
            "master_key",
            "provider",
            "model_routing",
            "default_workspace_budget",
            "max_workspace_budget",
            "default_agent_budget",
            "max_agent_budget",
            "is_active",
        ]


class GlobalAgentSerializer(serializers.ModelSerializer):
    skills = serializers.PrimaryKeyRelatedField(
        many=True, queryset=GlobalSkill.objects.all(), required=False
    )
    tools = serializers.PrimaryKeyRelatedField(
        many=True, queryset=GlobalTool.objects.all(), required=False
    )
    mcp_connections = serializers.PrimaryKeyRelatedField(
        many=True, queryset=GlobalMCPConnection.objects.all(), required=False
    )

    class Meta:
        model = GlobalAgent
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "instructions",
            "model_pref",
            "avatar_url",
            "default_monthly_budget",
            "is_active",
            "skills",
            "tools",
            "mcp_connections",
        ]


class GlobalSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalSkill
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "knowledge",
            "category",
            "is_active",
        ]


class GlobalToolSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalTool
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "implementation_type",
            "builtin_ref",
            "input_schema",
            "is_destructive",
            "is_active",
        ]


class GlobalMCPConnectionSerializer(serializers.ModelSerializer):
    auth_config = serializers.JSONField(write_only=True, required=False)
    env_vars = serializers.JSONField(write_only=True, required=False)

    class Meta:
        model = GlobalMCPConnection
        fields = [
            "id",
            "name",
            "slug",
            "server_url",
            "auth_type",
            "auth_config",
            "env_vars",
            "tool_manifest",
            "is_active",
        ]
