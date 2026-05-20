# InfraWatch — god-mode URL patterns for the AI module
# Mounted at: api/god-mode/ai/
# SPDX-License-Identifier: AGPL-3.0-only

from django.urls import path

from plane.iw.views.iw_ai_godmode import (
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
    # LiteLLM config (singleton)
    path(
        "litellm-config/",
        LiteLLMConfigEndpoint.as_view(),
        name="god-mode-ai-litellm-config",
    ),
    path(
        "litellm-config/test-connection/",
        LiteLLMConfigTestConnectionEndpoint.as_view(),
        name="god-mode-ai-litellm-test",
    ),
    # Global Agents
    path(
        "agents/",
        GlobalAgentEndpoint.as_view(),
        name="god-mode-ai-agents",
    ),
    path(
        "agents/<slug:slug>/",
        GlobalAgentDetailEndpoint.as_view(),
        name="god-mode-ai-agent-detail",
    ),
    # Global Skills
    path(
        "skills/",
        GlobalSkillEndpoint.as_view(),
        name="god-mode-ai-skills",
    ),
    path(
        "skills/<slug:slug>/",
        GlobalSkillDetailEndpoint.as_view(),
        name="god-mode-ai-skill-detail",
    ),
    # Global Tools
    path(
        "tools/",
        GlobalToolEndpoint.as_view(),
        name="god-mode-ai-tools",
    ),
    path(
        "tools/<slug:slug>/",
        GlobalToolDetailEndpoint.as_view(),
        name="god-mode-ai-tool-detail",
    ),
    # Global MCP Connections
    path(
        "mcps/",
        GlobalMCPConnectionEndpoint.as_view(),
        name="god-mode-ai-mcps",
    ),
    path(
        "mcps/<slug:slug>/",
        GlobalMCPConnectionDetailEndpoint.as_view(),
        name="god-mode-ai-mcp-detail",
    ),
]
