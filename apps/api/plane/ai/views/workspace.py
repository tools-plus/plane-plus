# InfraWatch — AI module workspace REST API views
# SPDX-License-Identifier: AGPL-3.0-only
#
# All endpoints under /api/v1/workspaces/{slug}/ai/

from django.utils.text import slugify

from rest_framework import status
from rest_framework.response import Response

from plane.app.views.base import BaseAPIView
from plane.app.permissions.iw_workspace_ai import (
    WorkspaceAISettingsPermission,
    WorkspaceAIPermission,
)
from plane.db.models import Workspace

from plane.ai.models import (
    LiteLLMConfig,
    WorkspaceAISettings,
    WorkspaceAgent,
    WorkspaceSkill,
    WorkspaceTool,
    WorkspaceMCPConnection,
    GlobalAgent,
    GlobalSkill,
    GlobalTool,
    GlobalMCPConnection,
)
from plane.ai.serializers import (
    WorkspaceAISettingsSerializer,
    WorkspaceAgentSerializer,
    WorkspaceSkillSerializer,
    WorkspaceToolSerializer,
    WorkspaceMCPConnectionSerializer,
)
from plane.ai.serializers.global_ import (
    GlobalAgentSerializer,
    GlobalSkillSerializer,
    GlobalToolSerializer,
    GlobalMCPConnectionSerializer,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_workspace_or_404(slug):
    """Return the Workspace for slug or None."""
    try:
        return Workspace.objects.get(slug=slug)
    except Workspace.DoesNotExist:
        return None


def _get_litellm_config():
    """Return the active LiteLLM config or None."""
    return LiteLLMConfig.objects.filter(is_active=True).first()


def _unique_slug(base_slug, workspace_id, model, instance=None):
    """
    Ensure a slug is unique within the workspace for the given model.
    Appends a numeric suffix if necessary.
    """
    slug = base_slug
    qs = model.objects.filter(workspace_id=workspace_id, slug=slug)
    if instance is not None:
        qs = qs.exclude(pk=instance.pk)
    if not qs.exists():
        return slug
    n = 1
    while True:
        candidate = f"{base_slug}-{n}"
        qs2 = model.objects.filter(workspace_id=workspace_id, slug=candidate)
        if instance is not None:
            qs2 = qs2.exclude(pk=instance.pk)
        if not qs2.exists():
            return candidate
        n += 1


# ---------------------------------------------------------------------------
# WorkspaceAISettings (singleton per workspace)
# ---------------------------------------------------------------------------


class WorkspaceAISettingsEndpoint(BaseAPIView):
    """
    GET  /api/v1/workspaces/{slug}/ai/settings/  — retrieve (auto-create with defaults)
    PATCH /api/v1/workspaces/{slug}/ai/settings/ — update is_enabled, monthly_budget
    """

    permission_classes = [WorkspaceAISettingsPermission]

    def get(self, request, slug):
        workspace = _get_workspace_or_404(slug)
        if workspace is None:
            return Response({"error": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)

        settings, _ = WorkspaceAISettings.objects.get_or_create(
            workspace=workspace,
            defaults={"is_enabled": False, "monthly_budget": 20.00},
        )
        return Response(WorkspaceAISettingsSerializer(settings).data, status=status.HTTP_200_OK)

    def patch(self, request, slug):
        workspace = _get_workspace_or_404(slug)
        if workspace is None:
            return Response({"error": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)

        settings, _ = WorkspaceAISettings.objects.get_or_create(
            workspace=workspace,
            defaults={"is_enabled": False, "monthly_budget": 20.00},
        )

        # Budget cap validation
        monthly_budget = request.data.get("monthly_budget")
        if monthly_budget is not None:
            config = _get_litellm_config()
            if config is not None:
                try:
                    if float(monthly_budget) > float(config.max_workspace_budget):
                        return Response(
                            {
                                "error": (
                                    f"monthly_budget cannot exceed the platform maximum "
                                    f"of {config.max_workspace_budget}"
                                )
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                except (TypeError, ValueError):
                    return Response(
                        {"error": "monthly_budget must be a number"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        serializer = WorkspaceAISettingsSerializer(settings, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# WorkspaceAgent  — list, create, include, exclude, clone
# ---------------------------------------------------------------------------


class WorkspaceAgentEndpoint(BaseAPIView):
    """
    GET  /api/v1/workspaces/{slug}/ai/agents/  — list active workspace agents
    POST /api/v1/workspaces/{slug}/ai/agents/  — create a custom workspace agent
    """

    permission_classes = [WorkspaceAIPermission]

    def get(self, request, slug):
        workspace = _get_workspace_or_404(slug)
        if workspace is None:
            return Response({"error": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)

        agents = WorkspaceAgent.objects.filter(
            workspace=workspace, is_active=True
        ).order_by("name")
        return Response(WorkspaceAgentSerializer(agents, many=True).data, status=status.HTTP_200_OK)

    def post(self, request, slug):
        workspace = _get_workspace_or_404(slug)
        if workspace is None:
            return Response({"error": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)

        name = request.data.get("name", "").strip()
        if not name:
            return Response({"error": "name is required"}, status=status.HTTP_400_BAD_REQUEST)

        agent_slug = _unique_slug(
            slugify(name), workspace.id, WorkspaceAgent
        )

        data = {**request.data, "slug": agent_slug, "source": "workspace"}
        serializer = WorkspaceAgentSerializer(data=data)
        if serializer.is_valid():
            serializer.save(workspace=workspace, source="workspace", slug=agent_slug)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WorkspaceAgentDetailEndpoint(BaseAPIView):
    """
    GET    /api/v1/workspaces/{slug}/ai/agents/{agent_slug}/
    PATCH  /api/v1/workspaces/{slug}/ai/agents/{agent_slug}/
    DELETE /api/v1/workspaces/{slug}/ai/agents/{agent_slug}/
    """

    permission_classes = [WorkspaceAIPermission]

    def _get_agent(self, slug, agent_slug):
        try:
            return WorkspaceAgent.objects.get(workspace__slug=slug, slug=agent_slug)
        except WorkspaceAgent.DoesNotExist:
            return None

    def get(self, request, slug, agent_slug):
        agent = self._get_agent(slug, agent_slug)
        if agent is None:
            return Response({"error": "Agent not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(WorkspaceAgentSerializer(agent).data, status=status.HTTP_200_OK)

    def patch(self, request, slug, agent_slug):
        agent = self._get_agent(slug, agent_slug)
        if agent is None:
            return Response({"error": "Agent not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = WorkspaceAgentSerializer(agent, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, slug, agent_slug):
        agent = self._get_agent(slug, agent_slug)
        if agent is None:
            return Response({"error": "Agent not found"}, status=status.HTTP_404_NOT_FOUND)
        agent.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WorkspaceAgentIncludeEndpoint(BaseAPIView):
    """
    POST /api/v1/workspaces/{slug}/ai/agents/include/
    body: {"global_agent_slug": "rhea"}

    Creates a WorkspaceAgent(source="global") mirroring the GlobalAgent.
    Bot provisioning happens automatically via signal.
    """

    permission_classes = [WorkspaceAIPermission]

    def post(self, request, slug):
        workspace = _get_workspace_or_404(slug)
        if workspace is None:
            return Response({"error": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)

        global_agent_slug = request.data.get("global_agent_slug", "").strip()
        if not global_agent_slug:
            return Response(
                {"error": "global_agent_slug is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            global_agent = GlobalAgent.objects.get(slug=global_agent_slug, is_active=True)
        except GlobalAgent.DoesNotExist:
            return Response(
                {"error": f"Global agent '{global_agent_slug}' not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Idempotent — if already included, return the existing record
        existing = WorkspaceAgent.objects.filter(
            workspace=workspace, global_agent=global_agent, source="global"
        ).first()
        if existing is not None:
            return Response(WorkspaceAgentSerializer(existing).data, status=status.HTTP_200_OK)

        agent_slug = _unique_slug(global_agent.slug, workspace.id, WorkspaceAgent)
        agent = WorkspaceAgent.objects.create(
            workspace=workspace,
            source="global",
            global_agent=global_agent,
            name=global_agent.name,
            slug=agent_slug,
            description=global_agent.description,
            instructions=global_agent.instructions,
            model_pref=global_agent.model_pref,
            avatar_url=global_agent.avatar_url,
            monthly_budget=global_agent.default_monthly_budget,
            is_active=True,
        )
        return Response(WorkspaceAgentSerializer(agent).data, status=status.HTTP_201_CREATED)


class WorkspaceAgentExcludeEndpoint(BaseAPIView):
    """
    POST /api/v1/workspaces/{slug}/ai/agents/exclude/
    body: {"agent_slug": "rhea"}

    Deletes the WorkspaceAgent (signal handles bot cleanup).
    """

    permission_classes = [WorkspaceAIPermission]

    def post(self, request, slug):
        workspace = _get_workspace_or_404(slug)
        if workspace is None:
            return Response({"error": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)

        agent_slug = request.data.get("agent_slug", "").strip()
        if not agent_slug:
            return Response({"error": "agent_slug is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            agent = WorkspaceAgent.objects.get(workspace=workspace, slug=agent_slug)
        except WorkspaceAgent.DoesNotExist:
            return Response({"error": "Agent not found"}, status=status.HTTP_404_NOT_FOUND)

        agent.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WorkspaceAgentCloneEndpoint(BaseAPIView):
    """
    POST /api/v1/workspaces/{slug}/ai/agents/clone/
    body: {"global_agent_slug": "rhea", "name": "Custom Rhea"}

    Creates a WorkspaceAgent(source="workspace") that is an editable copy
    of the GlobalAgent. New slug derived from the supplied name.
    """

    permission_classes = [WorkspaceAIPermission]

    def post(self, request, slug):
        workspace = _get_workspace_or_404(slug)
        if workspace is None:
            return Response({"error": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)

        global_agent_slug = request.data.get("global_agent_slug", "").strip()
        name = request.data.get("name", "").strip()

        if not global_agent_slug:
            return Response(
                {"error": "global_agent_slug is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            global_agent = GlobalAgent.objects.get(slug=global_agent_slug, is_active=True)
        except GlobalAgent.DoesNotExist:
            return Response(
                {"error": f"Global agent '{global_agent_slug}' not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        clone_name = name if name else f"{global_agent.name} (copy)"
        agent_slug = _unique_slug(slugify(clone_name), workspace.id, WorkspaceAgent)

        agent = WorkspaceAgent.objects.create(
            workspace=workspace,
            source="workspace",
            global_agent=None,  # clone is independent
            name=clone_name,
            slug=agent_slug,
            description=global_agent.description,
            instructions=global_agent.instructions,
            model_pref=global_agent.model_pref,
            avatar_url=global_agent.avatar_url,
            monthly_budget=global_agent.default_monthly_budget,
            is_active=True,
        )
        return Response(WorkspaceAgentSerializer(agent).data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# WorkspaceSkill  — list, create, include, exclude, clone
# ---------------------------------------------------------------------------


class WorkspaceSkillEndpoint(BaseAPIView):
    """
    GET  /api/v1/workspaces/{slug}/ai/skills/
    POST /api/v1/workspaces/{slug}/ai/skills/
    """

    permission_classes = [WorkspaceAIPermission]

    def get(self, request, slug):
        workspace = _get_workspace_or_404(slug)
        if workspace is None:
            return Response({"error": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)
        skills = WorkspaceSkill.objects.filter(workspace=workspace, is_active=True).order_by("name")
        return Response(WorkspaceSkillSerializer(skills, many=True).data, status=status.HTTP_200_OK)

    def post(self, request, slug):
        workspace = _get_workspace_or_404(slug)
        if workspace is None:
            return Response({"error": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)

        name = request.data.get("name", "").strip()
        if not name:
            return Response({"error": "name is required"}, status=status.HTTP_400_BAD_REQUEST)

        skill_slug = _unique_slug(slugify(name), workspace.id, WorkspaceSkill)
        serializer = WorkspaceSkillSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(workspace=workspace, source="workspace", slug=skill_slug)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WorkspaceSkillDetailEndpoint(BaseAPIView):
    """
    GET    /api/v1/workspaces/{slug}/ai/skills/{skill_slug}/
    PATCH  /api/v1/workspaces/{slug}/ai/skills/{skill_slug}/
    DELETE /api/v1/workspaces/{slug}/ai/skills/{skill_slug}/
    """

    permission_classes = [WorkspaceAIPermission]

    def _get_skill(self, slug, skill_slug):
        try:
            return WorkspaceSkill.objects.get(workspace__slug=slug, slug=skill_slug)
        except WorkspaceSkill.DoesNotExist:
            return None

    def get(self, request, slug, skill_slug):
        skill = self._get_skill(slug, skill_slug)
        if skill is None:
            return Response({"error": "Skill not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(WorkspaceSkillSerializer(skill).data, status=status.HTTP_200_OK)

    def patch(self, request, slug, skill_slug):
        skill = self._get_skill(slug, skill_slug)
        if skill is None:
            return Response({"error": "Skill not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = WorkspaceSkillSerializer(skill, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, slug, skill_slug):
        skill = self._get_skill(slug, skill_slug)
        if skill is None:
            return Response({"error": "Skill not found"}, status=status.HTTP_404_NOT_FOUND)
        skill.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WorkspaceSkillIncludeEndpoint(BaseAPIView):
    """POST /api/v1/workspaces/{slug}/ai/skills/include/"""

    permission_classes = [WorkspaceAIPermission]

    def post(self, request, slug):
        workspace = _get_workspace_or_404(slug)
        if workspace is None:
            return Response({"error": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)

        global_skill_slug = request.data.get("global_skill_slug", "").strip()
        if not global_skill_slug:
            return Response(
                {"error": "global_skill_slug is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            global_skill = GlobalSkill.objects.get(slug=global_skill_slug, is_active=True)
        except GlobalSkill.DoesNotExist:
            return Response(
                {"error": f"Global skill '{global_skill_slug}' not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        existing = WorkspaceSkill.objects.filter(
            workspace=workspace, global_skill=global_skill, source="global"
        ).first()
        if existing is not None:
            return Response(WorkspaceSkillSerializer(existing).data, status=status.HTTP_200_OK)

        skill_slug = _unique_slug(global_skill.slug, workspace.id, WorkspaceSkill)
        skill = WorkspaceSkill.objects.create(
            workspace=workspace,
            source="global",
            global_skill=global_skill,
            name=global_skill.name,
            slug=skill_slug,
            description=global_skill.description,
            knowledge=global_skill.knowledge,
            category=global_skill.category,
            is_active=True,
        )
        return Response(WorkspaceSkillSerializer(skill).data, status=status.HTTP_201_CREATED)


class WorkspaceSkillExcludeEndpoint(BaseAPIView):
    """POST /api/v1/workspaces/{slug}/ai/skills/exclude/"""

    permission_classes = [WorkspaceAIPermission]

    def post(self, request, slug):
        workspace = _get_workspace_or_404(slug)
        if workspace is None:
            return Response({"error": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)

        skill_slug = request.data.get("skill_slug", "").strip()
        if not skill_slug:
            return Response({"error": "skill_slug is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            skill = WorkspaceSkill.objects.get(workspace=workspace, slug=skill_slug)
        except WorkspaceSkill.DoesNotExist:
            return Response({"error": "Skill not found"}, status=status.HTTP_404_NOT_FOUND)

        skill.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WorkspaceSkillCloneEndpoint(BaseAPIView):
    """POST /api/v1/workspaces/{slug}/ai/skills/clone/"""

    permission_classes = [WorkspaceAIPermission]

    def post(self, request, slug):
        workspace = _get_workspace_or_404(slug)
        if workspace is None:
            return Response({"error": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)

        global_skill_slug = request.data.get("global_skill_slug", "").strip()
        name = request.data.get("name", "").strip()

        if not global_skill_slug:
            return Response(
                {"error": "global_skill_slug is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            global_skill = GlobalSkill.objects.get(slug=global_skill_slug, is_active=True)
        except GlobalSkill.DoesNotExist:
            return Response(
                {"error": f"Global skill '{global_skill_slug}' not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        clone_name = name if name else f"{global_skill.name} (copy)"
        skill_slug = _unique_slug(slugify(clone_name), workspace.id, WorkspaceSkill)
        skill = WorkspaceSkill.objects.create(
            workspace=workspace,
            source="workspace",
            global_skill=None,
            name=clone_name,
            slug=skill_slug,
            description=global_skill.description,
            knowledge=global_skill.knowledge,
            category=global_skill.category,
            is_active=True,
        )
        return Response(WorkspaceSkillSerializer(skill).data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# WorkspaceTool  — list, create, include, exclude, clone
# ---------------------------------------------------------------------------


class WorkspaceToolEndpoint(BaseAPIView):
    """
    GET  /api/v1/workspaces/{slug}/ai/tools/
    POST /api/v1/workspaces/{slug}/ai/tools/
    """

    permission_classes = [WorkspaceAIPermission]

    def get(self, request, slug):
        workspace = _get_workspace_or_404(slug)
        if workspace is None:
            return Response({"error": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)
        tools = WorkspaceTool.objects.filter(workspace=workspace, is_active=True).order_by("name")
        return Response(WorkspaceToolSerializer(tools, many=True).data, status=status.HTTP_200_OK)

    def post(self, request, slug):
        workspace = _get_workspace_or_404(slug)
        if workspace is None:
            return Response({"error": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)

        name = request.data.get("name", "").strip()
        if not name:
            return Response({"error": "name is required"}, status=status.HTTP_400_BAD_REQUEST)

        tool_slug = _unique_slug(slugify(name), workspace.id, WorkspaceTool)
        serializer = WorkspaceToolSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(workspace=workspace, source="workspace", slug=tool_slug)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WorkspaceToolDetailEndpoint(BaseAPIView):
    """
    GET    /api/v1/workspaces/{slug}/ai/tools/{tool_slug}/
    PATCH  /api/v1/workspaces/{slug}/ai/tools/{tool_slug}/
    DELETE /api/v1/workspaces/{slug}/ai/tools/{tool_slug}/
    """

    permission_classes = [WorkspaceAIPermission]

    def _get_tool(self, slug, tool_slug):
        try:
            return WorkspaceTool.objects.get(workspace__slug=slug, slug=tool_slug)
        except WorkspaceTool.DoesNotExist:
            return None

    def get(self, request, slug, tool_slug):
        tool = self._get_tool(slug, tool_slug)
        if tool is None:
            return Response({"error": "Tool not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(WorkspaceToolSerializer(tool).data, status=status.HTTP_200_OK)

    def patch(self, request, slug, tool_slug):
        tool = self._get_tool(slug, tool_slug)
        if tool is None:
            return Response({"error": "Tool not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = WorkspaceToolSerializer(tool, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, slug, tool_slug):
        tool = self._get_tool(slug, tool_slug)
        if tool is None:
            return Response({"error": "Tool not found"}, status=status.HTTP_404_NOT_FOUND)
        tool.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WorkspaceToolIncludeEndpoint(BaseAPIView):
    """POST /api/v1/workspaces/{slug}/ai/tools/include/"""

    permission_classes = [WorkspaceAIPermission]

    def post(self, request, slug):
        workspace = _get_workspace_or_404(slug)
        if workspace is None:
            return Response({"error": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)

        global_tool_slug = request.data.get("global_tool_slug", "").strip()
        if not global_tool_slug:
            return Response(
                {"error": "global_tool_slug is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            global_tool = GlobalTool.objects.get(slug=global_tool_slug, is_active=True)
        except GlobalTool.DoesNotExist:
            return Response(
                {"error": f"Global tool '{global_tool_slug}' not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        existing = WorkspaceTool.objects.filter(
            workspace=workspace, global_tool=global_tool, source="global"
        ).first()
        if existing is not None:
            return Response(WorkspaceToolSerializer(existing).data, status=status.HTTP_200_OK)

        tool_slug = _unique_slug(global_tool.slug, workspace.id, WorkspaceTool)
        tool = WorkspaceTool.objects.create(
            workspace=workspace,
            source="global",
            global_tool=global_tool,
            name=global_tool.name,
            slug=tool_slug,
            description=global_tool.description,
            implementation_type=global_tool.implementation_type,
            builtin_ref=global_tool.builtin_ref,
            input_schema=global_tool.input_schema,
            is_destructive=global_tool.is_destructive,
            is_active=True,
        )
        return Response(WorkspaceToolSerializer(tool).data, status=status.HTTP_201_CREATED)


class WorkspaceToolExcludeEndpoint(BaseAPIView):
    """POST /api/v1/workspaces/{slug}/ai/tools/exclude/"""

    permission_classes = [WorkspaceAIPermission]

    def post(self, request, slug):
        workspace = _get_workspace_or_404(slug)
        if workspace is None:
            return Response({"error": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)

        tool_slug = request.data.get("tool_slug", "").strip()
        if not tool_slug:
            return Response({"error": "tool_slug is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tool = WorkspaceTool.objects.get(workspace=workspace, slug=tool_slug)
        except WorkspaceTool.DoesNotExist:
            return Response({"error": "Tool not found"}, status=status.HTTP_404_NOT_FOUND)

        tool.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WorkspaceToolCloneEndpoint(BaseAPIView):
    """POST /api/v1/workspaces/{slug}/ai/tools/clone/"""

    permission_classes = [WorkspaceAIPermission]

    def post(self, request, slug):
        workspace = _get_workspace_or_404(slug)
        if workspace is None:
            return Response({"error": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)

        global_tool_slug = request.data.get("global_tool_slug", "").strip()
        name = request.data.get("name", "").strip()

        if not global_tool_slug:
            return Response(
                {"error": "global_tool_slug is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            global_tool = GlobalTool.objects.get(slug=global_tool_slug, is_active=True)
        except GlobalTool.DoesNotExist:
            return Response(
                {"error": f"Global tool '{global_tool_slug}' not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        clone_name = name if name else f"{global_tool.name} (copy)"
        tool_slug = _unique_slug(slugify(clone_name), workspace.id, WorkspaceTool)
        tool = WorkspaceTool.objects.create(
            workspace=workspace,
            source="workspace",
            global_tool=None,
            name=clone_name,
            slug=tool_slug,
            description=global_tool.description,
            implementation_type=global_tool.implementation_type,
            builtin_ref=global_tool.builtin_ref,
            input_schema=global_tool.input_schema,
            is_destructive=global_tool.is_destructive,
            is_active=True,
        )
        return Response(WorkspaceToolSerializer(tool).data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# WorkspaceMCPConnection  — list, create, include, exclude, clone
# ---------------------------------------------------------------------------


class WorkspaceMCPConnectionEndpoint(BaseAPIView):
    """
    GET  /api/v1/workspaces/{slug}/ai/mcps/
    POST /api/v1/workspaces/{slug}/ai/mcps/
    """

    permission_classes = [WorkspaceAIPermission]

    def get(self, request, slug):
        workspace = _get_workspace_or_404(slug)
        if workspace is None:
            return Response({"error": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)
        mcps = WorkspaceMCPConnection.objects.filter(
            workspace=workspace, is_active=True
        ).order_by("name")
        return Response(
            WorkspaceMCPConnectionSerializer(mcps, many=True).data, status=status.HTTP_200_OK
        )

    def post(self, request, slug):
        workspace = _get_workspace_or_404(slug)
        if workspace is None:
            return Response({"error": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)

        name = request.data.get("name", "").strip()
        if not name:
            return Response({"error": "name is required"}, status=status.HTTP_400_BAD_REQUEST)

        mcp_slug = _unique_slug(slugify(name), workspace.id, WorkspaceMCPConnection)
        serializer = WorkspaceMCPConnectionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(workspace=workspace, source="workspace", slug=mcp_slug)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WorkspaceMCPConnectionDetailEndpoint(BaseAPIView):
    """
    GET    /api/v1/workspaces/{slug}/ai/mcps/{mcp_slug}/
    PATCH  /api/v1/workspaces/{slug}/ai/mcps/{mcp_slug}/
    DELETE /api/v1/workspaces/{slug}/ai/mcps/{mcp_slug}/
    """

    permission_classes = [WorkspaceAIPermission]

    def _get_mcp(self, slug, mcp_slug):
        try:
            return WorkspaceMCPConnection.objects.get(workspace__slug=slug, slug=mcp_slug)
        except WorkspaceMCPConnection.DoesNotExist:
            return None

    def get(self, request, slug, mcp_slug):
        mcp = self._get_mcp(slug, mcp_slug)
        if mcp is None:
            return Response({"error": "MCP connection not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(WorkspaceMCPConnectionSerializer(mcp).data, status=status.HTTP_200_OK)

    def patch(self, request, slug, mcp_slug):
        mcp = self._get_mcp(slug, mcp_slug)
        if mcp is None:
            return Response({"error": "MCP connection not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = WorkspaceMCPConnectionSerializer(mcp, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, slug, mcp_slug):
        mcp = self._get_mcp(slug, mcp_slug)
        if mcp is None:
            return Response({"error": "MCP connection not found"}, status=status.HTTP_404_NOT_FOUND)
        mcp.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WorkspaceMCPConnectionIncludeEndpoint(BaseAPIView):
    """POST /api/v1/workspaces/{slug}/ai/mcps/include/"""

    permission_classes = [WorkspaceAIPermission]

    def post(self, request, slug):
        workspace = _get_workspace_or_404(slug)
        if workspace is None:
            return Response({"error": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)

        global_mcp_slug = request.data.get("global_mcp_slug", "").strip()
        if not global_mcp_slug:
            return Response(
                {"error": "global_mcp_slug is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            global_mcp = GlobalMCPConnection.objects.get(slug=global_mcp_slug, is_active=True)
        except GlobalMCPConnection.DoesNotExist:
            return Response(
                {"error": f"Global MCP connection '{global_mcp_slug}' not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        existing = WorkspaceMCPConnection.objects.filter(
            workspace=workspace, global_mcp=global_mcp, source="global"
        ).first()
        if existing is not None:
            return Response(
                WorkspaceMCPConnectionSerializer(existing).data, status=status.HTTP_200_OK
            )

        mcp_slug = _unique_slug(global_mcp.slug, workspace.id, WorkspaceMCPConnection)
        mcp = WorkspaceMCPConnection.objects.create(
            workspace=workspace,
            source="global",
            global_mcp=global_mcp,
            name=global_mcp.name,
            slug=mcp_slug,
            server_url=global_mcp.server_url,
            auth_type=global_mcp.auth_type,
            auth_config=global_mcp.auth_config,
            env_vars=global_mcp.env_vars,
            tool_manifest=global_mcp.tool_manifest,
            is_active=True,
        )
        return Response(WorkspaceMCPConnectionSerializer(mcp).data, status=status.HTTP_201_CREATED)


class WorkspaceMCPConnectionExcludeEndpoint(BaseAPIView):
    """POST /api/v1/workspaces/{slug}/ai/mcps/exclude/"""

    permission_classes = [WorkspaceAIPermission]

    def post(self, request, slug):
        workspace = _get_workspace_or_404(slug)
        if workspace is None:
            return Response({"error": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)

        mcp_slug = request.data.get("mcp_slug", "").strip()
        if not mcp_slug:
            return Response({"error": "mcp_slug is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            mcp = WorkspaceMCPConnection.objects.get(workspace=workspace, slug=mcp_slug)
        except WorkspaceMCPConnection.DoesNotExist:
            return Response({"error": "MCP connection not found"}, status=status.HTTP_404_NOT_FOUND)

        mcp.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WorkspaceMCPConnectionCloneEndpoint(BaseAPIView):
    """POST /api/v1/workspaces/{slug}/ai/mcps/clone/"""

    permission_classes = [WorkspaceAIPermission]

    def post(self, request, slug):
        workspace = _get_workspace_or_404(slug)
        if workspace is None:
            return Response({"error": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)

        global_mcp_slug = request.data.get("global_mcp_slug", "").strip()
        name = request.data.get("name", "").strip()

        if not global_mcp_slug:
            return Response(
                {"error": "global_mcp_slug is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            global_mcp = GlobalMCPConnection.objects.get(slug=global_mcp_slug, is_active=True)
        except GlobalMCPConnection.DoesNotExist:
            return Response(
                {"error": f"Global MCP connection '{global_mcp_slug}' not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        clone_name = name if name else f"{global_mcp.name} (copy)"
        mcp_slug = _unique_slug(slugify(clone_name), workspace.id, WorkspaceMCPConnection)
        mcp = WorkspaceMCPConnection.objects.create(
            workspace=workspace,
            source="workspace",
            global_mcp=None,
            name=clone_name,
            slug=mcp_slug,
            server_url=global_mcp.server_url,
            auth_type=global_mcp.auth_type,
            auth_config={},  # don't copy credentials
            env_vars={},
            tool_manifest=global_mcp.tool_manifest,
            is_active=True,
        )
        return Response(WorkspaceMCPConnectionSerializer(mcp).data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Available global entities (picker endpoints for UI)
# ---------------------------------------------------------------------------


class AvailableGlobalAgentsEndpoint(BaseAPIView):
    """
    GET /api/v1/workspaces/{slug}/ai/available-agents/
    Returns GlobalAgents not yet included in this workspace.
    """

    permission_classes = [WorkspaceAIPermission]

    def get(self, request, slug):
        workspace = _get_workspace_or_404(slug)
        if workspace is None:
            return Response({"error": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)

        included_global_ids = WorkspaceAgent.objects.filter(
            workspace=workspace, source="global"
        ).values_list("global_agent_id", flat=True)

        available = GlobalAgent.objects.filter(is_active=True).exclude(
            id__in=included_global_ids
        ).order_by("name")
        return Response(GlobalAgentSerializer(available, many=True).data, status=status.HTTP_200_OK)


class AvailableGlobalSkillsEndpoint(BaseAPIView):
    """
    GET /api/v1/workspaces/{slug}/ai/available-skills/
    Returns GlobalSkills not yet included in this workspace.
    """

    permission_classes = [WorkspaceAIPermission]

    def get(self, request, slug):
        workspace = _get_workspace_or_404(slug)
        if workspace is None:
            return Response({"error": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)

        included_global_ids = WorkspaceSkill.objects.filter(
            workspace=workspace, source="global"
        ).values_list("global_skill_id", flat=True)

        available = GlobalSkill.objects.filter(is_active=True).exclude(
            id__in=included_global_ids
        ).order_by("name")
        return Response(GlobalSkillSerializer(available, many=True).data, status=status.HTTP_200_OK)


class AvailableGlobalToolsEndpoint(BaseAPIView):
    """
    GET /api/v1/workspaces/{slug}/ai/available-tools/
    Returns GlobalTools not yet included in this workspace.
    """

    permission_classes = [WorkspaceAIPermission]

    def get(self, request, slug):
        workspace = _get_workspace_or_404(slug)
        if workspace is None:
            return Response({"error": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)

        included_global_ids = WorkspaceTool.objects.filter(
            workspace=workspace, source="global"
        ).values_list("global_tool_id", flat=True)

        available = GlobalTool.objects.filter(is_active=True).exclude(
            id__in=included_global_ids
        ).order_by("name")
        return Response(GlobalToolSerializer(available, many=True).data, status=status.HTTP_200_OK)


class AvailableGlobalMCPsEndpoint(BaseAPIView):
    """
    GET /api/v1/workspaces/{slug}/ai/available-mcps/
    Returns GlobalMCPConnections not yet included in this workspace.
    """

    permission_classes = [WorkspaceAIPermission]

    def get(self, request, slug):
        workspace = _get_workspace_or_404(slug)
        if workspace is None:
            return Response({"error": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)

        included_global_ids = WorkspaceMCPConnection.objects.filter(
            workspace=workspace, source="global"
        ).values_list("global_mcp_id", flat=True)

        available = GlobalMCPConnection.objects.filter(is_active=True).exclude(
            id__in=included_global_ids
        ).order_by("name")
        return Response(
            GlobalMCPConnectionSerializer(available, many=True).data, status=status.HTTP_200_OK
        )
