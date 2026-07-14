"""Lightweight website content fetcher for the Website Analysis Agent.

Fetches a page and extracts title, meta description, and visible text using the
stdlib HTML parser (no extra dependencies). Truncated to a safe length for LLM
context.
"""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser

import httpx

from app.core.exceptions import ExternalServiceError

_SKIP_TAGS = {"script", "style", "noscript", "template", "svg"}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.description = ""
        self._chunks: list[str] = []
        self._skip_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            attr = dict(attrs)
            if attr.get("name") == "description" and attr.get("content"):
                self.description = attr["content"] or ""

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = data.strip()
        if not text:
            return
        if self._in_title:
            self.title += text
        else:
            self._chunks.append(text)

    @property
    def text(self) -> str:
        return " ".join(self._chunks)


@dataclass(slots=True)
class WebsiteContent:
    url: str
    title: str
    description: str
    text: str


async def fetch_website_content(url: str, *, max_chars: int = 8000) -> WebsiteContent:
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    try:
        async with httpx.AsyncClient(
            timeout=20,
            follow_redirects=True,
            headers={"User-Agent": "AI-Ads-Agent/1.0 (+website-analysis)"},
        ) as client:
            resp = await client.get(url)
    except httpx.HTTPError as exc:
        raise ExternalServiceError(f"Could not fetch website: {url}") from exc

    if resp.status_code >= 400:
        raise ExternalServiceError(
            f"Website returned HTTP {resp.status_code}: {url}",
            details={"status": resp.status_code},
        )

    parser = _TextExtractor()
    parser.feed(resp.text)
    return WebsiteContent(
        url=str(resp.url),
        title=parser.title.strip()[:300],
        description=parser.description.strip()[:600],
        text=parser.text[:max_chars],
    )
