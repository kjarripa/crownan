# Crownan

Open-source AI-powered tools for the Krónan supermarket API. The name is a meme on "openclaw".

## What is this?

Krónan is Iceland's second-largest supermarket chain (~28% market share). They recently released a public REST API (beta) for their "snjallverslun" (online shop). Crownan builds open-source tools on top of it.

## Stack

- **Backend / SDK / CLI:** Python
- **UI (future):** TypeScript
- **API:** Krónan REST API at `https://api.kronan.is/api/v1/`

## Krónan API Quick Reference

- **Auth header:** `Authorization: AccessToken <token>` (NOT Token or Bearer)
- **Rate limit:** 200 requests per 200 seconds
- **Prices:** integers in ISK (no decimals)
- **JSON style:** camelCase fields, ISO-8601 UTC timestamps
- **Product search is POST** not GET: `POST /api/v1/products/search/`
- **Checkout lines `replace` defaults to `true`** — always pass `replace: false` to add items without clearing the cart
- **Category products only work on leaf categories** (level 2 slugs like `01-01-01-bananar-og-perur`)
- **Two pagination formats:** DRF offset/limit (orders, lists, stats) and page-based (search, category products)

Full API docs are in `ai_docs/`.

## Project Workflow

This is a greenfield project. We iterate fast:

1. **Experiment** in `experiments/` — quick scripts, prototypes, throwaway code
2. **Validate** that the approach works and feels right
3. **Promote** to root-level production code once validated

Never skip step 1 for new features. The `experiments/` folder is the sandbox.

## Directory Structure

```
crownan/
├── src/crownan/            # Production package (pip installable)
│   ├── client.py           # SDK — 30 typed methods for Krónan API
│   ├── models.py           # Dataclasses for all API response types
│   ├── cli.py              # CLI entry point (crownan command)
│   ├── benchmark.py        # Benchmark suite (crownan-benchmark)
│   ├── agent/              # Managed Agent integration
│   │   ├── tools.py        # Tool definitions + system prompt
│   │   ├── executor.py     # Maps tool calls → SDK
│   │   ├── session.py      # Agent turn loop (streaming + tool results)
│   │   └── setup.py        # Agent creation (crownan-agent-setup)
│   └── slackbot/           # Slack bot
│       └── app.py          # Bolt + Socket Mode, per-user sessions
├── tests/                  # Unit tests (pytest)
├── docs/                   # Setup guides (agent, slackbot)
├── ai_docs/                # API schemas, exploration results, context
├── experiments/            # Sandbox for prototyping new features
└── .github/                # CI, issue/PR templates
```

## Environment

Required env vars in `.env.local`:

- `KRONAN_API_KEY` — Krónan AccessToken for API calls
- `ANTHROPIC_API_KEY` — Anthropic API key for Managed Agents
- `SLACK_BOT_TOKEN` — (optional) Slack Bot User OAuth Token for the Slack bot
- `SLACK_APP_TOKEN` — (optional) Slack App-Level Token for Socket Mode

## Agent Architecture

Crownan uses Claude Managed Agents (beta) with custom tools:

1. User sends message (Slack DM, CLI, etc.)
2. Managed Agent (Sonnet 4.6) interprets the Icelandic text
3. Agent decides which Krónan API tools to call
4. Our code executes the tool via the SDK and returns results
5. Agent formulates an Icelandic response

Custom tools: `search_products`, `get_product`, `get_cart`, `add_to_cart`, `clear_cart`, `get_categories`, `get_category_products`, `get_orders`, `get_order_detail`, `get_purchase_stats`

**Managed Agents beta header:** `anthropic-beta: managed-agents-2026-04-01`

## Key API Endpoints

| Endpoint | Method | What it does |
|---|---|---|
| `/me/` | GET | User identity |
| `/categories/` | GET | Full 3-level category tree |
| `/categories/{slug}/products/` | GET | Products in a leaf category |
| `/products/{sku}/` | GET | Product detail |
| `/products/search/` | POST | Search products |
| `/checkout/` | GET | Active cart |
| `/checkout/lines/` | POST | Add/replace cart items |
| `/orders/` | GET | Order history |
| `/orders/{token}/` | GET | Order detail |
| `/product-lists/` | GET/POST | Saved product lists CRUD |
| `/product-purchase-stats/` | GET | Purchase frequency analytics |
| `/shopping-notes/{token}/` | GET/POST | Freeform shopping lists |
