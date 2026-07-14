"""Security hardening tests: rate limiting, security headers, request id."""

from __future__ import annotations

from types import SimpleNamespace

from httpx import AsyncClient

from app.core.rate_limit import RateLimiter


def test_rate_limit_memory_window() -> None:
    limiter = RateLimiter(times=2, seconds=60, scope="unit", enabled=True)
    assert limiter._allowed_memory("k") is True
    assert limiter._allowed_memory("k") is True
    assert limiter._allowed_memory("k") is False  # third within window is blocked


async def test_rate_limiter_disabled_is_noop() -> None:
    limiter = RateLimiter(times=1, seconds=60, scope="unit", enabled=False)
    request = SimpleNamespace(headers={}, client=SimpleNamespace(host="1.2.3.4"))
    # Should never raise regardless of call count when disabled.
    for _ in range(5):
        await limiter(request)  # type: ignore[arg-type]


async def test_security_headers_and_request_id(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers.get("x-request-id")
