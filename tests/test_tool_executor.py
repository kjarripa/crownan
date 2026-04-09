"""Test tool dispatch and serialization."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import httpx
import pytest

from crownan.agent.executor import ToolExecutor
from crownan.exceptions import KronanAPIError
from crownan.models import Checkout, SearchResult


@pytest.fixture()
def mock_client() -> MagicMock:
    """A mock KronanClient."""
    return MagicMock()


@pytest.fixture()
def executor(mock_client: MagicMock) -> ToolExecutor:
    """A ToolExecutor wired to the mock client."""
    return ToolExecutor(mock_client)


class TestToolDispatch:
    def test_search_products_calls_client(
        self, executor: ToolExecutor, mock_client: MagicMock, mock_search_data: dict
    ):
        mock_client.search_products.return_value = SearchResult.from_dict(mock_search_data)

        result = executor.execute("search_products", {"query": "mjólk"})
        parsed = json.loads(result)

        mock_client.search_products.assert_called_once_with(
            query="mjólk", page=1, with_detail=False
        )
        assert parsed["count"] == 1
        assert len(parsed["hits"]) == 1

    def test_get_cart_calls_client(
        self, executor: ToolExecutor, mock_client: MagicMock, mock_checkout_data: dict
    ):
        mock_client.get_checkout.return_value = Checkout.from_dict(mock_checkout_data)

        result = executor.execute("get_cart", {})
        parsed = json.loads(result)

        mock_client.get_checkout.assert_called_once()
        assert parsed["token"] == "abc-123"
        assert parsed["total"] == 199

    def test_unknown_tool_returns_error(self, executor: ToolExecutor):
        result = executor.execute("unknown_tool", {})
        parsed = json.loads(result)

        assert parsed["error"] is True
        assert "Unknown tool" in parsed["detail"]

    def test_api_error_returns_json_error(self, executor: ToolExecutor, mock_client: MagicMock):
        mock_response = MagicMock()
        mock_client.search_products.side_effect = KronanAPIError(
            status_code=401,
            detail="Invalid token",
            response=mock_response,
        )

        result = executor.execute("search_products", {"query": "test"})
        parsed = json.loads(result)

        assert parsed["error"] is True
        assert parsed["status_code"] == 401
        # Executor now sanitizes error messages — raw detail should NOT leak
        assert "Authentication failed" in parsed["detail"]

    def test_add_to_cart_always_uses_replace_false(
        self, mock_client: MagicMock, mock_checkout_data: dict
    ):
        """_add_to_cart ignores replace=True from model input."""
        mock_client.add_to_cart.return_value = Checkout.from_dict(mock_checkout_data)
        executor = ToolExecutor(mock_client)
        # Pass replace=True in input — executor should ignore it
        executor.execute("add_to_cart", {"items": [{"sku": "123", "quantity": 1}], "replace": True})
        mock_client.add_to_cart.assert_called_once()
        _, kwargs = mock_client.add_to_cart.call_args
        assert kwargs.get("replace") is False

    def test_api_error_returns_sanitized_message(self, mock_client: MagicMock):
        """API errors should NOT leak raw detail."""
        mock_resp = MagicMock(spec=httpx.Response)
        mock_client.search_products.side_effect = KronanAPIError(
            500, "internal server details", mock_resp
        )
        executor = ToolExecutor(mock_client)
        result = executor.execute("search_products", {"query": "test"})
        parsed = json.loads(result)
        assert parsed["error"] is True
        assert "internal server details" not in parsed["detail"]
        assert "API error" in parsed["detail"] or "error occurred" in parsed["detail"].lower()

    def test_generic_exception_returns_safe_message(self, mock_client: MagicMock):
        """Generic exceptions should NOT leak stack traces."""
        mock_client.get_checkout.side_effect = RuntimeError("secret internal info")
        executor = ToolExecutor(mock_client)
        result = executor.execute("get_cart", {})
        parsed = json.loads(result)
        assert parsed["error"] is True
        assert "secret internal info" not in parsed["detail"]
