"""Meta Graph API client (stub for roadmap step 4)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"


class IGClientError(RuntimeError):
    """Raised when the Instagram Graph API returns an error."""


class IGClient:
    def __init__(self, access_token: str, api_version: str = "v21.0") -> None:
        self.access_token = access_token
        self.base_url = f"https://graph.facebook.com/{api_version}"

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        query = {"access_token": self.access_token}
        if params:
            query.update(params)
        with httpx.Client(timeout=30.0) as client:
            response = client.get(f"{self.base_url}/{path.lstrip('/')}", params=query)
        if response.status_code >= 400:
            raise IGClientError(f"Graph API error {response.status_code}: {response.text[:500]}")
        data = response.json()
        if not isinstance(data, dict):
            raise IGClientError("Graph API response was not a JSON object")
        return data

    def list_recent_media(self, ig_user_id: str, limit: int = 25) -> list[dict[str, Any]]:
        """Fetch recent media for an IG business/creator account."""
        fields = "id,media_type,timestamp,permalink,caption"
        data = self._get(
            f"{ig_user_id}/media",
            {"fields": fields, "limit": str(limit)},
        )
        media = data.get("data", [])
        if not isinstance(media, list):
            return []
        return [item for item in media if isinstance(item, dict)]

    def get_media_insights(self, media_id: str, metrics: list[str]) -> dict[str, Any]:
        """Fetch insights for a single media item."""
        if not metrics:
            return {}
        data = self._get(
            f"{media_id}/insights",
            {"metric": ",".join(metrics)},
        )
        insights: dict[str, Any] = {}
        for item in data.get("data", []):
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            values = item.get("values", [])
            if name and values and isinstance(values[0], dict):
                insights[str(name)] = values[0].get("value")
        return insights