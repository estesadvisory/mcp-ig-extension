"""AWS Secrets Manager helpers."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any

import boto3  # type: ignore[import-untyped]
from botocore.exceptions import ClientError  # type: ignore[import-untyped]


class SecretLookupError(RuntimeError):
    """Raised when a secret cannot be fetched or parsed."""


@lru_cache(maxsize=1)
def _secrets_client() -> Any:
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"
    return boto3.client("secretsmanager", region_name=region)


def get_secret_string(secret_name: str) -> str:
    client = _secrets_client()
    try:
        response = client.get_secret_value(SecretId=secret_name)
    except ClientError as exc:
        raise SecretLookupError(f"Failed to read secret '{secret_name}': {exc}") from exc

    if "SecretString" in response and response["SecretString"]:
        return str(response["SecretString"])

    if "SecretBinary" in response and response["SecretBinary"]:
        return str(response["SecretBinary"].decode("utf-8"))

    raise SecretLookupError(f"Secret '{secret_name}' has no string or binary payload")


def get_secret_json(secret_name: str) -> dict[str, Any]:
    raw = get_secret_string(secret_name)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SecretLookupError(f"Secret '{secret_name}' is not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise SecretLookupError(f"Secret '{secret_name}' JSON root must be an object")
    return parsed


def _parse_secret_field(secret_name: str, field: str, *, fallback_fields: tuple[str, ...] = ()) -> str:
    """Extract a field from JSON secret ``{"field": "..."}`` or return raw string secret."""
    raw = get_secret_string(secret_name).strip()
    if not raw.startswith("{"):
        return raw

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SecretLookupError(f"Secret '{secret_name}' is not valid JSON") from exc

    if not isinstance(payload, dict):
        raise SecretLookupError(f"Secret '{secret_name}' JSON root must be an object")

    if field in payload and str(payload[field]).strip():
        return str(payload[field]).strip()

    for fallback in fallback_fields:
        if fallback in payload and str(payload[fallback]).strip():
            return str(payload[fallback]).strip()

    raise SecretLookupError(
        f"Secret '{secret_name}' JSON must include '{field}'"
        + (f" or one of {fallback_fields}" if fallback_fields else "")
    )


def get_bearer_token(secret_name: str, field: str = "token") -> str:
    """Return MCP Bearer token from JSON ``{"token": "..."}`` (preferred) or plain string."""
    return _parse_secret_field(secret_name, field)


def get_ig_access_token(secret_name: str) -> str:
    """Return Meta Graph API token from JSON ``{"access_token": "..."}`` or plain string."""
    return _parse_secret_field(secret_name, "access_token", fallback_fields=("token",))