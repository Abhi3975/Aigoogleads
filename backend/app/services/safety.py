"""Safety Decision Engine.

Validates and clamps AI optimization recommendations against a configurable
``OptimizationPolicy`` so autonomous execution stays within strict bounds. Pure
logic (no I/O) — fully unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.models.optimization import OptimizationPolicy
from app.schemas.agents import Recommendation, RecommendationType

# Actions the autonomous loop is allowed to enact.
_EXECUTABLE = {
    RecommendationType.ADJUST_BUDGET,
    RecommendationType.PAUSE_CAMPAIGN,
    RecommendationType.ENABLE_CAMPAIGN,
    RecommendationType.ADJUST_BID,
}


@dataclass(slots=True)
class SafetyDecision:
    recommendation: Recommendation
    approved: bool
    reason: str
    adjusted_value: float | None
    explanation: str


class SafetyEngine:
    def __init__(self, policy: OptimizationPolicy) -> None:
        self.policy = policy

    def evaluate(
        self, recommendations: list[Recommendation], *, context: dict[str, dict[str, Any]]
    ) -> list[SafetyDecision]:
        return [self._evaluate_one(rec, context) for rec in recommendations]

    def _evaluate_one(
        self, rec: Recommendation, context: dict[str, dict[str, Any]]
    ) -> SafetyDecision:
        if float(rec.confidence) < float(self.policy.min_confidence):
            return self._reject(rec, f"confidence {rec.confidence} below policy minimum")
        if rec.type not in _EXECUTABLE:
            return self._reject(rec, f"action '{rec.type.value}' not permitted autonomously")

        ctx = context.get(rec.target, {})
        if rec.type is RecommendationType.ADJUST_BUDGET:
            return self._budget(rec, ctx)
        if rec.type is RecommendationType.ADJUST_BID:
            return self._bid(rec, ctx)
        if rec.type is RecommendationType.PAUSE_CAMPAIGN:
            return self._pause(rec, ctx)
        return self._approve(rec, None, "Enable campaign per recommendation.")

    # -- Budget / bid clamping --------------------------------------------
    def _clamp_pct(self, current: float, proposed: float, max_inc: float, max_dec: float) -> float:
        if proposed >= current:
            return min(proposed, current * (1 + max_inc / 100.0))
        return max(proposed, current * (1 - max_dec / 100.0))

    def _budget(self, rec: Recommendation, ctx: dict[str, Any]) -> SafetyDecision:
        current = _num(ctx.get("budget")) or _num(rec.current_value)
        proposed = _num(rec.proposed_value)
        if current is None or proposed is None:
            return self._reject(rec, "missing current or proposed budget")
        adjusted = round(
            self._clamp_pct(
                current,
                proposed,
                float(self.policy.max_budget_increase_pct),
                float(self.policy.max_budget_decrease_pct),
            ),
            2,
        )
        pct = ((adjusted - current) / current * 100.0) if current else 0.0
        clamped = abs(adjusted - proposed) > 0.005
        note = " (clamped to policy limit)" if clamped else ""
        explanation = (
            f"Adjusted daily budget for {rec.target} from {current} to {adjusted} "
            f"({pct:+.0f}%){note}. {rec.rationale} Expected impact: {rec.expected_impact}."
        )
        return self._approve(rec, adjusted, explanation)

    def _bid(self, rec: Recommendation, ctx: dict[str, Any]) -> SafetyDecision:
        current = _num(ctx.get("bid")) or _num(rec.current_value)
        proposed = _num(rec.proposed_value)
        if current is None or proposed is None:
            return self._reject(rec, "missing current or proposed bid")
        cap = float(self.policy.max_bid_change_pct)
        adjusted = round(self._clamp_pct(current, proposed, cap, cap), 2)
        explanation = (
            f"Adjusted bid for {rec.target} from {current} to {adjusted}. "
            f"{rec.rationale} Expected impact: {rec.expected_impact}."
        )
        return self._approve(rec, adjusted, explanation)

    def _pause(self, rec: Recommendation, ctx: dict[str, Any]) -> SafetyDecision:
        clicks = int(ctx.get("clicks", 0) or 0)
        days = ctx.get("days_active")
        if clicks < self.policy.min_clicks_required:
            return self._reject(
                rec, f"only {clicks} clicks (< {self.policy.min_clicks_required} required to pause)"
            )
        if days is not None and int(days) < self.policy.min_days_active:
            return self._reject(
                rec, f"campaign active {days}d (< {self.policy.min_days_active}d required to pause)"
            )
        explanation = (
            f"Paused {rec.target} after {clicks} clicks with poor efficiency. "
            f"{rec.rationale} Expected impact: {rec.expected_impact}."
        )
        return self._approve(rec, None, explanation)

    # -- Helpers -----------------------------------------------------------
    @staticmethod
    def _approve(rec: Recommendation, adjusted: float | None, explanation: str) -> SafetyDecision:
        return SafetyDecision(rec, True, "approved by policy", adjusted, explanation)

    @staticmethod
    def _reject(rec: Recommendation, reason: str) -> SafetyDecision:
        return SafetyDecision(rec, False, reason, None, f"Rejected: {reason}. ({rec.rationale})")


def _num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
