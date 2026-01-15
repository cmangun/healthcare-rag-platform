"""Tests for cost guard governance module."""

from __future__ import annotations

import pytest

from src.governance.cost_guard import (
    CostGuard,
    CostGuardConfig,
    CostLimitExceededError,
    CostTier,
    MODEL_PRICING,
)


def _prompt_with_tokens(token_count: int) -> str:
    """Create a prompt with a predictable token estimate (len // 4)."""
    return "a" * (token_count * 4)


class TestCostEstimation:
    """Test cost estimation functionality."""

    def test_estimate_cost_gpt4(self):
        """Test cost estimation for GPT-4."""
        guard = CostGuard(CostGuardConfig(output_estimation_multiplier=1.0))
        prompt = _prompt_with_tokens(1000)

        estimate = guard.estimate_cost(
            prompt=prompt,
            model="gpt-4",
            max_output_tokens=500,
        )

        # GPT-4: $0.03/1K input, $0.06/1K output
        expected_input = 1000 * 0.03 / 1000
        expected_output = 500 * 0.06 / 1000

        assert estimate.input_tokens == 1000
        assert estimate.estimated_output_tokens == 500
        assert estimate.input_cost_usd == pytest.approx(expected_input, rel=1e-4)
        assert estimate.output_cost_usd == pytest.approx(expected_output, rel=1e-4)
        assert estimate.total_cost_usd == pytest.approx(expected_input + expected_output, rel=1e-4)

    def test_estimate_cost_claude(self):
        """Test cost estimation for Claude."""
        guard = CostGuard(CostGuardConfig(output_estimation_multiplier=1.0))
        prompt = _prompt_with_tokens(2000)

        estimate = guard.estimate_cost(
            prompt=prompt,
            model="claude-3-sonnet",
            max_output_tokens=1000,
        )

        assert estimate.model == "claude-3-sonnet"
        assert estimate.input_tokens == 2000
        assert estimate.estimated_output_tokens == 1000
        assert estimate.total_cost_usd > 0

    def test_estimate_cost_unknown_model(self):
        """Test cost estimation falls back for unknown models."""
        guard = CostGuard(CostGuardConfig(output_estimation_multiplier=1.0))
        prompt = _prompt_with_tokens(1000)

        estimate = guard.estimate_cost(
            prompt=prompt,
            model="unknown-model-xyz",
            max_output_tokens=500,
        )

        # Should use default pricing
        assert estimate.total_cost_usd > 0

    def test_estimate_cost_gpt4o_tier(self):
        """Test GPT-4o uses the GPT-4 Turbo pricing tier."""
        guard = CostGuard(CostGuardConfig(output_estimation_multiplier=1.0))
        prompt = _prompt_with_tokens(1000)

        estimate = guard.estimate_cost(
            prompt=prompt,
            model="gpt-4o",
            max_output_tokens=500,
        )

        pricing = MODEL_PRICING[CostTier.GPT4_TURBO]
        expected_input = 1000 * pricing["input"] / 1000
        expected_output = 500 * pricing["output"] / 1000

        assert estimate.total_cost_usd == pytest.approx(expected_input + expected_output, rel=1e-4)


class TestCostValidation:
    """Test cost limit validation."""

    def test_validate_within_limit(self):
        """Test validation passes for costs within limit."""
        config = CostGuardConfig(
            max_cost_per_request_usd=1.0,
            output_estimation_multiplier=1.0,
        )
        guard = CostGuard(config)
        prompt = _prompt_with_tokens(200)

        estimate = guard.estimate_cost(prompt=prompt, model="gpt-4", max_output_tokens=100)

        # Should not raise
        guard.validate_request(estimate)

    def test_validate_exceeds_limit(self):
        """Test validation fails for costs exceeding limit."""
        config = CostGuardConfig(
            max_cost_per_request_usd=0.001,
            output_estimation_multiplier=1.0,
        )
        guard = CostGuard(config)
        prompt = _prompt_with_tokens(1000)

        estimate = guard.estimate_cost(prompt=prompt, model="gpt-4", max_output_tokens=500)

        with pytest.raises(CostLimitExceededError) as exc_info:
            guard.validate_request(estimate)

        assert "exceeds limit" in str(exc_info.value).lower()


class TestUsageTracking:
    """Test usage tracking and summaries."""

    def test_user_usage_summary(self):
        """Test per-user usage is tracked correctly."""
        guard = CostGuard(CostGuardConfig(output_estimation_multiplier=1.0))
        prompt = _prompt_with_tokens(1000)
        estimate = guard.estimate_cost(prompt=prompt, model="gpt-4", max_output_tokens=500)

        guard.record_usage(
            request_id=estimate.request_id,
            model=estimate.model,
            input_tokens=estimate.input_tokens,
            output_tokens=estimate.estimated_output_tokens,
            latency_ms=123.0,
            user_id="user_123",
        )

        summary = guard.get_usage_summary(user_id="user_123", hours=1)
        assert summary["request_count"] == 1
        assert summary["total_cost_usd"] == pytest.approx(estimate.total_cost_usd, rel=1e-4)

    def test_global_usage_summary(self):
        """Test global usage summary aggregates records."""
        guard = CostGuard(CostGuardConfig(output_estimation_multiplier=1.0))

        total_cost = 0.0
        for _ in range(10):
            estimate = guard.estimate_cost(
                prompt=_prompt_with_tokens(1000),
                model="gpt-4",
                max_output_tokens=500,
            )
            record = guard.record_usage(
                request_id=estimate.request_id,
                model=estimate.model,
                input_tokens=estimate.input_tokens,
                output_tokens=estimate.estimated_output_tokens,
                latency_ms=100.0,
                user_id="user_123",
            )
            total_cost += record.actual_cost_usd

        summary = guard.get_usage_summary(hours=24)
        assert summary["request_count"] == 10
        assert summary["total_cost_usd"] == pytest.approx(total_cost, rel=1e-4)


class TestModelPricing:
    """Test model pricing configuration."""

    def test_model_pricing_exists(self):
        """Test that common model tiers have pricing."""
        assert CostTier.GPT4_TURBO in MODEL_PRICING
        assert CostTier.GPT4 in MODEL_PRICING
        assert CostTier.GPT35_TURBO in MODEL_PRICING
        assert CostTier.CLAUDE_OPUS in MODEL_PRICING
        assert CostTier.CLAUDE_SONNET in MODEL_PRICING

    def test_embedding_pricing(self):
        """Test embedding model pricing."""
        assert CostTier.EMBEDDING_ADA in MODEL_PRICING
