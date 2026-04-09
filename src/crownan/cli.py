#!/usr/bin/env python3
"""Crownan CLI — command-line interface for Krónan supermarket.

Usage:
    crownan search <query>          Search for products
    crownan product <sku>           Get product details
    crownan cart                    View current cart
    crownan cart add <sku> [qty]    Add product to cart
    crownan cart clear              Clear the cart
    crownan categories              List categories
    crownan categories <slug>       Browse products in a category
    crownan orders                  View order history
    crownan stats                   View purchase statistics
    crownan me                      Show current user
"""

from __future__ import annotations

import argparse
import sys

from crownan.client import KronanClient
from crownan.exceptions import KronanAPIError, KronanConnectionError

# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _fmt_isk(amount: int) -> str:
    """Format ISK amount with thousands separator."""
    return f"{amount:,} kr".replace(",", ".")


def _truncate(text: str, width: int = 40) -> str:
    return text[: width - 1] + "…" if len(text) > width else text


def _print_table(headers: list[str], rows: list[list[str]], col_widths: list[int] | None = None):
    """Print a simple aligned table."""
    if not rows:
        print("  (empty)")
        return

    if col_widths is None:
        col_widths = [
            max(len(h), max((len(str(r[i])) for r in rows), default=0))
            for i, h in enumerate(headers)
        ]

    header_line = "  ".join(h.ljust(w) for h, w in zip(headers, col_widths))
    sep_line = "  ".join("─" * w for w in col_widths)
    print(f"  {header_line}")
    print(f"  {sep_line}")
    for row in rows:
        line = "  ".join(str(cell).ljust(w) for cell, w in zip(row, col_widths))
        print(f"  {line}")


def _print_product_table(products, show_sku=True):
    """Print a list of products as a table."""
    if not products:
        print("  No products found.")
        return

    headers = []
    if show_sku:
        headers.append("SKU")
    headers.extend(["Name", "Price", "Info"])

    rows = []
    for p in products:
        row = []
        if show_sku:
            row.append(p.sku)
        row.extend(
            [
                _truncate(p.name, 35),
                _fmt_isk(p.price),
                p.price_info or "",
            ]
        )
        rows.append(row)

    widths = []
    if show_sku:
        widths.append(12)
    widths.extend([35, 12, 25])

    _print_table(headers, rows, widths)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_me(client: KronanClient, args: argparse.Namespace):
    me = client.get_me()
    print(f"  Logged in as: {me.name} ({me.type})")


def cmd_search(client: KronanClient, args: argparse.Namespace):
    query = " ".join(args.query)
    result = client.search_products(query, page=args.page, with_detail=args.detail)
    pg = f"page {result.page}/{result.page_count}"
    print(f'\n  Search: "{query}" — {result.count} results ({pg})\n')

    _print_product_table(result.hits)

    if result.has_next_page:
        print(f"\n  → More results: crownan search {query} --page {result.page + 1}")
    print()


def cmd_product(client: KronanClient, args: argparse.Namespace):
    p = client.get_product(args.sku)
    print(f"\n  {p.name}")
    print(f"  {'─' * 40}")
    print(f"  SKU:         {p.sku}")
    print(f"  Price:       {_fmt_isk(p.price)}")
    if p.discounted_price and p.discounted_price != p.price:
        print(f"  Sale price:  {_fmt_isk(p.discounted_price)} ({p.discount_percent}% off)")
    if p.price_info:
        print(f"  Unit price:  {p.price_info}")
    if p.description:
        print(f"  Description: {p.description}")
    if p.country_of_origin:
        print(f"  Origin:      {p.country_of_origin}")
    if p.tags:
        print(f"  Tags:        {', '.join(t.name for t in p.tags)}")
    if p.temporary_shortage:
        print("  ⚠ Temporarily out of stock")
    print()


