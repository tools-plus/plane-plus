# InfraWatch — Workspace AI REST URL patterns
# SPDX-License-Identifier: AGPL-3.0-only
#
# All patterns here are mounted under:
#   /api/v1/workspaces/<str:slug>/ai/
# via the registration in plane/app/urls/iw_workspace_ai.py

from django.urls import path

from plane.ai.views import (
    WorkspaceAISettingsEndpoint,
    # Agents
    WorkspaceAgentEndpoint,
    WorkspaceAgentDetailEndpoint,
    WorkspaceAgentIncludeEndpoint,
    WorkspaceAgentExcludeEndpoint,
    WorkspaceAgentCloneEndpoint,
    # Skills
    WorkspaceSkillEndpoint,
    WorkspaceSkillDetailEndpoint,
    WorkspaceSkillIncludeEndpoint,
    WorkspaceSkillExcludeEndpoint,
    WorkspaceSkillCloneEndpoint,
    # Tools
    WorkspaceToolEndpoint,
    WorkspaceToolDetailEndpoint,
    WorkspaceToolIncludeEndpoint,
    WorkspaceToolExcludeEndpoint,
    WorkspaceToolCloneEndpoint,
    # MCP Connections
    WorkspaceMCPConnectionEndpoint,
    WorkspaceMCPConnectionDetailEndpoint,
    WorkspaceMCPConnectionIncludeEndpoint,
    WorkspaceMCPConnectionExcludeEndpoint,
    WorkspaceMCPConnectionCloneEndpoint,
    # Available (picker) endpoints
    AvailableGlobalAgentsEndpoint,
    AvailableGlobalSkillsEndpoint,
    AvailableGlobalToolsEndpoint,
    AvailableGlobalMCPsEndpoint,
)

urlpatterns = [
    # ── Settings (singleton) ─────────────────────────────────────────────────
    path(
        "settings/",
        WorkspaceAISettingsEndpoint.as_view(),
        name="workspace-ai-settings",
    ),

    # ── Agents ───────────────────────────────────────────────────────────────
    path(
        "agents/",
        WorkspaceAgentEndpoint.as_view(),
        name="workspace-ai-agents",
    ),
    path(
        "agents/include/",
        WorkspaceAgentIncludeEndpoint.as_view(),
        name="workspace-ai-agents-include",
    ),
    path(
        "agents/exclude/",
        WorkspaceAgentExcludeEndpoint.as_view(),
        name="workspace-ai-agents-exclude",
    ),
    path(
        "agents/clone/",
        WorkspaceAgentCloneEndpoint.as_view(),
        name="workspace-ai-agents-clone",
    ),
    path(
        "agents/<slug:agent_slug>/",
        WorkspaceAgentDetailEndpoint.as_view(),
        name="workspace-ai-agent-detail",
    ),

    # ── Skills ───────────────────────────────────────────────────────────────
    path(
        "skills/",
        WorkspaceSkillEndpoint.as_view(),
        name="workspace-ai-skills",
    ),
    path(
        "skills/include/",
        WorkspaceSkillIncludeEndpoint.as_view(),
        name="workspace-ai-skills-include",
    ),
    path(
        "skills/exclude/",
        WorkspaceSkillExcludeEndpoint.as_view(),
        name="workspace-ai-skills-exclude",
    ),
    path(
        "skills/clone/",
        WorkspaceSkillCloneEndpoint.as_view(),
        name="workspace-ai-skills-clone",
    ),
    path(
        "skills/<slug:skill_slug>/",
        WorkspaceSkillDetailEndpoint.as_view(),
        name="workspace-ai-skill-detail",
    ),

    # ── Tools ────────────────────────────────────────────────────────────────
    path(
        "tools/",
        WorkspaceToolEndpoint.as_view(),
        name="workspace-ai-tools",
    ),
    path(
        "tools/include/",
        WorkspaceToolIncludeEndpoint.as_view(),
        name="workspace-ai-tools-include",
    ),
    path(
        "tools/exclude/",
        WorkspaceToolExcludeEndpoint.as_view(),
        name="workspace-ai-tools-exclude",
    ),
    path(
        "tools/clone/",
        WorkspaceToolCloneEndpoint.as_view(),
        name="workspace-ai-tools-clone",
    ),
    path(
        "tools/<slug:tool_slug>/",
        WorkspaceToolDetailEndpoint.as_view(),
        name="workspace-ai-tool-detail",
    ),

    # ── MCP Connections ──────────────────────────────────────────────────────
    path(
        "mcps/",
        WorkspaceMCPConnectionEndpoint.as_view(),
        name="workspace-ai-mcps",
    ),
    path(
        "mcps/include/",
        WorkspaceMCPConnectionIncludeEndpoint.as_view(),
        name="workspace-ai-mcps-include",
    ),
    path(
        "mcps/exclude/",
        WorkspaceMCPConnectionExcludeEndpoint.as_view(),
        name="workspace-ai-mcps-exclude",
    ),
    path(
        "mcps/clone/",
        WorkspaceMCPConnectionCloneEndpoint.as_view(),
        name="workspace-ai-mcps-clone",
    ),
    path(
        "mcps/<slug:mcp_slug>/",
        WorkspaceMCPConnectionDetailEndpoint.as_view(),
        name="workspace-ai-mcp-detail",
    ),

    # ── Available (UI picker) ────────────────────────────────────────────────
    path(
        "available-agents/",
        AvailableGlobalAgentsEndpoint.as_view(),
        name="workspace-ai-available-agents",
    ),
    path(
        "available-skills/",
        AvailableGlobalSkillsEndpoint.as_view(),
        name="workspace-ai-available-skills",
    ),
    path(
        "available-tools/",
        AvailableGlobalToolsEndpoint.as_view(),
        name="workspace-ai-available-tools",
    ),
    path(
        "available-mcps/",
        AvailableGlobalMCPsEndpoint.as_view(),
        name="workspace-ai-available-mcps",
    ),
]
