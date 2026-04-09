"""Test hardened client methods — transport errors, JSON guards, input validation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from crownan.client import KronanClient
from crownan.exceptions import KronanAPIError, KronanConnectionError


class TestTransportErrors:
    def test_request_catches_connection_error(self):
        """_request catches httpx.RequestError and raises KronanConnectionError."""
        client = KronanClient(api_key="test")
        with patch.object(client._client, "request", side_effect=httpx.ConnectError("DNS failed")):
            with pytest.raises(KronanConnectionError, match="Connection error"):
                client._request("GET", "test/")

    def test_request_catches_timeout_error(self):
        """_request catches httpx.TimeoutException and raises KronanConnectionError."""
        client = KronanClient(api_key="test")
        err = httpx.TimeoutException("timed out")
        with patch.object(client._client, "request", side_effect=err):
            with pytest.raises(KronanConnectionError):
                client._request("GET", "test/")


class TestJsonGuard:
    def test_get_catches_malformed_json(self):
        """_get raises KronanAPIError on malformed 2xx JSON."""
        client = KronanClient(api_key="test")
        mock_resp = MagicMock()
        mock_resp.is_success = True
        mock_resp.status_code = 200
        mock_resp.json.side_effect = ValueError("bad json")
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(KronanAPIError, match="Unexpected response"):
                client._get("test/")


class TestInputValidation:
    def test_search_rejects_empty_query(self):
        client = KronanClient(api_key="test")
        with pytest.raises(ValueError, match="query"):
            client.search_products("")

    def test_search_rejects_long_query(self):
        client = KronanClient(api_key="test")
        with pytest.raises(ValueError, match="query"):
            client.search_products("x" * 65)

    def test_search_rejects_zero_page(self):
        client = KronanClient(api_key="test")
        with pytest.raises(ValueError, match="page"):
            client.search_products("milk", page=0)

    def test_get_product_rejects_empty_sku(self):
        client = KronanClient(api_key="test")
        with pytest.raises(ValueError, match="sku"):
            client.get_product("")

    def test_add_to_cart_rejects_empty_lines(self):
        client = KronanClient(api_key="test")
        with pytest.raises(ValueError, match="lines"):
            client.add_to_cart([])

    def test_add_to_cart_rejects_invalid_quantity(self):
        client = KronanClient(api_key="test")
        with pytest.raises(ValueError, match="quantity"):
            client.add_to_cart([{"sku": "123", "quantity": 501}])

    def test_get_orders_rejects_zero_limit(self):
        client = KronanClient(api_key="test")
        with pytest.raises(ValueError, match="limit"):
            client.get_orders(limit=0)

    def test_get_orders_rejects_negative_offset(self):
        client = KronanClient(api_key="test")
        with pytest.raises(ValueError, match="offset"):
            client.get_orders(offset=-1)
