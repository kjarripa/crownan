"""Crownan Slack Bot — Krónan shopping assistant in Slack.

Uses Slack Bolt with Socket Mode (no public URL needed).
Each Slack user gets a persistent Managed Agent session.
Messages are routed through the agent, which calls Krónan API tools.

Required env vars:
    SLACK_BOT_TOKEN      — Bot User OAuth Token (xoxb-...)
    SLACK_APP_TOKEN      — App-Level Token for Socket Mode (xapp-...)
    ANTHROPIC_API_KEY    — Anthropic API key
    KRONAN_API_KEY       — Krónan API access token

Usage:
    python -m crownan.slackbot
"""

from __future__ import annotations

import logging
import os
import re
import threading

from anthropic import Anthropic
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from crownan.agent.executor import ToolExecutor
from crownan.agent.session import run_agent_turn
from crownan.agent.setup import load_config
from crownan.client import KronanClient

load_dotenv(".env.local")
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("crownan-slackbot")

MAX_MESSAGE_LENGTH = 1000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _split_response(text: str, max_len: int = 3000) -> list[str]:
    """Split a long response into Slack-friendly chunks.

    Tries to split on paragraph boundaries (``\\n\\n``).  If a single
    paragraph still exceeds *max_len*, falls back to splitting on
    single newlines.  As a last resort, hard-splits at *max_len*.
    """
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    # First pass: split on double-newline (paragraphs)
    paragraphs = text.split("\n\n")
    current = ""
    for para in paragraphs:
        candidate = f"{current}\n\n{para}" if current else para
        if len(candidate) <= max_len:
            current = candidate
        else:
            if current:
                chunks.append(current)
            # If the paragraph itself is too long, split on single newlines
            if len(para) > max_len:
                lines = para.split("\n")
                current = ""
                for line in lines:
                    candidate = f"{current}\n{line}" if current else line
                    if len(candidate) <= max_len:
                        current = candidate
                    else:
                        if current:
                            chunks.append(current)
                        # Hard-split if a single line is still too long
                        while len(line) > max_len:
                            chunks.append(line[:max_len])
                            line = line[max_len:]
                        current = line
            else:
                current = para

    if current:
        chunks.append(current)

    return chunks


# ---------------------------------------------------------------------------
# Session Manager — one Managed Agent session per Slack user
# ---------------------------------------------------------------------------


class SessionManager:
    """Manages Managed Agent sessions per Slack user."""

    def __init__(self, anthropic_client: Anthropic, agent_config: dict):
        self.client = anthropic_client
        self.agent_config = agent_config
        self._sessions: dict[str, str] = {}  # slack_user_id -> session_id
        self._meta_lock = threading.Lock()
        self._user_locks: dict[str, threading.Lock] = {}

    def _get_user_lock(self, slack_user_id: str) -> threading.Lock:
        with self._meta_lock:
            if slack_user_id not in self._user_locks:
                self._user_locks[slack_user_id] = threading.Lock()
            return self._user_locks[slack_user_id]

    def get_or_create_session(self, slack_user_id: str) -> str:
        """Get existing session or create a new one for this Slack user."""
        with self._get_user_lock(slack_user_id):
            if slack_user_id in self._sessions:
                # Verify session is still alive
                try:
                    session = self.client.beta.sessions.retrieve(self._sessions[slack_user_id])
                    if session.status not in ("terminated",):
                        return self._sessions[slack_user_id]
                except Exception:
                    pass

            # Create new session
            session = self.client.beta.sessions.create(
                agent=self.agent_config["agent_id"],
                environment_id=self.agent_config["environment_id"],
                title=f"Crownan Slack - User {slack_user_id}",
            )
            self._sessions[slack_user_id] = session.id
            logger.info(f"Created session {session.id} for user {slack_user_id}")
            return session.id

    def reset_session(self, slack_user_id: str) -> str:
        """Force create a new session for a user."""
        with self._get_user_lock(slack_user_id):
            if slack_user_id in self._sessions:
                del self._sessions[slack_user_id]
        return self.get_or_create_session(slack_user_id)


# ---------------------------------------------------------------------------
# Slack App
# ---------------------------------------------------------------------------


