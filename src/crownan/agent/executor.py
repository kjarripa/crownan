"""Execute custom tool calls using the Krónan SDK.

Maps Managed Agent custom tool names to KronanClient methods.
Returns JSON-serialized results for sending back as tool results.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from typing import Any

from crownan.client import KronanClient
from crownan.exceptions import KronanAPIError

logger = logging.getLogger(__name__)


def _serialize(obj: Any) -> Any:
    """Convert dataclass instances to dicts for JSON serialization."""
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _serialize(v) for k, v in asdict(obj).items()}
    if isinstance(obj, list):
        return [_serialize(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    return obj


def _truncate_results(products: list[dict], max_items: int = 10) -> list[dict]:
    """Truncate product lists to avoid bloating the agent context."""
    if len(products) <= max_items:
        return products
    return products[:max_items]


class ToolExecutor:
    """Executes Krónan API tool calls and returns JSON results."""

    def __init__(self, kronan_client: KronanClient):
        self.client = kronan_client

    def execute(self, tool_name: str, tool_input: dict) -> str:
        """Execute a tool and return a JSON string result."""
        try:
            result = self._dispatch(tool_name, tool_input)
            return json.dumps(result, ensure_ascii=False)
        except KronanAPIError as e:
            logger.error("API error in tool %s: HTTP %s", tool_name, e.status_code, exc_info=True)
            safe_messages = {
                401: "Authentication failed. Check your API key.",
                403: "Permission denied.",
                404: "The requested resource was not found.",
                429: "Rate limit exceeded. Please wait a moment.",
            }
            default_msg = "An API error occurred. Please try again."
            detail = safe_messages.get(e.status_code, default_msg)
            err = {"error": True, "status_code": e.status_code, "detail": detail}
            return json.dumps(err, ensure_ascii=False)
        except Exception:
            logger.error("Unexpected error in tool %s", tool_name, exc_info=True)
            err = {"error": True, "detail": "An unexpected error occurred."}
            return json.dumps(err, ensure_ascii=False)

    def _dispatch(self, tool_name: str, tool_input: dict) -> dict:
        """Route tool call to the correct method."""
        match tool_name:
            case "search_products":
                return self._search_products(tool_input)
            case "get_product":
                return self._get_product(tool_input)
            case "get_cart":
                return self._get_cart()
            case "add_to_cart":
                return self._add_to_cart(tool_input)
            case "clear_cart":
                return self._clear_cart()
            case "get_categories":
                return self._get_categories()
            case "get_category_products":
                return self._get_category_products(tool_input)
            case "get_orders":
                return self._get_orders(tool_input)
            case "get_order_detail":
                return self._get_order_detail(tool_input)
            case "get_purchase_stats":
                return self._get_purchase_stats(tool_input)
            case _:
                return {"error": True, "detail": f"Unknown tool: {tool_name}"}

    def _search_products(self, inp: dict) -> dict:
        result = self.client.search_products(
            query=inp["query"],
            page=inp.get("page", 1),
            with_detail=inp.get("with_detail", False),
        )
        serialized = _serialize(result)
        # Truncate hits to keep context manageable
        if "hits" in serialized:
            serialized["hits"] = _truncate_results(serialized["hits"])
            serialized["showing"] = len(serialized["hits"])
        return serialized

    def _get_product(self, inp: dict) -> dict:
        product = self.client.get_product(inp["sku"])
        return _serialize(product)

    def _get_cart(self) -> dict:
        checkout = self.client.get_checkout()
        return _serialize(checkout)

    def _add_to_cart(self, inp: dict) -> dict:
        lines = []
        for item in inp["items"]:
            lines.append(
                {
                    "sku": item["sku"],
                    "quantity": item.get("quantity", 1),
                }
            )
        # Safety: always append to cart, never replace
        checkout = self.client.add_to_cart(lines, replace=False)
        return _serialize(checkout)

    def _clear_cart(self) -> dict:
        checkout = self.client.clear_cart()
        return _serialize(checkout)

    def _get_categories(self) -> dict:
        categories = self.client.get_categories()
        # Return a simplified view to avoid context bloat
        result = []
        for cat in categories:
            cat_data = {"slug": cat.slug, "name": cat.name, "subcategories": []}
            for child in cat.children:
                child_data = {
                    "slug": child.slug,
                    "name": child.name,
                    "leaves": [{"slug": lf.slug, "name": lf.name} for lf in child.children],
                }
                cat_data["subcategories"].append(child_data)
            result.append(cat_data)
        return {"categories": result, "count": len(result)}

    def _get_category_products(self, inp: dict) -> dict:
        result = self.client.get_category_products(
            slug=inp["slug"],
            page=inp.get("page", 1),
        )
        serialized = _serialize(result)
        if "products" in serialized:
            serialized["products"] = _truncate_results(serialized["products"])
        return serialized

    def _get_orders(self, inp: dict) -> dict:
        result = self.client.get_orders(limit=inp.get("limit", 10))
        return _serialize(result)

    def _get_order_detail(self, inp: dict) -> dict:
        order = self.client.get_order(inp["token"])
        return _serialize(order)

    def _get_purchase_stats(self, inp: dict) -> dict:
        result = self.client.get_purchase_stats(limit=inp.get("limit", 20))
        return _serialize(result)
