"""Lightweight request context passed from the API layer into services."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RequestMeta:
    """Client metadata captured for auditing and session records."""

    ip_address: str | None = None
    user_agent: str | None = None
