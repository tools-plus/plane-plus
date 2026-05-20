# InfraWatch — AI module views
# SPDX-License-Identifier: AGPL-3.0-only

from .godmode import (
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

__all__ = [
    "LiteLLMConfigEndpoint",
    "LiteLLMConfigTestConnectionEndpoint",
    "GlobalAgentEndpoint",
    "GlobalAgentDetailEndpoint",
    "GlobalSkillEndpoint",
    "GlobalSkillDetailEndpoint",
    "GlobalToolEndpoint",
    "GlobalToolDetailEndpoint",
    "GlobalMCPConnectionEndpoint",
    "GlobalMCPConnectionDetailEndpoint",
]
