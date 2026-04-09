"""Shared test fixtures for the Crownan test suite."""

from __future__ import annotations

import pytest


@pytest.fixture()
def mock_product_data() -> dict:
    """A dict mimicking a Kronan product response (camelCase keys)."""
    return {
        "sku": "02500188",
        "name": "MS nýmjólk",
        "price": 230,
        "thumbnail": "https://media.kronan.is/products/92327-thumbnail-255x255-70.jpg",
        "discountedPrice": 230,
        "discountPercent": 0,
        "onSale": False,
        "priceInfo": "1 ltr. - 230 kr. / ltr",
        "chargedByWeight": False,
        "pricePerKilo": None,
        "baseComparisonUnit": "LTR",
        "temporaryShortage": False,
    }


@pytest.fixture()
def mock_checkout_data() -> dict:
    """A dict mimicking a Kronan checkout response."""
    return {
        "token": "abc-123",
        "lines": [],
        "total": 199,
        "subtotal": 0,
        "baggingFee": 199,
        "serviceFee": 0,
        "shippingFee": 0,
        "shippingFeeCutoff": 19900,
    }


@pytest.fixture()
def mock_search_data(mock_product_data: dict) -> dict:
    """A dict mimicking a Kronan search response."""
    hit = {**mock_product_data, "detail": None}
    return {
        "count": 1,
        "page": 1,
        "pageCount": 1,
        "hasNextPage": False,
        "hits": [hit],
    }
