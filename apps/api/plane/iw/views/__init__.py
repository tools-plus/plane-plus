from .page import (
    PageListCreateAPIEndpoint,
    PageDetailAPIEndpoint,
    PageDescriptionAPIEndpoint,
)

from .epic import (
    EpicListCreateAPIEndpoint,
    EpicDetailAPIEndpoint,
    EpicAnalyticsAPIEndpoint,
)

from .page_folder import (
    WorkspacePageFolderListCreateAPIEndpoint,
    WorkspacePageFolderDetailAPIEndpoint,
)

from .agent_doc import (
    AgentDocListAPIEndpoint,
    AgentDocDetailAPIEndpoint,
)

from .iw_ai_godmode import (
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

from .iw_ai_workspace import (
    WorkspaceAISettingsEndpoint,
    WorkspaceAgentEndpoint,
    WorkspaceAgentDetailEndpoint,
    WorkspaceAgentIncludeEndpoint,
    WorkspaceAgentExcludeEndpoint,
    WorkspaceAgentCloneEndpoint,
    WorkspaceSkillEndpoint,
    WorkspaceSkillDetailEndpoint,
    WorkspaceSkillIncludeEndpoint,
    WorkspaceSkillExcludeEndpoint,
    WorkspaceSkillCloneEndpoint,
    WorkspaceToolEndpoint,
    WorkspaceToolDetailEndpoint,
    WorkspaceToolIncludeEndpoint,
    WorkspaceToolExcludeEndpoint,
    WorkspaceToolCloneEndpoint,
    WorkspaceMCPConnectionEndpoint,
    WorkspaceMCPConnectionDetailEndpoint,
    WorkspaceMCPConnectionIncludeEndpoint,
    WorkspaceMCPConnectionExcludeEndpoint,
    WorkspaceMCPConnectionCloneEndpoint,
    AvailableGlobalAgentsEndpoint,
    AvailableGlobalSkillsEndpoint,
    AvailableGlobalToolsEndpoint,
    AvailableGlobalMCPsEndpoint,
)