def cmd_cart(client: KronanClient, args: argparse.Namespace):
    checkout = client.get_checkout()
    print(f"\n  🛒 Cart ({len(checkout.lines)} items)\n")

    if checkout.lines:
        headers = ["Qty", "Name", "Unit", "Total"]
        rows = []
        for line in checkout.lines:
            name = line.product.name if line.product else "(product)"
            rows.append(
                [
                    str(line.quantity),
                    _truncate(name, 35),
                    _fmt_isk(line.price),
                    _fmt_isk(line.total),
                ]
            )
        _print_table(headers, rows, [5, 35, 12, 12])
    else:
        print("  Cart is empty.")

    print(f"\n  {'─' * 40}")
    print(f"  Subtotal:     {_fmt_isk(checkout.subtotal)}")
    if checkout.bagging_fee:
        print(f"  Bagging fee:  {_fmt_isk(checkout.bagging_fee)}")
    if checkout.shipping_fee:
        print(f"  Shipping:     {_fmt_isk(checkout.shipping_fee)}")
    elif checkout.subtotal < checkout.shipping_fee_cutoff:
        remaining = checkout.shipping_fee_cutoff - checkout.subtotal
        cutoff = _fmt_isk(checkout.shipping_fee_cutoff)
        left = _fmt_isk(remaining)
        print(f"  Shipping:     Free over {cutoff} ({left} to go)")
    else:
        print("  Shipping:     Free!")
    print(f"  Total:        {_fmt_isk(checkout.total)}")
    print()


def cmd_cart_add(client: KronanClient, args: argparse.Namespace):
    qty = args.quantity or 1
    lines = [{"sku": args.sku, "quantity": qty}]
    checkout = client.add_to_cart(lines, replace=False)

    # Find the line we just added
    added = None
    for line in checkout.lines:
        if line.product and line.product.sku == args.sku:
            added = line
            break

    if added and added.product:
        print(f"  Added {qty}x {added.product.name} ({_fmt_isk(added.product.price)} each)")
    else:
        print(f"  Added {qty}x {args.sku}")
    print(f"  Cart total: {_fmt_isk(checkout.total)} ({len(checkout.lines)} items)")


def cmd_cart_clear(client: KronanClient, args: argparse.Namespace):
    checkout = client.clear_cart()
    print(f"  Cart cleared. Total: {_fmt_isk(checkout.total)}")


def cmd_categories(client: KronanClient, args: argparse.Namespace):
    if args.slug:
        # Browse products in a category
        try:
            result = client.get_category_products(args.slug, page=args.page)
            pg = f"page {result.page}/{result.page_count}"
            print(f"\n  {result.name} — {result.count} products ({pg})\n")
            _print_product_table(result.products)
            if result.has_next_page:
                print(f"\n  → More: crownan categories {args.slug} --page {result.page + 1}")
            print()
        except KronanAPIError as e:
            if e.status_code == 400 and "not a leaf category" in str(e.detail).lower():
                # Show subcategories instead
                cats = client.get_categories()
                for cat in cats:
                    if cat.slug == args.slug:
                        print(f"\n  {cat.name} — subcategories:\n")
                        for child in cat.children:
                            print(f"    {child.slug:40s} {child.name}")
                            for leaf in child.children:
                                print(f"      {leaf.slug:38s} {leaf.name}")
                        print()
                        return
                    for child in cat.children:
                        if child.slug == args.slug:
                            print(f"\n  {child.name} — leaf categories:\n")
                            for leaf in child.children:
                                print(f"    {leaf.slug:40s} {leaf.name}")
                            print()
                            return
                raise
    else:
        cats = client.get_categories()
        print(f"\n  {len(cats)} categories:\n")
        for cat in cats:
            n_children = sum(len(c1.children) for c1 in cat.children)
            print(f"  {cat.slug:40s} {cat.name} ({n_children} subcategories)")
        print("\n  → Browse: crownan categories <slug>")
        print("  → Products: crownan categories <leaf-slug> (level 2 only)\n")


