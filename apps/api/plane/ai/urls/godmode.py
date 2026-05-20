# InfraWatch — God-mode AI URL patterns
# SPDX-License-Identifier: AGPL-3.0-only

from django.urls import path

from plane.ai.views import (
    LiteLLMConfigEndpoint,
    LiteLLMConfigTestConnectionEndpoint,
    GlobalAgentEndpoint,
    GlobalAgentDetailEndpoint,
    GlobalSkillEndpoint,
    GlobalSkillDetailEndpoint,
    GlobalToolEndpoint,
    GlobalToolDetailEndpoint,
    GlobalMCPConnectionEndpoint,
    GlobalMCPConnectionDetailEndpoint,
)

urlpatterns = [
    # LiteLLM Config — singleton
    path(
        "litellm-config/",
        LiteLLMConfigEndpoint.as_view(),
        name="god-mode-ai-litellm-config",
    ),
    path(
        "litellm-config/test-connection/",
        LiteLLMConfigTestConnectionEndpoint.as_view(),
        name="god-mode-ai-litellm-config-test",
    ),
    # Global Agents
    path(
        "agents/",
        GlobalAgentEndpoint.as_view(),
        name="god-mode-ai-global-agents",
    ),
    path(
        "agents/<slug:slug>/",
        GlobalAgentDetailEndpoint.as_view(),
        name="god-mode-ai-global-agent-detail",
    ),
    # Global Skills
    path(
        "skills/",
        GlobalSkillEndpoint.as_view(),
        name="god-mode-ai-global-skills",
    ),
    path(
        "skills/<slug:slug>/",
        GlobalSkillDetailEndpoint.as_view(),
        name="god-mode-ai-global-skill-detail",
    ),
    # Global Tools
    path(
        "tools/",
        GlobalToolEndpoint.as_view(),
        name="god-mode-ai-global-tools",
    ),
    path(
        "tools/<slug:slug>/",
        GlobalToolDetailEndpoint.as_view(),
        name="god-mode-ai-global-tool-detail",
    ),
    # Global MCP Connections
    path(
        "mcp-connections/",
        GlobalMCPConnectionEndpoint.as_view(),
        name="god-mode-ai-global-mcp-connections",
    ),
    path(
        "mcp-connections/<slug:slug>/",
        GlobalMCPConnectionDetailEndpoint.as_view(),
        name="god-mode-ai-global-mcp-connection-detail",
    ),
]
