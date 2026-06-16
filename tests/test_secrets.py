import json
from unittest.mock import MagicMock, patch

import pytest

from secrets import SecretLookupError, get_bearer_token, get_ig_access_token


def test_get_bearer_token_from_json() -> None:
    mock_client = MagicMock()
    mock_client.get_secret_value.return_value = {
        "SecretString": json.dumps({"token": "mcp-bearer-123"}),
    }
    with patch("secrets._secrets_client", return_value=mock_client):
        assert get_bearer_token("mcp/ig-extension/bearer-token") == "mcp-bearer-123"


def test_get_ig_access_token_from_json() -> None:
    mock_client = MagicMock()
    mock_client.get_secret_value.return_value = {
        "SecretString": json.dumps({"access_token": "ig-token-456"}),
    }
    with patch("secrets._secrets_client", return_value=mock_client):
        assert get_ig_access_token("ig/me2dafuture/access-token") == "ig-token-456"


def test_get_bearer_token_requires_token_field() -> None:
    mock_client = MagicMock()
    mock_client.get_secret_value.return_value = {
        "SecretString": json.dumps({"access_token": "wrong-field"}),
    }
    with patch("secrets._secrets_client", return_value=mock_client):
        with pytest.raises(SecretLookupError):
            get_bearer_token("mcp/ig-extension/bearer-token")