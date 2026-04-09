"""Kronan API response models.

Typed dataclasses for all API response types. Fields use snake_case
(converted from the API's camelCase) for Pythonic access.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_snake(name: str) -> str:
    """Convert camelCase to snake_case."""
    import re

    s1 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def _from_dict(cls, data: dict):
    """Instantiate a dataclass from a camelCase dict, ignoring unknown keys."""
    if data is None:
        return None
    snake = {_to_snake(k): v for k, v in data.items()}
    hints = {f.name: f for f in cls.__dataclass_fields__.values()}
    kwargs = {}
    for name, f in hints.items():
        if name in snake:
            kwargs[name] = snake[name]
    return cls(**kwargs)


# ---------------------------------------------------------------------------
# Me
# ---------------------------------------------------------------------------


@dataclass
class Me:
    type: str
    name: str

    @classmethod
    def from_dict(cls, data: dict) -> Me:
        return _from_dict(cls, data)


# ---------------------------------------------------------------------------
# Product-related
# ---------------------------------------------------------------------------


@dataclass
class ProductTag:
    slug: str
    name: str

    @classmethod
    def from_dict(cls, data: dict) -> ProductTag:
        return _from_dict(cls, data)


@dataclass
class Product:
    """Product as it appears in lists, cart lines, etc."""

    sku: str
    name: str
    price: int
    thumbnail: Optional[str] = None
    discounted_price: Optional[int] = None
    discount_percent: Optional[int] = None
    on_sale: Optional[bool] = None
    price_info: Optional[str] = None
    charged_by_weight: bool = False
    price_per_kilo: Optional[int] = None
    base_comparison_unit: Optional[str] = None
    temporary_shortage: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> Product:
        return _from_dict(cls, data)


@dataclass
class ProductDetail(Product):
    """Full product detail (extends Product with extra fields)."""

    description: str = ""
    image: Optional[str] = None
    qty_per_base_comp_unit: Optional[float] = None
    country_of_origin: Optional[str] = None
    tags: list[ProductTag] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> ProductDetail:
        snake = {_to_snake(k): v for k, v in data.items()}
        tags_raw = snake.pop("tags", [])
        hints = {f.name for f in cls.__dataclass_fields__.values()}
        kwargs = {k: v for k, v in snake.items() if k in hints}
        kwargs["tags"] = [ProductTag.from_dict(t) for t in (tags_raw or [])]
        return cls(**kwargs)


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


@dataclass
class SearchDetail:
    """Extra detail returned when withDetail=true on search."""

    discounted_price: Optional[int] = None
    discount_percent: Optional[int] = None
    on_sale: Optional[bool] = None
    tags: list[ProductTag] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> SearchDetail:
        if data is None:
            return None
        snake = {_to_snake(k): v for k, v in data.items()}
        tags_raw = snake.pop("tags", [])
        hints = {f.name for f in cls.__dataclass_fields__.values()}
        kwargs = {k: v for k, v in snake.items() if k in hints}
        kwargs["tags"] = [ProductTag.from_dict(t) for t in (tags_raw or [])]
        return cls(**kwargs)


@dataclass
class SearchHit:
    sku: str
    name: str
    price: int
    thumbnail: Optional[str] = None
    temporary_shortage: bool = False
    price_info: Optional[str] = None
    charged_by_weight: bool = False
    price_per_kilo: Optional[int] = None
    base_comparison_unit: Optional[str] = None
    detail: Optional[SearchDetail] = None

    @classmethod
    def from_dict(cls, data: dict) -> SearchHit:
        snake = {_to_snake(k): v for k, v in data.items()}
        detail_raw = snake.pop("detail", None)
        hints = {f.name for f in cls.__dataclass_fields__.values()}
        kwargs = {k: v for k, v in snake.items() if k in hints}
        kwargs["detail"] = SearchDetail.from_dict(detail_raw) if detail_raw else None
        return cls(**kwargs)


@dataclass
class SearchResult:
    count: int
    page: int
    page_count: int
    has_next_page: bool
    hits: list[SearchHit] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> SearchResult:
        snake = {_to_snake(k): v for k, v in data.items()}
        hits_raw = snake.pop("hits", [])
        hints = {f.name for f in cls.__dataclass_fields__.values()}
        kwargs = {k: v for k, v in snake.items() if k in hints}
        kwargs["hits"] = [SearchHit.from_dict(h) for h in (hits_raw or [])]
        return cls(**kwargs)


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------


@dataclass
class CategoryLevel2:
    slug: str
    name: str

    @classmethod
    def from_dict(cls, data: dict) -> CategoryLevel2:
        return _from_dict(cls, data)


@dataclass
class CategoryLevel1:
    slug: str
    name: str
    children: list[CategoryLevel2] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> CategoryLevel1:
        snake = {_to_snake(k): v for k, v in data.items()}
        children_raw = snake.pop("children", [])
        hints = {f.name for f in cls.__dataclass_fields__.values()}
        kwargs = {k: v for k, v in snake.items() if k in hints}
        kwargs["children"] = [CategoryLevel2.from_dict(c) for c in (children_raw or [])]
        return cls(**kwargs)


@dataclass
class Category:
    slug: str
    name: str
    background_image: Optional[str] = None
    icon: Optional[str] = None
    children: list[CategoryLevel1] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> Category:
        snake = {_to_snake(k): v for k, v in data.items()}
        children_raw = snake.pop("children", [])
        hints = {f.name for f in cls.__dataclass_fields__.values()}
        kwargs = {k: v for k, v in snake.items() if k in hints}
        kwargs["children"] = [CategoryLevel1.from_dict(c) for c in (children_raw or [])]
        return cls(**kwargs)


@dataclass
class CategoryProductList:
    name: str
    count: int
    page: int
    page_count: int
    has_next_page: bool
    products: list[Product] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> CategoryProductList:
        snake = {_to_snake(k): v for k, v in data.items()}
        products_raw = snake.pop("products", [])
        hints = {f.name for f in cls.__dataclass_fields__.values()}
        kwargs = {k: v for k, v in snake.items() if k in hints}
        kwargs["products"] = [Product.from_dict(p) for p in (products_raw or [])]
        return cls(**kwargs)


# ---------------------------------------------------------------------------
# Checkout (Cart)
# ---------------------------------------------------------------------------


@dataclass
class CheckoutLine:
    id: int
    quantity: int
    total: int
    price: int
    substitution: bool = False
    product: Optional[Product] = None

    @classmethod
    def from_dict(cls, data: dict) -> CheckoutLine:
        snake = {_to_snake(k): v for k, v in data.items()}
        product_raw = snake.pop("product", None)
        hints = {f.name for f in cls.__dataclass_fields__.values()}
        kwargs = {k: v for k, v in snake.items() if k in hints}
        kwargs["product"] = Product.from_dict(product_raw) if product_raw else None
        return cls(**kwargs)


@dataclass
class Checkout:
    token: str
    total: int
    subtotal: int
    bagging_fee: int
    service_fee: int
    shipping_fee: int
    shipping_fee_cutoff: int
    lines: list[CheckoutLine] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> Checkout:
        snake = {_to_snake(k): v for k, v in data.items()}
        lines_raw = snake.pop("lines", [])
        hints = {f.name for f in cls.__dataclass_fields__.values()}
        kwargs = {k: v for k, v in snake.items() if k in hints}
        kwargs["lines"] = [CheckoutLine.from_dict(ln) for ln in (lines_raw or [])]
        return cls(**kwargs)


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------


@dataclass
class OrderLine:
    id: int
    product_name: str
    sku: str
    quantity: int
    quantity_ordered: int
    unit_price: int
    total: int
    substitution: bool = False
    substitution_for_line_id: Optional[int] = None
    is_mutable: bool = False
    is_last_chance: bool = False
    thumbnail: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> OrderLine:
        return _from_dict(cls, data)


@dataclass
class Order:
    token: str
    created: str  # ISO-8601
    status: str
    total: int
    discount: int
    type: Optional[str] = None
    delivery_date: Optional[str] = None
    allow_alter_order_lines: bool = False
    lines: list[OrderLine] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> Order:
        snake = {_to_snake(k): v for k, v in data.items()}
        lines_raw = snake.pop("lines", [])
        hints = {f.name for f in cls.__dataclass_fields__.values()}
        kwargs = {k: v for k, v in snake.items() if k in hints}
        kwargs["lines"] = [OrderLine.from_dict(ln) for ln in (lines_raw or [])]
        return cls(**kwargs)


@dataclass
class OrderSummary:
    """Order as returned in the paginated list (no lines)."""

    token: str
    created: str
    status: str
    total: int
    discount: int
    type: Optional[str] = None
    delivery_date: Optional[str] = None
    allow_alter_order_lines: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> OrderSummary:
        return _from_dict(cls, data)


# ---------------------------------------------------------------------------
# Product Lists
# ---------------------------------------------------------------------------


@dataclass
class ProductListItem:
    id: int
    quantity: int
    product: Optional[Product] = None

    @classmethod
    def from_dict(cls, data: dict) -> ProductListItem:
        snake = {_to_snake(k): v for k, v in data.items()}
        product_raw = snake.pop("product", None)
        hints = {f.name for f in cls.__dataclass_fields__.values()}
        kwargs = {k: v for k, v in snake.items() if k in hints}
        kwargs["product"] = Product.from_dict(product_raw) if product_raw else None
        return cls(**kwargs)


@dataclass
class ProductList:
    id: int
    name: str
    token: str
    description: str = ""
    has_products: Optional[bool] = None
    items: list[ProductListItem] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> ProductList:
        snake = {_to_snake(k): v for k, v in data.items()}
        items_raw = snake.pop("items", [])
        hints = {f.name for f in cls.__dataclass_fields__.values()}
        kwargs = {k: v for k, v in snake.items() if k in hints}
        kwargs["items"] = [ProductListItem.from_dict(i) for i in (items_raw or [])]
        return cls(**kwargs)


# ---------------------------------------------------------------------------
# Purchase Stats
# ---------------------------------------------------------------------------


@dataclass
class PurchaseStat:
    id: int
    purchase_count: int
    quantity_purchased: int
    last_purchase_quantity: int
    is_ignored: bool = False
    average_purchase_quantity: Optional[float] = None
    average_purchase_interval_days: Optional[float] = None
    first_purchase_date: Optional[str] = None
    last_purchase_date: Optional[str] = None
    product: Optional[Product] = None

    @classmethod
    def from_dict(cls, data: dict) -> PurchaseStat:
        snake = {_to_snake(k): v for k, v in data.items()}
        product_raw = snake.pop("product", None)
        hints = {f.name for f in cls.__dataclass_fields__.values()}
        kwargs = {k: v for k, v in snake.items() if k in hints}
        kwargs["product"] = Product.from_dict(product_raw) if product_raw else None
        return cls(**kwargs)


# ---------------------------------------------------------------------------
# Shopping Notes
# ---------------------------------------------------------------------------


@dataclass
class ShoppingNoteProduct:
    name: str
    description: str = ""
    sku: Optional[str] = None
    thumbnail: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> ShoppingNoteProduct:
        return _from_dict(cls, data)


@dataclass
class ShoppingNoteLine:
    token: str
    placement: int
    is_completed: bool = False
    text: Optional[str] = None
    quantity: Optional[int] = None
    product: Optional[ShoppingNoteProduct] = None

    @classmethod
    def from_dict(cls, data: dict) -> ShoppingNoteLine:
        snake = {_to_snake(k): v for k, v in data.items()}
        product_raw = snake.pop("product", None)
        hints = {f.name for f in cls.__dataclass_fields__.values()}
        kwargs = {k: v for k, v in snake.items() if k in hints}
        kwargs["product"] = ShoppingNoteProduct.from_dict(product_raw) if product_raw else None
        return cls(**kwargs)


@dataclass
class ShoppingNote:
    token: str
    name: str
    lines: list[ShoppingNoteLine] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> ShoppingNote:
        snake = {_to_snake(k): v for k, v in data.items()}
        lines_raw = snake.pop("lines", [])
        hints = {f.name for f in cls.__dataclass_fields__.values()}
        kwargs = {k: v for k, v in snake.items() if k in hints}
        kwargs["lines"] = [ShoppingNoteLine.from_dict(ln) for ln in (lines_raw or [])]
        return cls(**kwargs)


@dataclass
class ArchivedShoppingNoteLine:
    token: str
    text: str
    completed_count: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> ArchivedShoppingNoteLine:
        return _from_dict(cls, data)


# ---------------------------------------------------------------------------
# Pagination wrappers (DRF style)
# ---------------------------------------------------------------------------


@dataclass
class PaginatedResponse:
    """Generic DRF offset/limit pagination envelope."""

    count: int
    next: Optional[str] = None
    previous: Optional[str] = None
    results: list = field(default_factory=list)
