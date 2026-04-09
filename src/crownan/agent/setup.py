"""Create and configure the Crownan Managed Agent and Environment.

Provides functions to create the agent and environment via the Anthropic API,
and to load/save configuration to disk.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from crownan.agent.tools import CUSTOM_TOOLS, SYSTEM_PROMPT

DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_CONFIG_PATH = Path("~/.crownan/agent_config.json").expanduser()


def create_agent(client, model: str = DEFAULT_MODEL) -> dict:
    """Create a new Crownan Managed Agent.

    Returns a dict with ``agent_id`` and ``agent_version``.
    """
    print(f"Creating Crownan agent (model={model})...")

    agent = client.beta.agents.create(
        name="Crownan — Krónan Shopping Assistant",
        model=model,
        system=SYSTEM_PROMPT,
        tools=CUSTOM_TOOLS,
    )

    print(f"  Agent ID: {agent.id}")
    print(f"  Version: {agent.version}")
    return {"agent_id": agent.id, "agent_version": agent.version}


def create_environment(client) -> dict:
    """Create a new Crownan environment.

    Returns a dict with ``environment_id``.
    """
    print("Creating environment...")

    environment = client.beta.environments.create(
        name="crownan-env",
        config={
            "type": "cloud",
            "networking": {"type": "unrestricted"},
        },
    )

    print(f"  Environment ID: {environment.id}")
    return {"environment_id": environment.id}


def load_config(config_path: Path = DEFAULT_CONFIG_PATH) -> dict:
    """Load agent configuration from a JSON file."""
    if not config_path.exists():
        raise FileNotFoundError(
            f"No agent config found at {config_path}. "
            "Run agent setup first (e.g. `crownan-agent-setup`)."
        )
    return json.loads(config_path.read_text())


def save_config(config: dict, config_path: Path = DEFAULT_CONFIG_PATH) -> None:
    """Save agent configuration to a JSON file, creating parent dirs if needed."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2))
    print(f"Config saved to {config_path}")


def main() -> None:
    """Create agent + environment and save the config (CLI entry point)."""
    import argparse

    try:
        from anthropic import Anthropic
    except ImportError:
        print("Error: anthropic package not installed.")
        print("Install with: pip install crownan[agent]")
        sys.exit(1)

    load_dotenv(".env.local")
    load_dotenv()

    parser = argparse.ArgumentParser(description="Set up the Crownan Managed Agent")
    parser.add_argument("--model", default=None, help=f"Claude model (default: {DEFAULT_MODEL})")
    parser.add_argument("--force", action="store_true", help="Recreate even if config exists")
    args = parser.parse_args()

    model = args.model or os.environ.get("CROWNAN_MODEL", DEFAULT_MODEL)

    config_path = DEFAULT_CONFIG_PATH

    # Check for existing config
    if config_path.exists() and not args.force:
        existing = json.loads(config_path.read_text())
        print(f"Found existing config: {existing}")
        response = input("Create new agent? [y/N]: ").strip().lower()
        if response != "y":
            print("Keeping existing config.")
            return

    client = Anthropic()
    config: dict = {}

    agent_info = create_agent(client, model=model)
    config.update(agent_info)

    env_info = create_environment(client)
    config.update(env_info)

    config["model"] = model

    save_config(config, config_path)
    print(json.dumps(config, indent=2))


if __name__ == "__main__":
    main()
