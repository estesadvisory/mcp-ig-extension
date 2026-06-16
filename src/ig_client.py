"""Meta Graph API client for Instagram business/creator account metrics."""

from __future__ import annotations

import logging
import random
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_API_VERSION = "v21.0"
MAX_RETRIES = 5
INITIAL_BACKOFF_SECONDS = 1.0

# Graph API insight metrics vary by media type; filter to supported metrics per item.
METRICS_BY_MEDIA_TYPE: dict[str, list[str]] = {
    "FEED": ["impressions", "reach", "engagement", "likes", "comments", "shares", "saves"],
    "POST": ["impressions", "reach", "engagement", "likes", "comments", "shares", "saves"],
    "REEL": ["impressions", "reach", "likes", "comments", "shares", "saves", "video_views"],
    "VIDEO": ["impressions", "reach", "likes", "comments", "shares", "saves", "video_views"],
    "STORY": ["impressions", "reach", "replies", "exits", "taps_forward", "taps_back"],
    "CAROUSEL_ALBUM": ["impressions", "reach", "engagement", "likes", "comments", "shares", "saves"],
}


class IGClientError(RuntimeError):
    """Raised when the Instagram Graph API returns an error."""


class IGClient:
    def __init__(self, access_token: str, api_version: str = DEFAULT_API_VERSION) -> None:
        self.access_token = access_token
        self.base_url = f"https://graph.facebook.com/{api_version}"

    def _request_with_backoff(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        query = {"access_token": self.access_token}
        if params:
            query.update(params)

        url = f"{self.base_url}/{path.lstrip('/')}"
        backoff = INITIAL_BACKOFF_SECONDS

        with httpx.Client(timeout=30.0) as client:
            for attempt in range(1, MAX_RETRIES + 1):
                response = client.request(method, url, params=query)

                if response.status_code == 429 or response.status_code >= 500:
                    retry_after = _retry_after_seconds(response)
                    sleep_for = retry_after if retry_after is not None else backoff
                    sleep_for += random.uniform(0, 0.5)
                    logger.warning(
                        "Graph API %s %s -> %s; retry %s/%s in %.1fs",
                        method,
                        path,
                        response.status_code,
                        attempt,
                        MAX_RETRIES,
                        sleep_for,
                    )
                    if attempt == MAX_RETRIES:
                        raise IGClientError(
                            f"Graph API error {response.status_code} after retries: "
                            f"{response.text[:500]}"
                        )
                    time.sleep(sleep_for)
                    backoff = min(backoff * 2, 60.0)
                    continue

                if response.status_code >= 400:
                    raise IGClientError(
                        f"Graph API error {response.status_code}: {response.text[:500]}"
                    )

                data = response.json()
                if not isinstance(data, dict):
                    raise IGClientError("Graph API response was not a JSON object")
                return data

        raise IGClientError("Graph API request failed unexpectedly")

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._request_with_backoff("GET", path, params=params)

    def list_recent_media(
        self,
        ig_user_id: str,
        *,
        limit: int = 25,
        lookback_days: int = 7,
    ) -> list[dict[str, Any]]:
        """Fetch recent media for an IG business/creator account within the lookback window."""
        fields = "id,media_type,timestamp,permalink,caption"
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        collected: list[dict[str, Any]] = []
        next_url: str | None = None
        page_params: dict[str, Any] = {"fields": fields, "limit": str(min(limit, 50))}

        while len(collected) < limit:
            if next_url:
                # Pagination URLs are absolute and already include the access token.
                with httpx.Client(timeout=30.0) as client:
                    response = client.get(next_url)
                if response.status_code >= 400:
                    raise IGClientError(
                        f"Graph API pagination error {response.status_code}: {response.text[:500]}"
                    )
                data = response.json()
            else:
                data = self._get(f"{ig_user_id}/media", page_params)

            media = data.get("data", [])
            if not isinstance(media, list):
                break

            stop_paging = False
            for item in media:
                if not isinstance(item, dict):
                    continue
                timestamp = _parse_graph_timestamp(item.get("timestamp"))
                if timestamp and timestamp < cutoff:
                    stop_paging = True
                    continue
                collected.append(item)
                if len(collected) >= limit:
                    break

            if stop_paging or len(collected) >= limit:
                break

            paging = data.get("paging", {})
            next_url = paging.get("next") if isinstance(paging, dict) else None
            if not next_url:
                break

        return collected

    def get_media_insights(
        self,
        media_id: str,
        metrics: list[str],
        *,
        media_type: str = "POST",
    ) -> dict[str, Any]:
        """Fetch insights for a single media item, filtering to metrics valid for the media type."""
        supported = set(METRICS_BY_MEDIA_TYPE.get(media_type.upper(), metrics))
        requested = [metric for metric in metrics if metric in supported]
        if not requested:
            logger.info(
                "No supported insights metrics for media_id=%s media_type=%s",
                media_id,
                media_type,
            )
            return {}

        data = self._get(
            f"{media_id}/insights",
            {"metric": ",".join(requested)},
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


def _parse_graph_timestamp(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S%z")
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def _retry_after_seconds(response: httpx.Response) -> float | None:
    header = response.headers.get("Retry-After")
    if not header:
        return None
    try:
        return float(header)
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(header)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)
            delta = (retry_at - datetime.now(timezone.utc)).total_seconds()
            return max(delta, 0.0)
        except (TypeError, ValueError):
            return None