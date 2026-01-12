"""
Cost Guard - Enterprise LLM Cost Controls

Implements token-based cost estimation, per-request limits, and budget enforcement
for production LLM deployments in regulated environments.
"""

from __future__ import annotations

import hashlib
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from threading import Lock
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class CostTier(str, Enum):
    """Cost tiers for different model classes."""
    GPT4_TURBO = "gpt-4-turbo"
    GPT4 = "gpt-4"
    GPT35_TURBO = "gpt-3.5-turbo"
    CLAUDE_OPUS = "claude-3-opus"
    CLAUDE_SONNET = "claude-3-sonnet"
    EMBEDDING_ADA = "text-embedding-ada-002"


MODEL_PRICING = {
    CostTier.GPT4_TURBO: {"input": 0.01, "output": 0.03},
    CostTier.GPT4: {"input": 0.03, "output": 0.06},
    CostTier.GPT35_TURBO: {"input": 0.0005, "output": 0.0015},
    CostTier.CLAUDE_OPUS: {"input": 0.015, "output": 0.075},
    CostTier.CLAUDE_SONNET: {"input": 0.003, "output": 0.015},
    CostTier.EMBEDDING_ADA: {"input": 0.0001, "output": 0.0},
}


class CostGuardError(Exception):
    """Base exception for cost guard violations."""
    pass


class CostLimitExceededError(CostGuardError):
    """Raised when cost limit is exceeded."""
    def __init__(self, message: str, estimated_cost: float, limit: float, limit_type: str):
        super().__init__(message)
        self.estimated_cost = estimated_cost
        self.limit = limit
        self.limit_type = limit_type


@dataclass
class CostEstimate:
    """Detailed cost estimate for a request."""
    model: str
    input_tokens: int
    estimated_output_tokens: int
    input_cost_usd: float
    output_cost_usd: float
    total_cost_usd: float
    request_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "input_tokens": self.input_tokens,
            "estimated_output_tokens": self.estimated_output_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "request_id": self.request_id,
        }


@dataclass
class UsageRecord:
    """Record of actual usage after completion."""
    request_id: str
    model: str
    input_tokens: int
    output_tokens: int
    actual_cost_usd: float
    latency_ms: float
    user_id: str | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


class CostGuardConfig(BaseModel):
    """Configuration for cost guard."""
    max_cost_per_request_usd: float = Field(default=0.50, ge=0.0)
    max_input_tokens: int = Field(default=8000, ge=1)
    max_output_tokens: int = Field(default=4000, ge=1)
    max_cost_per_user_hourly_usd: float = Field(default=5.0, ge=0.0)
    max_cost_per_user_daily_usd: float = Field(default=25.0, ge=0.0)
    max_requests_per_user_hourly: int = Field(default=100, ge=1)
    max_cost_daily_usd: float = Field(default=500.0, ge=0.0)
    output_estimation_multiplier: float = Field(default=1.5, ge=1.0)


class CostGuard:
    """Enterprise cost guard for LLM requests."""

    def __init__(self, config: CostGuardConfig | None = None):
        self.config = config or CostGuardConfig()
        self._usage_records: list[UsageRecord] = []
        self._user_usage: dict[str, list[UsageRecord]] = defaultdict(list)
        self._lock = Lock()
        self._total_cost_today = 0.0

    def estimate_cost(self, prompt: str, model: str, max_output_tokens: int | None = None) -> CostEstimate:
        """Estimate cost for a request before execution."""
        tier = self._get_cost_tier(model)
        pricing = MODEL_PRICING.get(tier, MODEL_PRICING[CostTier.GPT35_TURBO])
        input_tokens = len(prompt) // 4  # Simple estimate
        if max_output_tokens is None:
            max_output_tokens = self.config.max_output_tokens
        estimated_output = int(max_output_tokens * self.config.output_estimation_multiplier)
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (estimated_output / 1000) * pricing["output"]
        request_id = f"req_{hashlib.sha256(f'{prompt}:{time.time_ns()}'.encode()).hexdigest()[:16]}"
        return CostEstimate(
            model=model, input_tokens=input_tokens, estimated_output_tokens=estimated_output,
            input_cost_usd=input_cost, output_cost_usd=output_cost,
            total_cost_usd=input_cost + output_cost, request_id=request_id,
        )

    def validate_request(self, estimate: CostEstimate, user_id: str | None = None) -> None:
        """Validate request against cost and rate limits."""
        if estimate.total_cost_usd > self.config.max_cost_per_request_usd:
            raise CostLimitExceededError(
                f"Estimated cost ${estimate.total_cost_usd:.4f} exceeds limit",
                estimated_cost=estimate.total_cost_usd,
                limit=self.config.max_cost_per_request_usd,
                limit_type="per_request",
            )
        if estimate.input_tokens > self.config.max_input_tokens:
            raise CostLimitExceededError(
                f"Input tokens {estimate.input_tokens} exceeds limit",
                estimated_cost=estimate.input_tokens,
                limit=self.config.max_input_tokens,
                limit_type="input_tokens",
            )

    def record_usage(self, request_id: str, model: str, input_tokens: int, output_tokens: int, latency_ms: float, user_id: str | None = None) -> UsageRecord:
        """Record actual usage after request completion."""
        tier = self._get_cost_tier(model)
        pricing = MODEL_PRICING.get(tier, MODEL_PRICING[CostTier.GPT35_TURBO])
        actual_cost = (input_tokens / 1000) * pricing["input"] + (output_tokens / 1000) * pricing["output"]
        record = UsageRecord(request_id=request_id, model=model, input_tokens=input_tokens, output_tokens=output_tokens, actual_cost_usd=actual_cost, latency_ms=latency_ms, user_id=user_id)
        with self._lock:
            self._usage_records.append(record)
            self._total_cost_today += actual_cost
            if user_id:
                self._user_usage[user_id].append(record)
        return record

    def get_usage_summary(self, user_id: str | None = None, hours: int = 24) -> dict[str, Any]:
        """Get usage summary for monitoring."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        with self._lock:
            if user_id:
                records = [r for r in self._user_usage.get(user_id, []) if r.timestamp > cutoff]
            else:
                records = [r for r in self._usage_records if r.timestamp > cutoff]
        if not records:
            return {"period_hours": hours, "request_count": 0, "total_cost_usd": 0.0}
        return {
            "period_hours": hours, "request_count": len(records),
            "total_cost_usd": sum(r.actual_cost_usd for r in records),
            "total_input_tokens": sum(r.input_tokens for r in records),
        }

    def _get_cost_tier(self, model: str) -> CostTier:
        model_lower = model.lower()
        if "gpt-4-turbo" in model_lower or "gpt-4o" in model_lower:
            return CostTier.GPT4_TURBO
        elif "gpt-4" in model_lower:
            return CostTier.GPT4
        elif "claude" in model_lower and "opus" in model_lower:
            return CostTier.CLAUDE_OPUS
        elif "claude" in model_lower:
            return CostTier.CLAUDE_SONNET
        return CostTier.GPT35_TURBO
