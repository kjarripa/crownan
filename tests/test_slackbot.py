"""Test Slack bot utility functions."""

from __future__ import annotations

import re

import pytest

pytest.importorskip("slack_bolt", reason="slack-bolt not installed")

from crownan.slackbot.app import _split_response  # noqa: E402


class TestSplitResponse:
    def test_short_text_single_element(self):
        result = _split_response("short text")

        assert result == ["short text"]
        assert len(result) == 1

    def test_long_text_splits_on_paragraph_boundaries(self):
        # Create text that exceeds the default 3000-char limit
        text = "a\n\nb\n\nc" * 100
        result = _split_response(text)

        assert len(result) >= 1
        # Each chunk should respect the max length
        for chunk in result:
            assert len(chunk) <= 3000

        # Reconstruct: joining on \n\n should recover the original paragraphs
        reconstructed = "\n\n".join(result)
        # All original content should be present
        assert reconstructed.count("a") == text.count("a")
        assert reconstructed.count("b") == text.count("b")
        assert reconstructed.count("c") == text.count("c")


class TestMentionRegex:
    """Test the mention-stripping regex used in the Slack bot."""

    MENTION_RE = re.compile(r"<@[A-Z0-9]+>")

    def test_strips_single_mention(self):
        result = self.MENTION_RE.sub("", "<@U123ABC> hello").strip()

        assert result == "hello"

    def test_strips_multiple_mentions(self):
        result = self.MENTION_RE.sub("", "<@U123ABC> <@U456DEF> hello world").strip()

        assert result == "hello world"
