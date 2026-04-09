# Contributing to Crownan

Please note that this project is released with a [Code of Conduct](CODE_OF_CONDUCT.md). By participating you agree to abide by its terms.

Thanks for your interest in contributing! Here's how to get started.

## Development Setup

1. Fork and clone the repo:

   ```bash
   git clone https://github.com/<your-username>/crownan.git
   cd crownan
   ```

2. Create a virtual environment and install in editable mode with all extras:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev,slackbot]"
   ```

3. Copy the environment file and add your keys:

   ```bash
   cp .env.example .env.local
   ```

## Agent Setup

Each contributor needs their own Managed Agent. After configuring your `.env.local` with your Anthropic API key:

```bash
crownan-agent-setup
```

This creates a personal Claude agent tied to your API key. Agent config is stored locally at `~/.crownan/agent_config.json` and is not committed to the repo.

## Code Style

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
ruff check .
ruff format .
```

Target: Python 3.11+, line length 100.

## Running Tests

```bash
pytest
```

## Running Benchmarks

The benchmark suite sends 8 Icelandic test queries through the agent and validates behavior:

```bash
crownan-benchmark
```

This requires a working agent and valid Kronan API key.

## PR Process

1. Open an issue first for non-trivial changes (new features, architecture changes)
2. Fork the repo and create a feature branch from `main`
3. Make your changes, keeping commits focused
4. Ensure `ruff check .` and `pytest` pass
5. Open a PR against `main` with a clear description of what and why

## Questions?

Open an issue on GitHub -- we're happy to help.
