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
    # Override URLField → CharField so Django's strict URL validator doesn't
    # reject internal Docker/k8s hostnames like http://plane-litellm:4000.
    # DRF does not call model.full_clean(), so the model-level URLField
    # constraint is bypassed gracefully.
    endpoint = serializers.CharField(max_length=500, required=False)
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
    # Use slug (== builtin_ref for built-ins) so the frontend sends human-readable
    # identifiers instead of opaque UUIDs.
    skills = serializers.SlugRelatedField(
        many=True, queryset=GlobalSkill.objects.all(), slug_field="slug", required=False
    )
    tools = serializers.SlugRelatedField(
        many=True, queryset=GlobalTool.objects.all(), slug_field="slug", required=False
    )
    mcp_connections = serializers.SlugRelatedField(
        many=True, queryset=GlobalMCPConnection.objects.all(), slug_field="slug", required=False
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
