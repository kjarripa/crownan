![Crownan](https://raw.githubusercontent.com/kjarripa/crownan/main/assets/logo.jpg)

# Crownan

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

**AI-powered tools for Kronan, Iceland's supermarket**

Open-source Python SDK, CLI, and Slack bot for the Kronan snjallverslun API. Manage your grocery shopping through natural language in Icelandic.

## Features

- **Python SDK** -- 30 typed methods covering every Kronan API endpoint (products, cart, orders, categories, stats)
- **CLI tool** -- search products, manage your cart, browse categories, view orders, and check purchase stats from the terminal
- **Slack Bot** -- chat with your supermarket in Icelandic, powered by Claude as a Managed Agent
- **Benchmark suite** -- 8 test queries to validate agent behavior and catch regressions

## Quick Start

**Prerequisites:** Python 3.11+, a Kronan account (with Audkenni), an Anthropic API key.

```bash
pip install crownan[slackbot]
```

Copy the example environment file and fill in your keys:

```bash
cp .env.example .env.local
```

| Variable | Description |
|---|---|
| `KRONAN_API_KEY` | Your Kronan AccessToken (Settings > Access Tokens at kronan.is) |
| `ANTHROPIC_API_KEY` | Anthropic API key from console.anthropic.com |
| `SLACK_BOT_TOKEN` | *(optional)* Slack Bot User OAuth Token (`xoxb-...`) |
| `SLACK_APP_TOKEN` | *(optional)* Slack App-Level Token (`xapp-...`) |

## Setup

Verify your Kronan connection:

```bash
crownan me
```

Deploy your Managed Agent (creates a personal Claude agent with Kronan tools):

```bash
crownan-agent-setup
```

Run the benchmark suite to verify everything works:

```bash
crownan-benchmark
```

See [docs/agent-setup.md](docs/agent-setup.md) for detailed agent configuration.

## CLI Usage

```bash
# Search for products
crownan search mjolk

# Get product details by SKU
crownan product 02500188

# View your cart
crownan cart

# Add a product to your cart
crownan cart add 02500188

# Clear your cart
crownan cart clear

# Browse the category tree
crownan categories

# View order history
crownan orders

# Purchase frequency stats
crownan stats
```

## Slack Bot

Chat with your supermarket in Icelandic through Slack -- DM the bot, @mention it in channels, or use `/reset` to start a new session.

See [docs/slackbot-setup.md](docs/slackbot-setup.md) for the full setup guide.

## How It Works

1. **SDK** wraps the Kronan REST API with 30 typed Python methods
2. **Managed Agent** (Claude Sonnet 4.6) interprets Icelandic natural language and decides which API tools to call
3. **Custom tools** bridge the agent to the SDK: search, cart, categories, orders, stats (10 tools total)
4. **Slack bot** runs one agent session per user via Socket Mode -- stateful conversations with automatic context

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and PR process.

## License

MIT -- see [LICENSE](LICENSE) for details.
