"""Base class for LLM-backed specialized agents."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from app.agents.context import RunContext

OutputT = TypeVar("OutputT", bound=BaseModel)


class BaseAgent(Generic[OutputT]):
    """An agent produces a validated structured output from a prompt.

    Subclasses define ``name``, ``system_prompt``, ``output_model`` and a
    ``build_prompt`` method. ``run`` calls the LLM, logs the decision (with
    reasoning + token usage), and returns the typed output.
    """

    name: str
    description: str = ""
    system_prompt: str
    output_model: type[OutputT]
    temperature: float = 0.4

    def build_prompt(self, payload: dict[str, Any]) -> str:
        raise NotImplementedError

    async def run(self, ctx: RunContext, payload: dict[str, Any]) -> OutputT:
        user_prompt = self.build_prompt(payload)
        result = await ctx.provider.complete_structured(
            system=self.system_prompt,
            user=user_prompt,
            schema=self.output_model,
            temperature=self.temperature,
        )
        output = result.data
        reasoning = getattr(output, "reasoning", None) or getattr(output, "summary", None)
        await ctx.log_step(
            agent_name=self.name,
            input=payload,
            output=output,
            reasoning=reasoning,
            usage=result.usage,
        )
        return output  # type: ignore[return-value]
