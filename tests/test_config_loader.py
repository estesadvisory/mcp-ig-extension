from pathlib import Path

from config_loader import load_accounts_config
from models import AccountsConfig


def test_load_accounts_config() -> None:
    config_path = Path(__file__).resolve().parent.parent / "config" / "accounts.json"
    config = load_accounts_config(config_path)
    assert isinstance(config, AccountsConfig)
    assert config.version == "1.0"
    assert len(config.accounts) == 1
    assert config.accounts[0].label == "me2dafuture"
    assert config.global_.lookback_days == 7