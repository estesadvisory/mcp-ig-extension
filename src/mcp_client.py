"""Write IG metrics to the deployed MCP server over HTTPS."""

from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class MCPWriteError(RuntimeError):
    """Raised when an MCP write fails."""


def _mcp_base_url() -> str:
    url = os.environ.get("MCP_BASE_URL", "").strip()
    if not url:
        raise MCPWriteError("MCP_BASE_URL environment variable is required")
    return url.rstrip("/") + "/"


def _serialize_store_content(content: str) -> str:
    """
    Keep metrics content as a string through MCP JSON-RPC argument parsing.

    Streamable HTTP may coerce JSON-looking strings into objects before the store
    tool runs; double-encoding ensures the server still receives a string.
    """
    return json.dumps(content)


def _build_store_payload(
    logical_key: str,
    content: str,
    *,
    title: str,
    summary: str,
    content_type: str = "application/json",
    run_id: str,
) -> dict[str, Any]:
    """Payload aligned with grok-memory-mcp's canonical `store` tool."""
    return {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "tools/call",
        "params": {
            "name": "store",
            "arguments": {
                "logical_key": logical_key,
                "content": _serialize_store_content(content),
                "metadata": {
                    "title": title,
                    "summary": summary,
                    "tags": ["ig_monitor", "metrics", run_id],
                    "source": "ig-mcp-extension",
                },
                "storage_type": "s3",
                "content_type": content_type,
            },
        },
    }


def write_metric(
    logical_key: str,
    content: str,
    *,
    bearer_token: str,
    title: str,
    summary: str,
    run_id: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    """POST a canonical MCP `store` tool call to the public Function URL."""
    payload = _build_store_payload(
        logical_key,
        content,
        title=title,
        summary=summary,
        run_id=run_id,
    )

    if dry_run:
        logger.info("Dry run MCP write for key=%s payload=%s", logical_key, json.dumps(payload))
        return {"dry_run": True, "logical_key": logical_key, "payload": payload}

    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }

    with httpx.Client(timeout=30.0) as client:
        response = client.post(_mcp_base_url(), headers=headers, json=payload)

    if response.status_code >= 400:
        raise MCPWriteError(
            f"MCP write failed for {logical_key}: HTTP {response.status_code} {response.text[:500]}"
        )

    try:
        body: dict[str, Any] = response.json()
    except json.JSONDecodeError:
        body = {"raw": response.text[:1000]}

    logger.info("MCP write succeeded for key=%s status=%s", logical_key, response.status_code)
    return {"logical_key": logical_key, "status_code": response.status_code, "body": body}