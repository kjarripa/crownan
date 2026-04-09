"""Test client initialization (mock httpx, no live API)."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from crownan.client import KronanClient


class TestClientInit:
    def test_raises_without_api_key(self):
        """KronanClient() raises ValueError when no API key is available."""
        with patch.dict(os.environ, {}, clear=True):
            # Ensure KRONAN_API_KEY is not in the environment
            os.environ.pop("KRONAN_API_KEY", None)
            with pytest.raises(ValueError, match="No API key provided"):
                KronanClient()

    def test_sets_correct_headers(self):
        """KronanClient(api_key='test') sets the expected HTTP headers."""
        client = KronanClient(api_key="test")
        headers = client._client.headers

        assert "authorization" in headers
        assert headers["content-type"] == "application/json"
        assert headers["accept"] == "application/json"
        client.close()

    def test_authorization_header_format(self):
        """Authorization header must be 'AccessToken <key>', not Bearer or Token."""
        client = KronanClient(api_key="my-secret-key")
        auth = client._client.headers["authorization"]

        assert auth == "AccessToken my-secret-key"
        assert not auth.startswith("Bearer ")
        assert not auth.startswith("Token ")
        client.close()

    def test_base_url_trailing_slash(self):
        """Base URL is normalized to always end with a single trailing slash."""
        client_no_slash = KronanClient(api_key="test", base_url="https://example.com/api")
        client_with_slash = KronanClient(api_key="test", base_url="https://example.com/api/")

        assert client_no_slash._base_url == "https://example.com/api/"
        assert client_with_slash._base_url == "https://example.com/api/"

        client_no_slash.close()
        client_with_slash.close()