def create_app() -> tuple[App, SocketModeHandler]:
    agent_config = load_config()
    anthropic_client = Anthropic()
    kronan_client = KronanClient()
    tool_executor = ToolExecutor(kronan_client)
    session_manager = SessionManager(anthropic_client, agent_config)

    _turn_locks: dict[str, threading.Lock] = {}
    _turn_meta_lock = threading.Lock()

    def _get_turn_lock(user_id: str) -> threading.Lock:
        with _turn_meta_lock:
            if user_id not in _turn_locks:
                _turn_locks[user_id] = threading.Lock()
            return _turn_locks[user_id]

    app = App(token=os.environ["SLACK_BOT_TOKEN"])

    @app.event("app_mention")
    def handle_mention(event, say, client):
        """Handle @crownan mentions in channels."""
        user_id = event["user"]
        text = event.get("text", "")
        channel = event.get("channel", "")

        # Strip bot mention(s) from the message
        message = re.sub(r"<@[A-Z0-9]+>", "", text).strip()

        if not message:
            say("Hæ! Segðu mér hvað þú vilt gera. Til dæmis: 'hvað er í körfunni minni?'")
            return

        if len(message) > MAX_MESSAGE_LENGTH:
            msg = f"Skilaboðin eru of löng (hámark {MAX_MESSAGE_LENGTH} stafir)."
            say(f"{msg} Reyndu að stytta þau.")
            return

        # Post a thinking indicator and capture its timestamp
        thinking = client.chat_postMessage(channel=channel, text="Augnablik...")
        thinking_ts = thinking["ts"]

        try:
            session_id = session_manager.get_or_create_session(user_id)

            turn_lock = _get_turn_lock(user_id)
            if not turn_lock.acquire(blocking=False):
                busy_msg = "Augnablik, ég er enn að vinna úr fyrri beiðni..."
                client.chat_update(channel=channel, ts=thinking_ts, text=busy_msg)
                turn_lock.acquire()  # wait for previous turn

            try:
                response_text, _tools_called = run_agent_turn(
                    anthropic_client,
                    session_id,
                    message,
                    tool_executor,
                )
            finally:
                turn_lock.release()

            chunks = _split_response(response_text)

            # Replace the thinking message with the first chunk
            client.chat_update(channel=channel, ts=thinking_ts, text=chunks[0])

            # Send remaining chunks as new messages
            for chunk in chunks[1:]:
                say(chunk)

        except Exception:
            logger.exception(f"Error processing mention from {user_id}")
            response_text = "Ups, eitthvað fór úrskeiðis. Reyndu aftur."
            client.chat_update(channel=channel, ts=thinking_ts, text=response_text)

    @app.event("message")
    def handle_dm(event, say, client):
        """Handle direct messages to the bot."""
        # Skip messages from bots (including ourselves)
        if event.get("bot_id") or event.get("subtype"):
            return

        # Only handle DMs (channel type "im")
        if event.get("channel_type") != "im":
            return

        user_id = event["user"]
        message = event.get("text", "").strip()
        channel = event.get("channel", "")

        if not message:
            return

        # Special commands
        if message.lower() in ("/reset", "/byrja aftur"):
            session_manager.reset_session(user_id)
            say("♻️ Ný seta byrjuð. Hvernig get ég aðstoðað?")
            return

        if len(message) > MAX_MESSAGE_LENGTH:
            msg = f"Skilaboðin eru of löng (hámark {MAX_MESSAGE_LENGTH} stafir)."
            say(f"{msg} Reyndu að stytta þau.")
            return

        # Post a thinking indicator and capture its timestamp
        thinking = client.chat_postMessage(channel=channel, text="Augnablik...")
        thinking_ts = thinking["ts"]

        try:
            session_id = session_manager.get_or_create_session(user_id)

            turn_lock = _get_turn_lock(user_id)
            if not turn_lock.acquire(blocking=False):
                busy_msg = "Augnablik, ég er enn að vinna úr fyrri beiðni..."
                client.chat_update(channel=channel, ts=thinking_ts, text=busy_msg)
                turn_lock.acquire()  # wait for previous turn

            try:
                response_text, _tools_called = run_agent_turn(
                    anthropic_client,
                    session_id,
                    message,
                    tool_executor,
                )
            finally:
                turn_lock.release()

            chunks = _split_response(response_text)

            # Replace the thinking message with the first chunk
            client.chat_update(channel=channel, ts=thinking_ts, text=chunks[0])

            # Send remaining chunks as new messages
            for chunk in chunks[1:]:
                say(chunk)

        except Exception:
            logger.exception(f"Error processing message from {user_id}")
            response_text = "Ups, eitthvað fór úrskeiðis. Reyndu aftur."
            client.chat_update(channel=channel, ts=thinking_ts, text=response_text)

    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    return app, handler


def main():
    print("\n  Crownan Slack Bot")
    print("  Starting in Socket Mode...\n")

    app, handler = create_app()
    handler.start()


if __name__ == "__main__":
    main()
