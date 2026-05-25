"""AI cost estimation for observability and quota checks."""

from __future__ import annotations

from dataclasses import dataclass

MODEL_PRICING_USD_PER_1M: dict[str, dict[str, float]] = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "text-embedding-3-large": {"input": 0.13, "output": 0.0},
    "text-embedding-3-small": {"input": 0.02, "output": 0.0},
}


def estimate_cost_usd(
    model: str,
    prompt_tokens: int,
    completion_tokens: int = 0,
) -> float:
    """Return estimated USD cost for a single AI request."""
    pricing = MODEL_PRICING_USD_PER_1M.get(model)
    if pricing is None:
        return 0.0
    cost = (
        prompt_tokens * pricing["input"] + completion_tokens * pricing["output"]
    ) / 1_000_000
    return round(cost, 6)


@dataclass
class UsageRecord:
    model: str
    prompt_tokens: int
    completion_tokens: int = 0

    @property
    def cost_usd(self) -> float:
        return estimate_cost_usd(self.model, self.prompt_tokens, self.completion_tokens)


def aggregate_cost_usd(records: list[UsageRecord]) -> float:
    return round(sum(record.cost_usd for record in records), 6)


def quota_utilization(used_usd: float, cap_usd: float) -> float:
    if cap_usd <= 0:
        return 1.0
    return round(used_usd / cap_usd, 4)


def should_warn_quota(used_usd: float, cap_usd: float, threshold: float = 0.8) -> bool:
    return quota_utilization(used_usd, cap_usd) >= threshold
