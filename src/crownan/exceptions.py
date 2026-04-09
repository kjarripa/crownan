"""Crownan exceptions."""

from __future__ import annotations

from typing import Any

import httpx


class KronanAPIError(Exception):
    """Raised when the Kronan API returns a non-success status code."""

    def __init__(self, status_code: int, detail: Any, response: httpx.Response):
        self.status_code = status_code
        self.detail = detail
        self.response = response
        super().__init__(f"HTTP {status_code}: {detail}")


class KronanConnectionError(Exception):
    """Raised on DNS, timeout, TLS, or other transport-level failures."""

    def __init__(self, message: str, original: Exception | None = None):
        self.original = original
        super().__init__(message)