def cmd_orders(client: KronanClient, args: argparse.Namespace):
    result = client.get_orders(limit=args.limit)
    print(f"\n  Orders ({result.count} total):\n")

    if not result.results:
        print("  No orders found.")
        print()
        return

    headers = ["Date", "Status", "Type", "Total"]
    rows = []
    for order in result.results:
        rows.append(
            [
                order.delivery_date or order.created[:10],
                order.status,
                order.type or "",
                _fmt_isk(order.total),
            ]
        )
    _print_table(headers, rows, [12, 20, 12, 12])
    print()


def cmd_stats(client: KronanClient, args: argparse.Namespace):
    result = client.get_purchase_stats(limit=args.limit)
    print(f"\n  Purchase statistics ({result.count} products tracked):\n")

    if not result.results:
        print("  No purchase data yet.")
        print()
        return

    headers = ["Product", "Times", "Total Qty", "Avg Interval", "Last Purchase"]
    rows = []
    for stat in result.results:
        name = stat.product.name if stat.product else "(unknown)"
        avg_days = stat.average_purchase_interval_days
        interval = f"{avg_days:.0f} days" if avg_days else "—"
        rows.append(
            [
                _truncate(name, 30),
                str(stat.purchase_count),
                str(stat.quantity_purchased),
                interval,
                stat.last_purchase_date or "—",
            ]
        )
    _print_table(headers, rows, [30, 7, 10, 14, 12])
    print()


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crownan",
        description="Crownan — CLI for Krónan supermarket",
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # me
    sub.add_parser("me", help="Show current user")

    # search
    p_search = sub.add_parser("search", help="Search for products")
    p_search.add_argument("query", nargs="+", help="Search query")
    p_search.add_argument("--page", type=int, default=1, help="Page number")
    p_search.add_argument("--detail", action="store_true", help="Include discount/tag info")

    # product
    p_product = sub.add_parser("product", help="Get product details")
    p_product.add_argument("sku", help="Product SKU")

    # cart
    p_cart = sub.add_parser("cart", help="Cart operations")
    cart_sub = p_cart.add_subparsers(dest="cart_action")
    p_cart_add = cart_sub.add_parser("add", help="Add product to cart")
    p_cart_add.add_argument("sku", help="Product SKU")
    p_cart_add.add_argument("quantity", nargs="?", type=int, help="Quantity (default: 1)")
    cart_sub.add_parser("clear", help="Clear the cart")

    # categories
    p_cats = sub.add_parser("categories", help="Browse categories")
    p_cats.add_argument("slug", nargs="?", help="Category slug to browse")
    p_cats.add_argument("--page", type=int, default=1, help="Page number")

    # orders
    p_orders = sub.add_parser("orders", help="View order history")
    p_orders.add_argument("--limit", type=int, default=10, help="Number of orders")

    # stats
    p_stats = sub.add_parser("stats", help="View purchase statistics")
    p_stats.add_argument("--limit", type=int, default=20, help="Number of products")

    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    from dotenv import load_dotenv

    load_dotenv(".env.local")
    load_dotenv()

    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        client = KronanClient()
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Set KRONAN_API_KEY in .env.local or as an env var.", file=sys.stderr)
        sys.exit(1)

    try:
        if args.command == "me":
            cmd_me(client, args)
        elif args.command == "search":
            cmd_search(client, args)
        elif args.command == "product":
            cmd_product(client, args)
        elif args.command == "cart":
            if args.cart_action == "add":
                cmd_cart_add(client, args)
            elif args.cart_action == "clear":
                cmd_cart_clear(client, args)
            else:
                cmd_cart(client, args)
        elif args.command == "categories":
            cmd_categories(client, args)
        elif args.command == "orders":
            cmd_orders(client, args)
        elif args.command == "stats":
            cmd_stats(client, args)
    except (KronanAPIError, KronanConnectionError) as e:
        print(f"\n  Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    main()
