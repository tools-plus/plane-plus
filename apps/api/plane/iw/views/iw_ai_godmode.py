# InfraWatch — God-mode REST API for AI module global entities
# SPDX-License-Identifier: AGPL-3.0-only

import json as json_lib

from rest_framework import status
from rest_framework.response import Response

from plane.app.views import BaseAPIView
from plane.license.api.permissions import InstanceAdminPermission

from plane.ai.litellm_client import LiteLLMClient
from plane.ai.models import (
    LiteLLMConfig,
    GlobalAgent,
    GlobalSkill,
    GlobalTool,
    GlobalMCPConnection,
)
from plane.ai.serializers import (
    LiteLLMConfigSerializer,
    GlobalAgentSerializer,
    GlobalSkillSerializer,
    GlobalToolSerializer,
    GlobalMCPConnectionSerializer,
)


# ---------------------------------------------------------------------------
# LiteLLM Config — singleton (GET + PATCH) and test-connection
# ---------------------------------------------------------------------------


class LiteLLMConfigEndpoint(BaseAPIView):
    """Retrieve or update the singleton LiteLLM gateway configuration."""

    permission_classes = [InstanceAdminPermission]

    # Budget fields sent as empty strings from the form → remove so model defaults apply.
    _BUDGET_FIELDS = (
        "default_workspace_budget",
        "max_workspace_budget",
        "default_agent_budget",
        "max_agent_budget",
    )

    def _clean_data(self, raw, is_create: bool) -> dict:
        """
        Sanitize incoming form data before passing to the serializer:

        - Empty budget strings → omitted (model defaults on create; no-op on update)
        - Empty master_key on update → omitted (retain stored value)
        - model_routing string → parsed to dict; empty string → {}
        """
        data = dict(raw)

        # Budget fields: DRF's DecimalField rejects "" — strip it
        for field in self._BUDGET_FIELDS:
            if data.get(field) == "":
                data.pop(field, None)

        # master_key: "" on update means "don't change"
        if not is_create and data.get("master_key") == "":
            data.pop("master_key", None)

        # model_routing: textarea sends a JSON string; JSONField expects a dict
        routing = data.get("model_routing")
        if isinstance(routing, str):
            routing = routing.strip()
            if routing == "":
                data["model_routing"] = {}
            else:
                try:
                    data["model_routing"] = json_lib.loads(routing)
                except (json_lib.JSONDecodeError, ValueError):
                    data["model_routing"] = {}

        return data

    def get(self, request):
        config = LiteLLMConfig.objects.first()
        if config is None:
            return Response(
                {"detail": "LiteLLM config not configured."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = LiteLLMConfigSerializer(config)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        config = LiteLLMConfig.objects.first()
        if config is None:
            # First save — create a new record
            cleaned = self._clean_data(request.data, is_create=True)
            serializer = LiteLLMConfigSerializer(data=cleaned)
        else:
            cleaned = self._clean_data(request.data, is_create=False)
            serializer = LiteLLMConfigSerializer(config, data=cleaned, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LiteLLMConfigTestConnectionEndpoint(BaseAPIView):
    """Test connectivity to the configured LiteLLM endpoint."""

    permission_classes = [InstanceAdminPermission]

    def post(self, request):
        config = LiteLLMConfig.objects.first()
        if config is None:
            return Response(
                {"detail": "LiteLLM not configured yet. Save the configuration first."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        client = LiteLLMClient(config.endpoint, config.master_key)
        if client.health_check():
            return Response({"status": "ok"}, status=status.HTTP_200_OK)
        return Response(
            {"detail": "Cannot reach LiteLLM endpoint. Check the endpoint URL and master key."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class LiteLLMConfigTestModelEndpoint(BaseAPIView):
    """Send a minimal chat completion through LiteLLM to verify end-to-end routing.

    Accepts an optional ``model`` body parameter (e.g. "anthropic/claude-3-haiku-20240307").
    Falls back to the provider stored in LiteLLMConfig when omitted.
    """

    permission_classes = [InstanceAdminPermission]

    def post(self, request):
        import requests as req_lib

        config = LiteLLMConfig.objects.first()
        if config is None:
            return Response(
                {"detail": "LiteLLM not configured yet. Save the configuration first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        model = request.data.get("model") or config.provider
        url = f"{config.endpoint.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {config.master_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "Say hello in one word."}],
            "max_tokens": 10,
        }

        try:
            resp = req_lib.post(url, json=payload, headers=headers, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                reply = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                )
                return Response(
                    {"status": "ok", "model": model, "reply": reply},
                    status=status.HTTP_200_OK,
                )
            # Pass through LiteLLM's error body for easier debugging
            try:
                err = resp.json()
            except Exception:
                err = {"detail": resp.text}
            return Response(err, status=resp.status_code)
        except req_lib.exceptions.Timeout:
            return Response(
                {"detail": f"Request to LiteLLM timed out after 30 s. Model: {model}"},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        except Exception as exc:
            return Response(
                {"detail": f"Unexpected error: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )


# ---------------------------------------------------------------------------
# Global Agents
# ---------------------------------------------------------------------------


class GlobalAgentEndpoint(BaseAPIView):
    """List and create global agents."""

    permission_classes = [InstanceAdminPermission]

    def get(self, request):
        agents = GlobalAgent.objects.all().order_by("name")
        serializer = GlobalAgentSerializer(agents, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = GlobalAgentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GlobalAgentDetailEndpoint(BaseAPIView):
    """Retrieve, update, or delete a global agent by slug."""

    permission_classes = [InstanceAdminPermission]

    def _get_agent(self, slug):
        try:
            return GlobalAgent.objects.get(slug=slug)
        except GlobalAgent.DoesNotExist:
            return None

    def get(self, request, slug):
        agent = self._get_agent(slug)
        if agent is None:
            return Response(
                {"detail": "Agent not found."}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = GlobalAgentSerializer(agent)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, slug):
        agent = self._get_agent(slug)
        if agent is None:
            return Response(
                {"detail": "Agent not found."}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = GlobalAgentSerializer(agent, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, slug):
        agent = self._get_agent(slug)
        if agent is None:
            return Response(
                {"detail": "Agent not found."}, status=status.HTTP_404_NOT_FOUND
            )
        agent.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Global Skills
# ---------------------------------------------------------------------------


class GlobalSkillEndpoint(BaseAPIView):
    """List and create global skills."""

    permission_classes = [InstanceAdminPermission]

    def get(self, request):
        skills = GlobalSkill.objects.all().order_by("name")
        serializer = GlobalSkillSerializer(skills, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = GlobalSkillSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GlobalSkillDetailEndpoint(BaseAPIView):
    """Retrieve, update, or delete a global skill by slug."""

    permission_classes = [InstanceAdminPermission]

    def _get_skill(self, slug):
        try:
            return GlobalSkill.objects.get(slug=slug)
        except GlobalSkill.DoesNotExist:
            return None

    def get(self, request, slug):
        skill = self._get_skill(slug)
        if skill is None:
            return Response(
                {"detail": "Skill not found."}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = GlobalSkillSerializer(skill)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, slug):
        skill = self._get_skill(slug)
        if skill is None:
            return Response(
                {"detail": "Skill not found."}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = GlobalSkillSerializer(skill, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, slug):
        skill = self._get_skill(slug)
        if skill is None:
            return Response(
                {"detail": "Skill not found."}, status=status.HTTP_404_NOT_FOUND
            )
        skill.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Global Tools
# ---------------------------------------------------------------------------


class GlobalToolEndpoint(BaseAPIView):
    """List and create global tools. Built-in tools are read-only via detail endpoint."""

    permission_classes = [InstanceAdminPermission]

    def get(self, request):
        qs = GlobalTool.objects.all().order_by("name")
        is_active = request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() in ("true", "1"))
        serializer = GlobalToolSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        # Admins may only create custom tools directly; builtin tools are
        # seeded via migration/admin and must not be re-created via API.
        impl_type = request.data.get("implementation_type", "custom")
        if impl_type == "builtin":
            return Response(
                {"detail": "Built-in tools must be seeded via migration, not the API."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = GlobalToolSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GlobalToolDetailEndpoint(BaseAPIView):
    """Retrieve, update, or delete a global tool by slug.
    Built-in tools are read-only — PATCH and DELETE return 403.
    """

    permission_classes = [InstanceAdminPermission]

    def _get_tool(self, slug):
        try:
            return GlobalTool.objects.get(slug=slug)
        except GlobalTool.DoesNotExist:
            return None

    def get(self, request, slug):
        tool = self._get_tool(slug)
        if tool is None:
            return Response(
                {"detail": "Tool not found."}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = GlobalToolSerializer(tool)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, slug):
        tool = self._get_tool(slug)
        if tool is None:
            return Response(
                {"detail": "Tool not found."}, status=status.HTTP_404_NOT_FOUND
            )
        if tool.implementation_type == "builtin":
            return Response(
                {"detail": "Built-in tools are read-only."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = GlobalToolSerializer(tool, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, slug):
        tool = self._get_tool(slug)
        if tool is None:
            return Response(
                {"detail": "Tool not found."}, status=status.HTTP_404_NOT_FOUND
            )
        if tool.implementation_type == "builtin":
            return Response(
                {"detail": "Built-in tools are read-only."},
                status=status.HTTP_403_FORBIDDEN,
            )
        tool.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Global MCP Connections
# ---------------------------------------------------------------------------


class GlobalMCPConnectionEndpoint(BaseAPIView):
    """List and create global MCP connections."""

    permission_classes = [InstanceAdminPermission]

    def get(self, request):
        connections = GlobalMCPConnection.objects.all().order_by("name")
        serializer = GlobalMCPConnectionSerializer(connections, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = GlobalMCPConnectionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GlobalMCPConnectionDetailEndpoint(BaseAPIView):
    """Retrieve, update, or delete a global MCP connection by slug."""

    permission_classes = [InstanceAdminPermission]

    def _get_connection(self, slug):
        try:
            return GlobalMCPConnection.objects.get(slug=slug)
        except GlobalMCPConnection.DoesNotExist:
            return None

    def get(self, request, slug):
        conn = self._get_connection(slug)
        if conn is None:
            return Response(
                {"detail": "MCP connection not found."}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = GlobalMCPConnectionSerializer(conn)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, slug):
        conn = self._get_connection(slug)
        if conn is None:
            return Response(
                {"detail": "MCP connection not found."}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = GlobalMCPConnectionSerializer(conn, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, slug):
        conn = self._get_connection(slug)
        if conn is None:
            return Response(
                {"detail": "MCP connection not found."}, status=status.HTTP_404_NOT_FOUND
            )
        conn.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
