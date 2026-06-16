"""Load and validate the accounts definition file."""

from __future__ import annotations

import json
import os
from pathlib import Path

from models import AccountsConfig

DEFAULT_CONFIG_PATH = Path("/var/task/config/accounts.json")


def resolve_config_path() -> Path:
    override = os.environ.get("CONFIG_PATH")
    if override:
        return Path(override)
    repo_relative = Path(__file__).resolve().parent.parent / "config" / "accounts.json"
    if repo_relative.exists():
        return repo_relative
    return DEFAULT_CONFIG_PATH


def load_accounts_config(path: Path | None = None) -> AccountsConfig:
    config_path = path or resolve_config_path()
    with config_path.open(encoding="utf-8") as handle:
        raw = json.load(handle)
    return AccountsConfig.model_validate(raw)