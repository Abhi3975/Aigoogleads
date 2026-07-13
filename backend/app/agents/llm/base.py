"""LLM provider interface and result types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


@dataclass(slots=True)
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass(slots=True)
class StructuredResult:
    data: BaseModel
    raw: str = ""
    usage: Usage = field(default_factory=Usage)


class LLMProvider(ABC):
    """Abstract, provider-agnostic LLM interface."""

    @abstractmethod
    async def complete_structured(
        self,
        *,
        system: str,
        user: str,
        schema: type[T],
        temperature: float = 0.4,
    ) -> StructuredResult:
        """Return a validated instance of ``schema`` produced by the model."""
        raise NotImplementedError
