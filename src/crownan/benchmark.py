"""Crownan benchmark runner — validate agent tool routing.

Sends a set of benchmark queries through the Managed Agent and checks
whether the expected tool was invoked for each query.

Usage:
    python -m crownan.benchmark
    python -m crownan.benchmark --verbose
"""

from __future__ import annotations

import argparse
import sys
import time

from dotenv import load_dotenv

from crownan.agent.executor import ToolExecutor
from crownan.agent.session import run_agent_turn
from crownan.agent.setup import load_config
from crownan.client import KronanClient

load_dotenv(".env.local")
load_dotenv()

# ---------------------------------------------------------------------------
# Benchmark queries
# ---------------------------------------------------------------------------

BENCHMARKS = [
    {
        "query": "hvað er í körfunni minni?",
        "description": "What's in my cart?",
        "expected_tool": "get_cart",
    },
    {
        "query": "bættu við gúrkum í körfuna",
        "description": "Add cucumbers to cart",
        "expected_tool": "search_products",
    },
    {
        "query": "búðu til nýja körfu með sömu pöntun og síðast",
        "description": "Reorder last order",
        "expected_tool": "get_orders",
    },
    {
        "query": "leitaðu að brauði",
        "description": "Search for bread",
        "expected_tool": "search_products",
    },
    {
        "query": "hvaða flokkar eru í boði?",
        "description": "What categories available?",
        "expected_tool": "get_categories",
    },
    {
        "query": "sýndu mér hvað ég kaupi oftast",
        "description": "Show purchase stats",
        "expected_tool": "get_purchase_stats",
    },
    {
        "query": "hreinsa körfuna",
        "description": "Clear cart (should confirm)",
        "expected_tool": "clear_cart",
    },
    {
        "query": "what's in my cart?",
        "description": "English fallback",
        "expected_tool": "get_cart",
    },
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_benchmarks(verbose: bool = False) -> int:
    """Run all benchmark queries and return the number that passed."""
    from anthropic import Anthropic

    config = load_config()
    anthropic_client = Anthropic()
    kronan_client = KronanClient()
    tool_executor = ToolExecutor(kronan_client)

    # Create a single session for all benchmarks
    session = anthropic_client.beta.sessions.create(
        agent=config["agent_id"],
        environment_id=config["environment_id"],
        title="Crownan Benchmark Session",
    )
    session_id = session.id

    print("\nCrownan Benchmark Runner")
    print(f"Session: {session_id}")
    print(f"Running {len(BENCHMARKS)} benchmarks...\n")

    passed = 0
    total = len(BENCHMARKS)

    for i, bench in enumerate(BENCHMARKS, 1):
        if i > 1:
            time.sleep(2)

        query = bench["query"]
        expected = bench["expected_tool"]
        description = bench["description"]

        print(f"  [{i}/{total}] {query}")
        print(f"          ({description})")
        print(f"          Expected tool: {expected}")

        try:
            response_text, tools_called = run_agent_turn(
                anthropic_client,
                session_id,
                query,
                tool_executor,
                verbose=verbose,
            )

            tool_hit = expected in tools_called
            status = "PASS" if tool_hit else "FAIL"

            if tool_hit:
                passed += 1

            truncated = response_text[:200]
            if len(response_text) > 200:
                truncated += "..."

            print(f"          Tools called: {tools_called}")
            print(f"          Result: {status}")
            if verbose:
                print(f"          Response: {truncated}")

        except Exception as e:
            if "429" in str(e) or "rate" in str(e).lower():
                print("          Rate limited, waiting 10s...")
                time.sleep(10)
                try:
                    response_text, tools_called = run_agent_turn(
                        anthropic_client,
                        session_id,
                        query,
                        tool_executor,
                        verbose=verbose,
                    )

                    tool_hit = expected in tools_called
                    status = "PASS" if tool_hit else "FAIL"

                    if tool_hit:
                        passed += 1

                    print(f"          Tools called: {tools_called}")
                    print(f"          Result: {status}")
                except Exception as retry_e:
                    print(f"          Result: FAIL (error: {retry_e})")
                    continue
            else:
                print(f"          Result: FAIL (error: {e})")
                continue

        print()

    print(f"{'=' * 50}")
    print(f"  {passed}/{total} benchmarks passed")
    print(f"{'=' * 50}\n")

    return passed


def main():
    parser = argparse.ArgumentParser(description="Crownan benchmark runner")
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show full agent responses",
    )
    args = parser.parse_args()

    passed = run_benchmarks(verbose=args.verbose)

    # Exit with non-zero status if any benchmark failed
    if passed < len(BENCHMARKS):
        sys.exit(1)


if __name__ == "__main__":
    main()
