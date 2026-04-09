# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Fixed
- Transport error handling: DNS/timeout/TLS failures now raise `KronanConnectionError`
- Input validation on all SDK public methods (query length, page bounds, quantity limits)
- Agent error messages sanitized — no raw API details exposed to model
- Hard-coded `replace=False` in cart executor (prevents accidental cart wipe)
- Prompt injection protection added to agent system prompt
- Tool schemas tightened with bounds and `additionalProperties: false`
- Per-user locking in Slack bot (was blocking all users on one lock)
- Input length validation in Slack bot (max 1000 characters)
- Entry point import guards for optional dependencies
- Version sourced from single `_version.py` file
- CLI: removed _P class hack, improved error handling
- Session timeout (120s default) in agent streaming loop
- Rate limiting (2s delay) between benchmark queries

### Added
- `KronanConnectionError` exception for transport failures
- Model selection via `--model` flag or `CROWNAN_MODEL` env var in `crownan-agent-setup`
- `get_order_detail` documented in agent system prompt

## [0.1.0] - 2026-04-09

### Added

- Python SDK with 30 typed methods covering all Krónan API endpoints
- CLI tool (`crownan`) for product search, cart management, categories, orders, and purchase stats
- Managed Agent (Claude Sonnet 4.6) with 10 custom tools for Icelandic natural language understanding
- Slack bot with Socket Mode — manage your Krónan shopping cart through DMs and @mentions
- Benchmark suite with 8 Icelandic/English test queries (`crownan-benchmark`)
- Agent setup command (`crownan-agent-setup`) for deploying your own Managed Agent
