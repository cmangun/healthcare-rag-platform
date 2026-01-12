"""
Immutable Audit Logger with Hash Chain

Implements an append-only audit log with cryptographic hash chains
for regulatory compliance (HIPAA, SOC 2, FDA 21 CFR Part 11).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class AuditEventType(str, Enum):
    """Types of auditable events."""
    AUTH_LOGIN = "auth.login"
    AUTH_LOGOUT = "auth.logout"
    DATA_READ = "data.read"
    DATA_WRITE = "data.write"
    RAG_QUERY = "rag.query"
    RAG_RETRIEVAL = "rag.retrieval"
    DOC_UPLOAD = "document.upload"
    PHI_DETECTED = "phi.detected"
    PHI_REDACTED = "phi.redacted"
    COST_LIMIT_EXCEEDED = "governance.cost_limit"
    SYSTEM_ERROR = "system.error"


class AuditSeverity(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Immutable audit event with hash chain support."""
    event_id: str
    event_type: AuditEventType
    severity: AuditSeverity
    timestamp: datetime
    actor_id: str | None
    actor_type: str
    action: str
    outcome: str
    details: dict[str, Any]
    request_id: str | None
    previous_hash: str | None
    event_hash: str = field(init=False)

    def __post_init__(self) -> None:
        self.event_hash = self._calculate_hash()

    def _calculate_hash(self) -> str:
        content = {
            "event_id": self.event_id, "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(), "actor_id": self.actor_id,
            "action": self.action, "outcome": self.outcome, "details": self.details,
            "previous_hash": self.previous_hash,
        }
        return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id, "event_type": self.event_type.value,
            "severity": self.severity.value, "timestamp": self.timestamp.isoformat(),
            "actor_id": self.actor_id, "action": self.action, "outcome": self.outcome,
            "details": self.details, "event_hash": self.event_hash,
        }


class AuditLogStore:
    """Abstract base for audit log storage backends."""
    async def write(self, event: AuditEvent) -> None:
        raise NotImplementedError
    async def write_batch(self, events: list[AuditEvent]) -> None:
        raise NotImplementedError
    async def query(self, start_time: datetime | None = None, event_types: list[AuditEventType] | None = None, limit: int = 100) -> list[AuditEvent]:
        raise NotImplementedError


class InMemoryAuditStore(AuditLogStore):
    """In-memory audit store for testing and development."""
    def __init__(self) -> None:
        self._events: list[AuditEvent] = []
        self._lock = asyncio.Lock()

    async def write(self, event: AuditEvent) -> None:
        async with self._lock:
            self._events.append(event)

    async def write_batch(self, events: list[AuditEvent]) -> None:
        async with self._lock:
            self._events.extend(events)

    async def query(self, start_time: datetime | None = None, event_types: list[AuditEventType] | None = None, actor_id: str | None = None, limit: int = 100) -> list[AuditEvent]:
        async with self._lock:
            results = self._events.copy()
        if start_time:
            results = [e for e in results if e.timestamp >= start_time]
        if event_types:
            results = [e for e in results if e.event_type in event_types]
        if actor_id:
            results = [e for e in results if e.actor_id == actor_id]
        return results[:limit]

    async def verify_chain(self, start_time: datetime, end_time: datetime) -> tuple[bool, list[str]]:
        events = await self.query(start_time=start_time, limit=10000)
        errors = []
        for i, event in enumerate(events):
            if i > 0 and event.previous_hash != events[i - 1].event_hash:
                errors.append(f"Event {event.event_id}: chain broken")
        return len(errors) == 0, errors


class AuditLogger:
    """Production audit logger with hash chain and async batching."""

    def __init__(self, store: AuditLogStore, enable_hash_chain: bool = True):
        self.store = store
        self.enable_hash_chain = enable_hash_chain
        self._buffer: list[AuditEvent] = []
        self._last_hash: str | None = None
        self._running = False

    async def start(self) -> None:
        self._running = True

    async def stop(self) -> None:
        self._running = False
        await self._flush()

    async def log(self, event_type: AuditEventType, action: str, outcome: str = "success",
                  severity: AuditSeverity = AuditSeverity.INFO, actor_id: str | None = None,
                  actor_type: str = "user", details: dict[str, Any] | None = None,
                  request_id: str | None = None) -> AuditEvent:
        event = AuditEvent(
            event_id=str(uuid.uuid4()), event_type=event_type, severity=severity,
            timestamp=datetime.utcnow(), actor_id=actor_id, actor_type=actor_type,
            action=action, outcome=outcome, details=details or {}, request_id=request_id,
            previous_hash=self._last_hash if self.enable_hash_chain else None,
        )
        self._last_hash = event.event_hash
        self._buffer.append(event)
        await self._flush()
        return event

    async def log_rag_query(self, query: str, user_id: str | None, request_id: str,
                            retrieved_count: int, model: str, latency_ms: float, cost_usd: float) -> AuditEvent:
        return await self.log(
            event_type=AuditEventType.RAG_QUERY, action="query", actor_id=user_id,
            request_id=request_id, details={"query_length": len(query), "retrieved_count": retrieved_count, "model": model, "latency_ms": latency_ms, "cost_usd": cost_usd},
        )

    async def log_phi_detection(self, request_id: str, phi_count: int, categories: list[str], action_taken: str, user_id: str | None = None) -> AuditEvent:
        return await self.log(
            event_type=AuditEventType.PHI_DETECTED, action="detect", severity=AuditSeverity.WARNING,
            actor_id=user_id, request_id=request_id, details={"phi_count": phi_count, "categories": categories, "action_taken": action_taken},
        )

    async def log_cost_limit(self, request_id: str, estimated_cost: float, limit: float, limit_type: str, user_id: str | None = None) -> AuditEvent:
        return await self.log(
            event_type=AuditEventType.COST_LIMIT_EXCEEDED, action="enforce_limit", outcome="blocked",
            severity=AuditSeverity.WARNING, actor_id=user_id, request_id=request_id,
            details={"estimated_cost": estimated_cost, "limit": limit, "limit_type": limit_type},
        )

    async def query_events(self, start_time: datetime | None = None, event_types: list[AuditEventType] | None = None, actor_id: str | None = None, limit: int = 100) -> list[AuditEvent]:
        await self._flush()
        return await self.store.query(start_time=start_time, event_types=event_types, actor_id=actor_id, limit=limit)

    async def verify_integrity(self, start_time: datetime, end_time: datetime) -> tuple[bool, list[str]]:
        await self._flush()
        return await self.store.verify_chain(start_time, end_time)

    async def _flush(self) -> None:
        if not self._buffer:
            return
        events = self._buffer.copy()
        self._buffer.clear()
        await self.store.write_batch(events)


_audit_logger: AuditLogger | None = None

def get_audit_logger() -> AuditLogger:
    global _audit_logger
    if _audit_logger is None:
        raise RuntimeError("Audit logger not initialized")
    return _audit_logger

async def init_audit_logger(store: AuditLogStore | None = None) -> AuditLogger:
    global _audit_logger
    if store is None:
        store = InMemoryAuditStore()
    _audit_logger = AuditLogger(store)
    await _audit_logger.start()
    return _audit_logger
