"""Helpers to run async job coroutines from synchronous Celery tasks."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any, TypeVar

T = TypeVar("T")


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """Execute an async coroutine to completion in a fresh event loop."""
    return asyncio.run(coro)
