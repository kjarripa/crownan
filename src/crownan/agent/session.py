"""Core agent session loop for the Crownan Managed Agent.

Handles streaming events, custom tool execution, and message collection.
"""

from __future__ import annotations

import json
import logging
import time

from anthropic import Anthropic

from crownan.agent.executor import ToolExecutor

logger = logging.getLogger(__name__)


def run_agent_turn(
    client: Anthropic,
    session_id: str,
    message: str,
    tool_executor: ToolExecutor,
    verbose: bool = False,
    timeout: float = 120.0,
) -> tuple[str, list[str]]:
    """Send a message and process the full agent turn, handling custom tool calls.

    Returns the agent's final text response and a list of tool names that were called.
    """
    events_by_id = {}
    agent_text_parts: list[str] = []
    tools_called: list[str] = []

    with client.beta.sessions.events.stream(session_id) as stream:
        # Send the user message
        client.beta.sessions.events.send(
            session_id,
            events=[
                {
                    "type": "user.message",
                    "content": [{"type": "text", "text": message}],
                },
            ],
        )

        start = time.monotonic()
        for event in stream:
            if time.monotonic() - start > timeout:
                logger.warning("Agent turn timed out after %.0fs", timeout)
                agent_text_parts.append("[Svarið tók of langan tíma. Reyndu aftur.]")
                break

            if event.type == "agent.custom_tool_use":
                events_by_id[event.id] = event
                tools_called.append(event.name)
                if verbose:
                    inp = json.dumps(event.input, ensure_ascii=False)[:80]
                    print(f"  [tool: {event.name}({inp})]")

            elif event.type == "agent.message":
                for block in event.content:
                    if hasattr(block, "text"):
                        agent_text_parts.append(block.text)

            elif event.type == "session.status_idle":
                stop = event.stop_reason
                if stop and stop.type == "requires_action":
                    # Execute custom tools and send results back
                    for event_id in stop.event_ids:
                        tool_event = events_by_id.get(event_id)
                        if tool_event:
                            result = tool_executor.execute(tool_event.name, tool_event.input)
                            if verbose:
                                # Show truncated result
                                preview = result[:200] + "..." if len(result) > 200 else result
                                print(f"  [result: {preview}]")

                            client.beta.sessions.events.send(
                                session_id,
                                events=[
                                    {
                                        "type": "user.custom_tool_result",
                                        "custom_tool_use_id": event_id,
                                        "content": [{"type": "text", "text": result}],
                                    },
                                ],
                            )
                    # Clear the events_by_id for the next round and
                    # reset text parts since the agent will continue
                    events_by_id.clear()

                elif stop and stop.type == "end_turn":
                    break

            elif event.type == "session.error":
                error_msg = (
                    getattr(event.error, "message", "Unknown error")
                    if event.error
                    else "Unknown error"
                )
                logger.error("Session error: %s", error_msg)
                agent_text_parts.append("\n[Villa kom upp. Reyndu aftur.]")
                break

    return "".join(agent_text_parts), tools_called
