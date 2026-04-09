"""Unit tests for model deserialization (no live API)."""

from __future__ import annotations

from crownan.models import (
    Category,
    CategoryLevel1,
    CategoryLevel2,
    Checkout,
    CheckoutLine,
    Me,
    Product,
    ProductDetail,
    ProductTag,
    SearchResult,
)


class TestProduct:
    def test_from_dict_camelcase(self, mock_product_data: dict):
        product = Product.from_dict(mock_product_data)

        assert product.sku == "02500188"
        assert product.name == "MS nýmjólk"
        assert product.price == 230
        assert product.discounted_price == 230
        assert product.discount_percent == 0
        assert product.on_sale is False
        assert product.price_info == "1 ltr. - 230 kr. / ltr"
        assert product.charged_by_weight is False
        assert product.price_per_kilo is None
        assert product.base_comparison_unit == "LTR"
        assert product.temporary_shortage is False
        assert product.thumbnail == (
            "https://media.kronan.is/products/92327-thumbnail-255x255-70.jpg"
        )


class TestProductDetail:
    def test_from_dict_with_tags(self, mock_product_data: dict):
        data = {
            **mock_product_data,
            "description": "Nýmjólk frá MS",
            "image": "https://media.kronan.is/products/92327.jpg",
            "qtyPerBaseCompUnit": 1.0,
            "countryOfOrigin": "IS",
            "tags": [
                {"slug": "icelandic", "name": "Íslenskt"},
                {"slug": "dairy", "name": "Mjólkurvörur"},
            ],
        }

        detail = ProductDetail.from_dict(data)

        assert detail.sku == "02500188"
        assert detail.description == "Nýmjólk frá MS"
        assert detail.country_of_origin == "IS"
        assert len(detail.tags) == 2
        assert isinstance(detail.tags[0], ProductTag)
        assert detail.tags[0].slug == "icelandic"
        assert detail.tags[1].name == "Mjólkurvörur"


class TestCheckout:
    def test_from_dict_empty_lines(self, mock_checkout_data: dict):
        checkout = Checkout.from_dict(mock_checkout_data)

        assert checkout.token == "abc-123"
        assert checkout.total == 199
        assert checkout.subtotal == 0
        assert checkout.bagging_fee == 199
        assert checkout.service_fee == 0
        assert checkout.shipping_fee == 0
        assert checkout.shipping_fee_cutoff == 19900
        assert checkout.lines == []

    def test_from_dict_with_nested_products(self, mock_product_data: dict):
        data = {
            "token": "cart-456",
            "lines": [
                {
                    "id": 1,
                    "quantity": 2,
                    "total": 460,
                    "price": 230,
                    "substitution": False,
                    "product": mock_product_data,
                },
            ],
            "total": 659,
            "subtotal": 460,
            "baggingFee": 199,
            "serviceFee": 0,
            "shippingFee": 0,
            "shippingFeeCutoff": 19900,
        }

        checkout = Checkout.from_dict(data)

        assert checkout.token == "cart-456"
        assert len(checkout.lines) == 1
        assert isinstance(checkout.lines[0], CheckoutLine)
        assert checkout.lines[0].quantity == 2
        assert checkout.lines[0].product is not None
        assert checkout.lines[0].product.sku == "02500188"
        assert checkout.lines[0].product.name == "MS nýmjólk"


class TestSearchResult:
    def test_from_dict(self, mock_search_data: dict):
        result = SearchResult.from_dict(mock_search_data)

        assert result.count == 1
        assert result.page == 1
        assert result.page_count == 1
        assert result.has_next_page is False
        assert len(result.hits) == 1
        assert result.hits[0].sku == "02500188"
        assert result.hits[0].name == "MS nýmjólk"
        assert result.hits[0].detail is None


class TestCategory:
    def test_from_dict_with_nested_children(self):
        data = {
            "slug": "01-avextir-og-graenmeti",
            "name": "Ávextir og grænmeti",
            "backgroundImage": "https://media.kronan.is/cat/bg.jpg",
            "icon": "https://media.kronan.is/cat/icon.svg",
            "children": [
                {
                    "slug": "01-01-avextir",
                    "name": "Ávextir",
                    "children": [
                        {
                            "slug": "01-01-01-bananar-og-perur",
                            "name": "Bananar og perur",
                        },
                        {
                            "slug": "01-01-02-epli",
                            "name": "Epli",
                        },
                    ],
                },
            ],
        }

        category = Category.from_dict(data)

        assert category.slug == "01-avextir-og-graenmeti"
        assert category.name == "Ávextir og grænmeti"
        assert category.background_image == "https://media.kronan.is/cat/bg.jpg"
        assert category.icon == "https://media.kronan.is/cat/icon.svg"
        assert len(category.children) == 1

        level1 = category.children[0]
        assert isinstance(level1, CategoryLevel1)
        assert level1.slug == "01-01-avextir"
        assert len(level1.children) == 2

        level2 = level1.children[0]
        assert isinstance(level2, CategoryLevel2)
        assert level2.slug == "01-01-01-bananar-og-perur"
        assert level2.name == "Bananar og perur"


class TestMe:
    def test_from_dict(self):
        data = {"type": "user", "name": "Jón Jónsson"}

        me = Me.from_dict(data)

        assert me.type == "user"
        assert me.name == "Jón Jónsson"
