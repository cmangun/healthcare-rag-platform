"""Tests for cost guard governance module."""

import pytest
from datetime import datetime, timedelta

from src.governance.cost_guard import (
    CostGuard,
    CostGuardConfig,
    CostEstimate,
    CostGuardError,
    MODEL_PRICING,
)


class TestCostEstimation:
    """Test cost estimation functionality."""
    
    def test_estimate_cost_gpt4(self):
        """Test cost estimation for GPT-4."""
        guard = CostGuard()
        
        estimate = guard.estimate_cost(
            model="gpt-4",
            input_tokens=1000,
            output_tokens=500,
        )
        
        # GPT-4: $0.03/1K input, $0.06/1K output
        expected_input = 1000 * 0.03 / 1000
        expected_output = 500 * 0.06 / 1000
        
        assert estimate.input_cost == pytest.approx(expected_input, rel=1e-4)
        assert estimate.output_cost == pytest.approx(expected_output, rel=1e-4)
        assert estimate.total_cost == pytest.approx(expected_input + expected_output, rel=1e-4)
    
    def test_estimate_cost_claude(self):
        """Test cost estimation for Claude."""
        guard = CostGuard()
        
        estimate = guard.estimate_cost(
            model="claude-3-sonnet",
            input_tokens=2000,
            output_tokens=1000,
        )
        
        assert estimate.model == "claude-3-sonnet"
        assert estimate.input_tokens == 2000
        assert estimate.output_tokens == 1000
        assert estimate.total_cost > 0
    
    def test_estimate_cost_unknown_model(self):
        """Test cost estimation falls back for unknown models."""
        guard = CostGuard()
        
        estimate = guard.estimate_cost(
            model="unknown-model-xyz",
            input_tokens=1000,
            output_tokens=500,
        )
        
        # Should use default pricing
        assert estimate.total_cost > 0


class TestCostValidation:
    """Test cost limit validation."""
    
    def test_validate_within_limit(self):
        """Test validation passes for costs within limit."""
        config = CostGuardConfig(max_cost_per_request=1.0)
        guard = CostGuard(config)
        
        estimate = CostEstimate(
            model="gpt-4",
            input_tokens=100,
            output_tokens=50,
            input_cost=0.003,
            output_cost=0.003,
            total_cost=0.006,
        )
        
        # Should not raise
        guard.validate_request(estimate)
    
    def test_validate_exceeds_limit(self):
        """Test validation fails for costs exceeding limit."""
        config = CostGuardConfig(max_cost_per_request=0.01)
        guard = CostGuard(config)
        
        estimate = CostEstimate(
            model="gpt-4",
            input_tokens=10000,
            output_tokens=5000,
            input_cost=0.30,
            output_cost=0.30,
            total_cost=0.60,
        )
        
        with pytest.raises(CostGuardError) as exc_info:
            guard.validate_request(estimate)
        
        assert "exceeds limit" in str(exc_info.value).lower()


class TestUserRateLimiting:
    """Test per-user rate limiting."""
    
    def test_user_within_hourly_limit(self):
        """Test user within hourly request limit."""
        config = CostGuardConfig(
            max_requests_per_hour=100,
            max_cost_per_hour=10.0,
        )
        guard = CostGuard(config)
        
        # First request should pass
        guard.check_user_limits("user_123")
    
    def test_user_exceeds_hourly_requests(self):
        """Test user exceeding hourly request limit."""
        config = CostGuardConfig(max_requests_per_hour=5)
        guard = CostGuard(config)
        
        # Make requests up to limit
        for i in range(5):
            guard.record_usage("user_123", CostEstimate(
                model="gpt-4",
                input_tokens=100,
                output_tokens=50,
                input_cost=0.003,
                output_cost=0.003,
                total_cost=0.006,
            ))
        
        # Next request should fail
        with pytest.raises(CostGuardError) as exc_info:
            guard.check_user_limits("user_123")
        
        assert "rate limit" in str(exc_info.value).lower()


class TestGlobalBudget:
    """Test global budget tracking."""
    
    def test_global_budget_tracking(self):
        """Test that global budget is tracked correctly."""
        config = CostGuardConfig(global_daily_budget=100.0)
        guard = CostGuard(config)
        
        # Record some usage
        for i in range(10):
            guard.record_usage("user_123", CostEstimate(
                model="gpt-4",
                input_tokens=1000,
                output_tokens=500,
                input_cost=0.03,
                output_cost=0.03,
                total_cost=0.06,
            ))
        
        stats = guard.get_usage_stats()
        assert stats["total_requests"] == 10
        assert stats["total_cost"] == pytest.approx(0.60, rel=1e-2)


class TestModelPricing:
    """Test model pricing configuration."""
    
    def test_model_pricing_exists(self):
        """Test that common models have pricing."""
        assert "gpt-4" in MODEL_PRICING
        assert "gpt-4o" in MODEL_PRICING
        assert "gpt-3.5-turbo" in MODEL_PRICING
        assert "claude-3-opus" in MODEL_PRICING
        assert "claude-3-sonnet" in MODEL_PRICING
    
    def test_embedding_pricing(self):
        """Test embedding model pricing."""
        assert "text-embedding-ada-002" in MODEL_PRICING
        assert "text-embedding-3-small" in MODEL_PRICING
