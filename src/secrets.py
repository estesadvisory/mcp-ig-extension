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


def get_bearer_token(secret_name: str, field: str = "token") -> str:
    """Return a bearer token from a plain string or JSON secret."""
    raw = get_secret_string(secret_name).strip()
    if raw.startswith("{"):
        payload = json.loads(raw)
        if isinstance(payload, dict) and field in payload:
            return str(payload[field])
        if isinstance(payload, dict) and "access_token" in payload:
            return str(payload["access_token"])
    return raw