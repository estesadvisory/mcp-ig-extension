"""Pydantic models for accounts config and metric payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class GlobalConfig(BaseModel):
    lookback_days: int = 7
    max_media_per_run: int = 50


class AccountConfig(BaseModel):
    label: str
    ig_user_id: str
    username: str
    secret_name: str
    enabled: bool = True
    media_types: list[str] = Field(default_factory=lambda: ["POST", "REEL", "STORY"])
    metrics: list[str] = Field(default_factory=list)


class AccountsConfig(BaseModel):
    version: str = "1.0"
    schedule: str = "rate(6 hours)"
    accounts: list[AccountConfig] = Field(default_factory=list)
    global_: GlobalConfig = Field(default_factory=GlobalConfig, alias="global")

    model_config = {"populate_by_name": True}


class MediaMetrics(BaseModel):
    ig_user_id: str
    media_id: str
    media_type: str
    timestamp: str | None = None
    permalink: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    collected_at: datetime
    source: str = "ig-mcp-extension"
    run_id: str

    def to_json(self) -> str:
        return self.model_dump_json()