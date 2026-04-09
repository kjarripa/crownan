"""Kronan supermarket API client.

Usage::

    from crownan.client import KronanClient

    client = KronanClient()          # reads KRONAN_API_KEY from env
    me = client.get_me()
    results = client.search_products("mjolk")
"""

from __future__ import annotations

import os
from typing import Any, Optional

import httpx

from crownan.exceptions import KronanAPIError, KronanConnectionError
from crownan.models import (
    ArchivedShoppingNoteLine,
    Category,
    CategoryProductList,
    Checkout,
    Me,
    Order,
    OrderSummary,
    PaginatedResponse,
    ProductDetail,
    ProductList,
    PurchaseStat,
    SearchResult,
    ShoppingNote,
)

# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

_DEFAULT_BASE_URL = "https://api.kronan.is/api/v1/"
_DEFAULT_TIMEOUT = 30.0


class KronanClient:
    """Synchronous Python client for the Kronan supermarket REST API.

    Parameters
    ----------
    api_key : str, optional
        The AccessToken for authentication. If not provided, reads from
        the ``KRONAN_API_KEY`` environment variable.
    base_url : str, optional
        Override the API base URL (useful for testing).
    timeout : float, optional
        HTTP request timeout in seconds (default 30).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._api_key = api_key or os.environ.get("KRONAN_API_KEY", "")
        if not self._api_key:
            raise ValueError("No API key provided. Pass api_key= or set KRONAN_API_KEY env var.")
        self._base_url = base_url.rstrip("/") + "/"
        self._client = httpx.Client(
            base_url=self._base_url,
            headers={
                "Authorization": f"AccessToken {self._api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=timeout,
        )

    # ------------------------------------------------------------------
    # Low-level HTTP helpers
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict] = None,
        json: Optional[dict] = None,
    ) -> httpx.Response:
        """Make an HTTP request and raise on non-2xx status."""
        try:
            resp = self._client.request(method, path, params=params, json=json)
        except httpx.RequestError as e:
            raise KronanConnectionError(f"Connection error: {e}", original=e) from e
        if not resp.is_success:
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            raise KronanAPIError(resp.status_code, detail, resp)
        return resp

    def _get(self, path: str, *, params: Optional[dict] = None) -> Any:
        resp = self._request("GET", path, params=params)
        try:
            return resp.json()
        except (ValueError, Exception):
            raise KronanAPIError(resp.status_code, "Unexpected response format", resp)

    def _post(self, path: str, *, json: Optional[dict] = None) -> Any:
        resp = self._request("POST", path, json=json)
        try:
            return resp.json()
        except (ValueError, Exception):
            raise KronanAPIError(resp.status_code, "Unexpected response format", resp)

    def _patch(self, path: str, *, json: Optional[dict] = None) -> Any:
        resp = self._request("PATCH", path, json=json)
        try:
            return resp.json()
        except (ValueError, Exception):
            raise KronanAPIError(resp.status_code, "Unexpected response format", resp)

    def _delete(self, path: str, *, params: Optional[dict] = None) -> httpx.Response:
        return self._request("DELETE", path, params=params)

    # ==================================================================
    # Me
    # ==================================================================

    def get_me(self) -> Me:
        """Get the identity behind the current access token."""
        data = self._get("me/")
        return Me.from_dict(data)

    # ==================================================================
    # Products
    # ==================================================================

    def search_products(
        self,
        query: str,
        *,
        page: int = 1,
        page_size: int = 48,
        sort_by: Optional[str] = None,
        with_detail: bool = False,
    ) -> SearchResult:
        """Search for products.

        Parameters
        ----------
        query : str
            Search query (max 64 characters).
        page : int
            Page number (1-indexed).
        page_size : int
            Results per page (default 48).
        sort_by : str, optional
            Sort field, e.g. ``"price"`` or ``"name"``.
        with_detail : bool
            If True, include discount and tag info (slower).
        """
        if not query or len(query) > 64:
            raise ValueError("query must be 1-64 characters")
        if page < 1:
            raise ValueError("page must be >= 1")
        body: dict[str, Any] = {
            "query": query,
            "page": page,
            "pageSize": page_size,
            "withDetail": with_detail,
        }
        if sort_by is not None:
            body["sortBy"] = sort_by
        data = self._post("products/search/", json=body)
        return SearchResult.from_dict(data)

    def get_product(self, sku: str) -> ProductDetail:
        """Get full product details by SKU."""
        if not sku:
            raise ValueError("sku must not be empty")
        data = self._get(f"products/{sku}/")
        return ProductDetail.from_dict(data)

    # ==================================================================
    # Categories
    # ==================================================================

    def get_categories(self) -> list[Category]:
        """Get the full 3-level category tree."""
        data = self._get("categories/")
        return [Category.from_dict(c) for c in data]

    def get_category_products(self, slug: str, *, page: int = 1) -> CategoryProductList:
        """Get products in a leaf category.

        Only works on level-2 (leaf) category slugs like
        ``01-01-01-bananar-og-perur``.
        """
        if not slug:
            raise ValueError("slug must not be empty")
        if page < 1:
            raise ValueError("page must be >= 1")
        data = self._get(f"categories/{slug}/products/", params={"page": page})
        return CategoryProductList.from_dict(data)

    # ==================================================================
    # Checkout (Cart)
    # ==================================================================

    def get_checkout(self) -> Checkout:
        """Get the active checkout (shopping cart).

        A checkout is auto-created if none exists.
        """
        data = self._get("checkout/")
        return Checkout.from_dict(data)

    def add_to_cart(
        self,
        lines: list[dict[str, Any]],
        *,
        replace: bool = False,
    ) -> Checkout:
        """Add product lines to the cart.

        Parameters
        ----------
        lines : list[dict]
            Each dict should have ``"sku"`` (str), ``"quantity"`` (int),
            and optionally ``"substitution"`` (bool).
        replace : bool
            If True, replaces ALL existing lines. Defaults to False
            (the API defaults to True, so we override for safety).
        """
        if not lines:
            raise ValueError("lines must not be empty")
        for line in lines:
            if "quantity" in line and not (1 <= line["quantity"] <= 500):
                raise ValueError("quantity must be 1-500")
        body = {"lines": lines, "replace": replace}
        data = self._post("checkout/lines/", json=body)
        return Checkout.from_dict(data)

    def clear_cart(self) -> Checkout:
        """Remove all lines from the cart."""
        body = {"lines": [], "replace": True}
        data = self._post("checkout/lines/", json=body)
        return Checkout.from_dict(data)

    # ==================================================================
    # Orders
    # ==================================================================

    def get_orders(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        order_type: Optional[str] = None,
    ) -> PaginatedResponse:
        """Get paginated order history.

        Parameters
        ----------
        limit : int
            Results per page.
        offset : int
            Number of results to skip.
        order_type : str, optional
            Filter: ``"delivery"``, ``"pickup"``, ``"scan_n_go"``, ``"digital"``.

        Returns
        -------
        PaginatedResponse
            With ``results`` as a list of ``OrderSummary`` objects.
        """
        if limit < 1 or limit > 100:
            raise ValueError("limit must be 1-100")
        if offset < 0:
            raise ValueError("offset must be >= 0")
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if order_type is not None:
            params["type"] = order_type
        data = self._get("orders/", params=params)
        return PaginatedResponse(
            count=data["count"],
            next=data.get("next"),
            previous=data.get("previous"),
            results=[OrderSummary.from_dict(r) for r in data.get("results", [])],
        )

    def get_order(self, token: str) -> Order:
        """Get full order details including lines."""
        if not token:
            raise ValueError("token must not be empty")
        data = self._get(f"orders/{token}/")
        return Order.from_dict(data)

    def delete_order_lines(self, token: str, line_ids: list[int]) -> Order:
        """Remove lines from an order.

        Cannot delete service lines, the last remaining line,
        or lines where picking has started.
        """
        if not token:
            raise ValueError("token must not be empty")
        data = self._post(f"orders/{token}/delete-lines/", json={"lineIds": line_ids})
        return Order.from_dict(data)

    def lower_order_quantity(self, token: str, line_ids: list[int], quantity: int) -> Order:
        """Lower the quantity of order lines.

        Quantity can only be lowered (not raised). Set to 0 to remove.
        """
        if not token:
            raise ValueError("token must not be empty")
        data = self._post(
            f"orders/{token}/lower-quantity-lines/",
            json={"lineIds": line_ids, "quantity": quantity},
        )
        return Order.from_dict(data)

    def toggle_order_substitution(self, token: str, line_ids: list[int]) -> Order:
        """Toggle substitution preference on order lines."""
        if not token:
            raise ValueError("token must not be empty")
        data = self._post(
            f"orders/{token}/lines-toggle-substitution/",
            json={"lineIds": line_ids},
        )
        return Order.from_dict(data)

    # ==================================================================
    # Product Lists
    # ==================================================================

    def get_product_lists(self, *, limit: int = 20, offset: int = 0) -> PaginatedResponse:
        """Get paginated list of saved product lists.

        Returns
        -------
        PaginatedResponse
            With ``results`` as a list of ``ProductList`` objects.
        """
        if limit < 1 or limit > 100:
            raise ValueError("limit must be 1-100")
        if offset < 0:
            raise ValueError("offset must be >= 0")
        params = {"limit": limit, "offset": offset}
        data = self._get("product-lists/", params=params)
        return PaginatedResponse(
            count=data["count"],
            next=data.get("next"),
            previous=data.get("previous"),
            results=[ProductList.from_dict(r) for r in data.get("results", [])],
        )

    def create_product_list(self, name: str, *, description: str = "") -> ProductList:
        """Create a new product list."""
        if not name:
            raise ValueError("name must not be empty")
        data = self._post("product-lists/", json={"name": name, "description": description})
        return ProductList.from_dict(data)

    def get_product_list(self, token: str) -> ProductList:
        """Get a product list with all items."""
        if not token:
            raise ValueError("token must not be empty")
        data = self._get(f"product-lists/{token}/")
        return ProductList.from_dict(data)

    def update_product_list(
        self,
        token: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> ProductList:
        """Update a product list's name and/or description."""
        if not token:
            raise ValueError("token must not be empty")
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        data = self._patch(f"product-lists/{token}/", json=body)
        return ProductList.from_dict(data)

    def delete_product_list(self, token: str) -> None:
        """Delete a product list and all its items."""
        if not token:
            raise ValueError("token must not be empty")
        self._delete(f"product-lists/{token}/")

    def update_product_list_item(self, token: str, sku: str, quantity: int) -> ProductList:
        """Add a product to a list or update its quantity.

        Set quantity to 0 to remove the item.
        """
        if not token:
            raise ValueError("token must not be empty")
        if not sku:
            raise ValueError("sku must not be empty")
        if quantity < 0 or quantity > 500:
            raise ValueError("quantity must be 0-500")
        data = self._post(
            f"product-lists/{token}/update-item/",
            json={"sku": sku, "quantity": quantity},
        )
        return ProductList.from_dict(data)

    def delete_all_product_list_items(self, token: str) -> None:
        """Remove all items from a product list (keeps the list)."""
        if not token:
            raise ValueError("token must not be empty")
        self._delete(f"product-lists/{token}/delete-all-items/")

    def sort_product_list_items(self, token: str) -> ProductList:
        """Sort product list items by store department layout."""
        if not token:
            raise ValueError("token must not be empty")
        data = self._post(f"product-lists/{token}/sort-items/")
        return ProductList.from_dict(data)

    # ==================================================================
    # Purchase Stats
    # ==================================================================

    def get_purchase_stats(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        include_ignored: bool = False,
    ) -> PaginatedResponse:
        """Get purchase history analytics.

        Returns
        -------
        PaginatedResponse
            With ``results`` as a list of ``PurchaseStat`` objects.
        """
        if limit < 1 or limit > 100:
            raise ValueError("limit must be 1-100")
        if offset < 0:
            raise ValueError("offset must be >= 0")
        params: dict[str, Any] = {
            "limit": limit,
            "offset": offset,
            "include_ignored": str(include_ignored).lower(),
        }
        data = self._get("product-purchase-stats/", params=params)
        return PaginatedResponse(
            count=data["count"],
            next=data.get("next"),
            previous=data.get("previous"),
            results=[PurchaseStat.from_dict(r) for r in data.get("results", [])],
        )

    def set_purchase_stat_ignored(self, id: int, *, is_ignored: bool) -> PurchaseStat:
        """Hide or unhide a product from purchase history."""
        if id < 1:
            raise ValueError("id must be positive")
        data = self._patch(
            f"product-purchase-stats/{id}/set-ignored/",
            json={"isIgnored": is_ignored},
        )
        return PurchaseStat.from_dict(data)

    # ==================================================================
    # Shopping Notes
    # ==================================================================

    def get_shopping_note(self, token: str) -> ShoppingNote:
        """Get a shopping note. Auto-creates one if it doesn't exist."""
        if not token:
            raise ValueError("token must not be empty")
        data = self._get(f"shopping-notes/{token}/")
        return ShoppingNote.from_dict(data)

    def add_shopping_note_line(
        self,
        token: str,
        *,
        text: Optional[str] = None,
        sku: Optional[str] = None,
        quantity: int = 1,
    ) -> ShoppingNote:
        """Add a line to a shopping note.

        Provide either ``text`` (freeform) or ``sku`` (product link).
        """
        if not token:
            raise ValueError("token must not be empty")
        body: dict[str, Any] = {"quantity": quantity}
        if text is not None:
            body["text"] = text
        if sku is not None:
            body["sku"] = sku
        data = self._post(f"shopping-notes/{token}/add-line/", json=body)
        return ShoppingNote.from_dict(data)

    def change_shopping_note_line(
        self,
        token: str,
        line_token: str,
        *,
        text: Optional[str] = None,
        quantity: Optional[int] = None,
    ) -> ShoppingNote:
        """Update text or quantity of a shopping note line."""
        if not token:
            raise ValueError("token must not be empty")
        body: dict[str, Any] = {"token": line_token}
        if text is not None:
            body["text"] = text
        if quantity is not None:
            body["quantity"] = quantity
        data = self._patch(f"shopping-notes/{token}/change-line/", json=body)
        return ShoppingNote.from_dict(data)

    def toggle_shopping_note_line(self, token: str, line_token: str) -> ShoppingNote:
        """Toggle completion status of a shopping note line."""
        if not token:
            raise ValueError("token must not be empty")
        data = self._patch(
            f"shopping-notes/{token}/toggle-complete-on-line/",
            json={"token": line_token},
        )
        return ShoppingNote.from_dict(data)

    def delete_shopping_note_line(self, token: str, line_token: str) -> None:
        """Remove a specific line from a shopping note."""
        if not token:
            raise ValueError("token must not be empty")
        self._delete(f"shopping-notes/{token}/delete-line/", params={"token": line_token})

    def get_archived_shopping_note_lines(self, token: str) -> list[ArchivedShoppingNoteLine]:
        """Get previously completed/archived shopping note lines."""
        if not token:
            raise ValueError("token must not be empty")
        data = self._get(f"shopping-notes/{token}/lines-archived/")
        return [ArchivedShoppingNoteLine.from_dict(ln) for ln in data]

    def delete_shopping_note(self, token: str) -> None:
        """Clear all lines from a shopping note (note itself is preserved)."""
        if not token:
            raise ValueError("token must not be empty")
        self._delete(f"shopping-notes/{token}/delete-shopping-note/")

    def sort_shopping_note_by_store(self, token: str) -> ShoppingNote:
        """Reorder shopping note lines to match store aisle layout."""
        if not token:
            raise ValueError("token must not be empty")
        data = self._post(f"shopping-notes/{token}/store-product-order/")
        return ShoppingNote.from_dict(data)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> KronanClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"<KronanClient base_url={self._base_url!r}>"
