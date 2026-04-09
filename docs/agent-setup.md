# Agent Setup

## What is a Managed Agent?

Crownan uses Anthropic's Managed Agents API to create a persistent Claude agent that understands Icelandic and has direct access to Kronan API tools. The agent runs in a cloud environment with unrestricted networking, so it can call the Kronan API on your behalf. You create it once, and it stays available for all your sessions (CLI, Slack bot, benchmarks).

## Prerequisites

- `crownan` installed (`pip install crownan[agent]` or `pip install crownan[slackbot]`)
- `ANTHROPIC_API_KEY` set in your `.env.local` file (get one at [console.anthropic.com](https://console.anthropic.com/settings/keys))

## Create the Agent

```bash
crownan-agent-setup
```

This command:

1. Creates a Claude Sonnet 4.6 Managed Agent with the `anthropic-beta: managed-agents-2026-04-01` header
2. Registers 10 custom Kronan tools: `search_products`, `get_product`, `get_cart`, `add_to_cart`, `clear_cart`, `get_categories`, `get_category_products`, `get_orders`, `get_order_detail`, `get_purchase_stats`
3. Provisions a cloud environment with unrestricted networking
4. Saves the configuration (agent ID + environment ID) to `~/.crownan/agent_config.json`

## Verify

Run the benchmark suite to confirm the agent works correctly:

```bash
crownan-benchmark
```

This sends 8 test queries in Icelandic and validates that the agent calls the right tools and returns sensible responses.

## Configuration

The agent config is stored at:

```
~/.crownan/agent_config.json
```

This file contains the `agent_id` and `environment_id` needed to start sessions. Do not edit it manually.

## Troubleshooting

**"ANTHROPIC_API_KEY not set"**
Make sure your `.env.local` file exists in the project root and contains a valid key:
```
ANTHROPIC_API_KEY=sk-ant-your_key_here
```

**"Managed Agents beta access required"**
The Managed Agents API is in beta. Ensure your Anthropic account has access and your key has the necessary permissions.

**Rate limit errors**
The Kronan API allows 200 requests per 200 seconds. The benchmark suite includes a 2-second delay between queries to reduce the chance of hitting rate limits, but heavy tool use in a single query could still trigger throttling.

## Model Selection

By default, the agent uses `claude-sonnet-4-6`. You can override this:

```bash
# Via CLI flag
crownan-agent-setup --model claude-opus-4-6

# Via environment variable
export CROWNAN_MODEL=claude-haiku-4-5
crownan-agent-setup
```

Available models: `claude-sonnet-4-6` (default, recommended), `claude-opus-4-6` (most capable), `claude-haiku-4-5` (fastest, cheapest).

The chosen model is saved in the config file. To change models, delete the config and re-run setup.

## Re-creating the Agent

If you need to start fresh, delete the config and re-run setup:

```bash
rm ~/.crownan/agent_config.json
crownan-agent-setup
```
