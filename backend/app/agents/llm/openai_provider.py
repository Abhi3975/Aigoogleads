"""OpenAI-compatible chat-completions provider with structured output.

Works with any endpoint implementing the OpenAI ``/chat/completions`` API
(OpenAI, Azure OpenAI, the Vercel AI Gateway, local servers, …). Requests
JSON-schema-constrained output when supported, falling back to JSON-object
mode with the schema embedded in the prompt.
"""

from __future__ import annotations

import json
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from app.agents.llm.base import LLMProvider, StructuredResult, Usage
from app.core.config import settings
from app.core.exceptions import ExternalServiceError
from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class OpenAIProvider(LLMProvider):
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout: float = 60.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    async def complete_structured(
        self,
        *,
        system: str,
        user: str,
        schema: type[T],
        temperature: float = 0.4,
    ) -> StructuredResult:
        json_schema = schema.model_json_schema()
        schema_hint = (
            f"{system}\n\nReturn ONLY a JSON object matching this JSON schema:\n"
            f"{json.dumps(json_schema)}"
        )

        # Prefer strict json_schema; fall back to json_object for compatibility.
        for response_format in (
            {
                "type": "json_schema",
                "json_schema": {"name": schema.__name__, "schema": json_schema},
            },
            {"type": "json_object"},
        ):
            payload = {
                "model": self.model,
                "temperature": temperature,
                "messages": [
                    {
                        "role": "system",
                        "content": schema_hint
                        if response_format["type"] == "json_object"
                        else system,
                    },
                    {"role": "user", "content": user},
                ],
                "response_format": response_format,
            }
            content, usage, ok = await self._post(payload)
            if not ok:
                continue
            try:
                data = schema.model_validate_json(content)
            except PydanticValidationError:
                # Try lenient parse (model may wrap or add prose).
                data = schema.model_validate(_extract_json(content))
            return StructuredResult(data=data, raw=content, usage=usage)

        raise ExternalServiceError("LLM did not return usable structured output.")

    async def _post(self, payload: dict[str, Any]) -> tuple[str, Usage, bool]:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions", json=payload, headers=headers
                )
        except httpx.HTTPError as exc:
            raise ExternalServiceError("Failed to reach the LLM provider.") from exc

        if resp.status_code >= 400:
            # 400 on unsupported response_format => signal caller to fall back.
            if resp.status_code == 400 and payload["response_format"]["type"] == "json_schema":
                logger.warning("llm_json_schema_unsupported_fallback")
                return "", Usage(), False
            raise ExternalServiceError(
                "LLM provider returned an error.",
                details={"status": resp.status_code, "body": resp.text[:500]},
            )

        body = resp.json()
        content = body["choices"][0]["message"]["content"]
        u = body.get("usage", {})
        usage = Usage(
            prompt_tokens=u.get("prompt_tokens", 0),
            completion_tokens=u.get("completion_tokens", 0),
            total_tokens=u.get("total_tokens", 0),
        )
        return content, usage, True


def _extract_json(text: str) -> dict[str, Any]:
    """Best-effort extraction of a JSON object embedded in model output."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ExternalServiceError("LLM response contained no JSON object.")
    return json.loads(text[start : end + 1])


def build_default_provider() -> OpenAIProvider:
    return OpenAIProvider(
        api_key=settings.AI_API_KEY,
        base_url=settings.AI_BASE_URL,
        model=settings.AI_DEFAULT_MODEL,
    )
