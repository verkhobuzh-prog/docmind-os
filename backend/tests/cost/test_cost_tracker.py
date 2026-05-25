"""Cost tracking tests — pricing formula and quota helpers."""

import pytest

from app.utils.cost_tracker import (
    UsageRecord,
    aggregate_cost_usd,
    estimate_cost_usd,
    quota_utilization,
    should_warn_quota,
)


@pytest.mark.cost
class TestCostTracker:
    def test_estimate_chat_cost_gpt4o_mini(self):
        cost = estimate_cost_usd("gpt-4o-mini", prompt_tokens=1000, completion_tokens=500)
        assert cost == pytest.approx(0.00045, rel=1e-3)

    def test_estimate_embedding_cost(self):
        cost = estimate_cost_usd("text-embedding-3-large", prompt_tokens=2000)
        assert cost == pytest.approx(0.00026, rel=1e-3)

    def test_unknown_model_returns_zero(self):
        assert estimate_cost_usd("unknown-model", prompt_tokens=1000) == 0.0

    def test_aggregate_multiple_requests(self):
        records = [
            UsageRecord("gpt-4o-mini", prompt_tokens=1000, completion_tokens=200),
            UsageRecord("text-embedding-3-small", prompt_tokens=5000),
        ]
        total = aggregate_cost_usd(records)
        assert total > 0
        assert total == pytest.approx(
            records[0].cost_usd + records[1].cost_usd,
            rel=1e-6,
        )

    def test_quota_utilization_and_warning(self):
        used = 82.0
        cap = 100.0
        assert quota_utilization(used, cap) == 0.82
        assert should_warn_quota(used, cap, threshold=0.8) is True
        assert should_warn_quota(50.0, cap, threshold=0.8) is False
