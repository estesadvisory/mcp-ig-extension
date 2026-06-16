"""
AWS Lambda entrypoint for the IG MCP extension.

v0.1 flow:
1. Load accounts.json
2. Fetch MCP bearer token + per-account IG tokens from Secrets Manager
3. For each enabled account, collect metrics (stub/dummy in early builds)
4. Write dot-notation keys to the deployed MCP over HTTPS
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from config_loader import load_accounts_config
from ig_client import IGClient
from mcp_client import write_metric
from models import AccountConfig, MediaMetrics
from secrets import SecretLookupError, get_bearer_token, get_ig_access_token

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _run_id(event: dict[str, Any]) -> str:
    request_context = event.get("requestContext")
    if isinstance(request_context, dict):
        request_id = request_context.get("requestId")
        if isinstance(request_id, str) and request_id:
            return request_id
    event_id = event.get("id")
    if isinstance(event_id, str) and event_id:
        return event_id
    return f"run-{uuid.uuid4()}"


def _media_logical_key(account: AccountConfig, media_id: str, media_type: str) -> str:
    media_type_upper = media_type.upper()
    if media_type_upper == "REEL":
        return f"ig_monitor.accounts.{account.ig_user_id}.reels.{media_id}.insights"
    if media_type_upper == "STORY":
        return f"ig_monitor.accounts.{account.ig_user_id}.stories.{media_id}.insights"
    return f"ig_monitor.media.{media_id}.insights"


def _process_account(
    account: AccountConfig,
    *,
    run_id: str,
    mcp_token: str,
    dry_run: bool,
    dummy_mode: bool,
    lookback_days: int,
    max_media_per_run: int,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "label": account.label,
        "ig_user_id": account.ig_user_id,
        "writes": [],
        "errors": [],
    }

    try:
        ig_token = get_ig_access_token(account.secret_name)
    except SecretLookupError as exc:
        result["errors"].append(str(exc))
        return result

    if dummy_mode:
        payload = MediaMetrics(
            ig_user_id=account.ig_user_id,
            media_id="dummy-media-0001",
            media_type="REEL",
            timestamp=datetime.now(timezone.utc).isoformat(),
            permalink=f"https://www.instagram.com/{account.username}/",
            metrics={"impressions": 0, "reach": 0, "engagement": 0},
            collected_at=datetime.now(timezone.utc),
            run_id=run_id,
        )
        logical_key = _media_logical_key(account, payload.media_id, payload.media_type)
        write_result = write_metric(
            logical_key,
            payload.to_json(),
            bearer_token=mcp_token,
            title=f"IG metrics {account.username} {payload.media_id}",
            summary=f"Dummy metrics write for {account.label}",
            run_id=run_id,
            dry_run=dry_run,
        )
        result["writes"].append(write_result)
        return result

    client = IGClient(ig_token)
    max_media = int(os.environ.get("MAX_MEDIA_PER_RUN", str(max_media_per_run)))
    media_items = client.list_recent_media(
        account.ig_user_id,
        limit=max_media,
        lookback_days=lookback_days,
    )

    for item in media_items:
        media_id = str(item.get("id", ""))
        media_type = str(item.get("media_type", "POST"))
        if not media_id:
            continue
        if account.media_types and media_type.upper() not in {m.upper() for m in account.media_types}:
            continue

        try:
            metrics = client.get_media_insights(
                media_id,
                account.metrics,
                media_type=media_type,
            )
            payload = MediaMetrics(
                ig_user_id=account.ig_user_id,
                media_id=media_id,
                media_type=media_type,
                timestamp=item.get("timestamp"),
                permalink=item.get("permalink"),
                metrics=metrics,
                collected_at=datetime.now(timezone.utc),
                run_id=run_id,
            )
            logical_key = _media_logical_key(account, media_id, media_type)
            write_result = write_metric(
                logical_key,
                payload.to_json(),
                bearer_token=mcp_token,
                title=f"IG metrics {account.username} {media_id}",
                summary=f"{media_type} insights for {account.label}",
                run_id=run_id,
                dry_run=dry_run,
            )
            result["writes"].append(write_result)
        except Exception as exc:  # noqa: BLE001 - per-media isolation
            logger.exception("Failed media_id=%s account=%s", media_id, account.label)
            result["errors"].append(f"{media_id}: {exc}")

    return result


def handler(event: dict[str, Any] | None, context: Any) -> dict[str, Any]:
    event = event or {}
    run_id = _run_id(event)
    dry_run = os.environ.get("DRY_RUN", "").lower() in {"1", "true", "yes"}
    dummy_mode = os.environ.get("DUMMY_MODE", "true").lower() in {"1", "true", "yes"}

    logger.info("IG extension run_id=%s dry_run=%s dummy_mode=%s", run_id, dry_run, dummy_mode)

    try:
        config = load_accounts_config()
        mcp_secret_name = os.environ["MCP_AUTH_SECRET_NAME"]
        mcp_token = get_bearer_token(mcp_secret_name)
    except (KeyError, SecretLookupError, ValueError) as exc:
        logger.exception("Initialization failed")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(exc), "run_id": run_id}),
        }

    account_results: list[dict[str, Any]] = []
    for account in config.accounts:
        if not account.enabled:
            continue
        account_results.append(
            _process_account(
                account,
                run_id=run_id,
                mcp_token=mcp_token,
                dry_run=dry_run,
                dummy_mode=dummy_mode,
                lookback_days=config.global_.lookback_days,
                max_media_per_run=config.global_.max_media_per_run,
            )
        )

    body = {
        "status": "ok",
        "run_id": run_id,
        "accounts_processed": len(account_results),
        "dry_run": dry_run,
        "dummy_mode": dummy_mode,
        "results": account_results,
    }
    logger.info("Run complete: %s", json.dumps(body))
    return {"statusCode": 200, "body": json.dumps(body)}