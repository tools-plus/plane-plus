# InfraWatch — LiteLLM Admin API client
# SPDX-License-Identifier: AGPL-3.0-only
#
# Wraps LiteLLM's /key/* and /health endpoints with a simple synchronous
# requests.Session. All callers should treat a None return from
# get_litellm_client() as "LiteLLM not configured; skip silently."

import requests


class LiteLLMClient:
    """Synchronous client for LiteLLM's Admin (proxy) API."""

    def __init__(self, endpoint: str, master_key: str):
        self.endpoint = endpoint.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {master_key}",
                "Content-Type": "application/json",
            }
        )

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def health_check(self) -> bool:
        """Return True if LiteLLM is reachable and reports healthy."""
        try:
            resp = self.session.get(
                f"{self.endpoint}/health/liveliness", timeout=5
            )
            return resp.status_code == 200
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Virtual key lifecycle
    # ------------------------------------------------------------------

    def create_key(
        self,
        key_alias: str,
        budget_usd: float | None = None,
        metadata: dict | None = None,
    ) -> str:
        """Create a virtual key and return the generated key string."""
        payload: dict = {"key_alias": key_alias}
        if budget_usd is not None:
            payload["max_budget"] = budget_usd
        if metadata:
            payload["metadata"] = metadata
        resp = self.session.post(
            f"{self.endpoint}/key/generate", json=payload, timeout=10
        )
        resp.raise_for_status()
        return resp.json()["key"]

    def delete_key(self, key: str) -> None:
        """Delete a virtual key by its key string."""
        resp = self.session.post(
            f"{self.endpoint}/key/delete", json={"keys": [key]}, timeout=10
        )
        resp.raise_for_status()

    def update_key(self, key: str, budget_usd: float | None = None) -> None:
        """Update a virtual key's budget ceiling."""
        payload: dict = {"key": key}
        if budget_usd is not None:
            payload["max_budget"] = budget_usd
        resp = self.session.post(
            f"{self.endpoint}/key/update", json=payload, timeout=10
        )
        resp.raise_for_status()


def get_litellm_client() -> "LiteLLMClient | None":
    """Return a configured LiteLLMClient, or None if LiteLLM is not set up.

    Imports are deferred to avoid circular-import issues at module load time.
    """
    from plane.ai.models import LiteLLMConfig

    config = LiteLLMConfig.objects.filter(is_active=True).first()
    if not config or not config.master_key:
        return None
    return LiteLLMClient(config.endpoint, config.master_key)
