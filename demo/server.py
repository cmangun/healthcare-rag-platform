"""
Healthcare RAG Platform - Self-Contained Demo Server

Run with: python -m demo.server
Or via:   docker compose up

No external API keys required. Uses the actual platform components
(PHI detector, guardrails, cost guard, audit logger, hybrid retriever)
with synthetic embeddings for demonstration.

Endpoints:
    GET  /health           - Health check
    GET  /docs             - Swagger UI
    POST /api/v1/query     - RAG query with full governance pipeline
    GET  /api/v1/audit     - View audit log entries
    GET  /api/v1/cost      - View cost usage summary
    POST /api/v1/evaluate  - Run RAG evaluation on sample data
"""

from __future__ import annotations

import asyncio
import time
import uuid
from contextlib import asynccontextmanager

import numpy as np
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.governance.audit_logger import (
    AuditEventType,
    AuditLogger,
    AuditSeverity,
    InMemoryAuditStore,
    init_audit_logger,
)
from src.governance.cost_guard import CostGuard, CostGuardConfig, CostLimitExceededError
from src.governance.guardrails import HealthcareGuardrails
from src.governance.phi_detector import HIPAASafeHarborDetector
from src.rag.evaluation import RAGEvaluator
from src.rag.retriever import HybridRetriever

from demo.seed_data import SAMPLE_QUERIES, SYNTHETIC_DOCUMENTS

# ---------------------------------------------------------------------------
# Global state (initialized in lifespan)
# ---------------------------------------------------------------------------
retriever: HybridRetriever | None = None
phi_detector: HIPAASafeHarborDetector | None = None
guardrails: HealthcareGuardrails | None = None
cost_guard: CostGuard | None = None
audit_logger: AuditLogger | None = None
evaluator: RAGEvaluator | None = None


def _seed_retriever() -> HybridRetriever:
    """Load synthetic documents into the hybrid retriever."""
    ret = HybridRetriever(dense_weight=0.7, sparse_weight=0.3, top_k=3)
    rng = np.random.default_rng(42)
    embeddings = rng.standard_normal((len(SYNTHETIC_DOCUMENTS), 384)).astype(np.float32)
    # Normalize embeddings
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings = embeddings / norms
    ret.add_documents(SYNTHETIC_DOCUMENTS, embeddings)
    return ret


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize all platform components on startup."""
    global retriever, phi_detector, guardrails, cost_guard, audit_logger, evaluator

    retriever = _seed_retriever()
    phi_detector = HIPAASafeHarborDetector(enable_anonymization=True)
    guardrails = HealthcareGuardrails(require_disclaimer=True, min_confidence=0.5)
    cost_guard = CostGuard(CostGuardConfig(max_cost_per_request_usd=1.0))
    audit_logger = await init_audit_logger(InMemoryAuditStore())
    evaluator = RAGEvaluator(use_llm_eval=False)

    print("=" * 60)
    print("Healthcare RAG Platform - Demo Server")
    print("=" * 60)
    print(f"  Documents indexed : {len(SYNTHETIC_DOCUMENTS)}")
    print(f"  PHI detector      : active (18 Safe Harbor categories)")
    print(f"  Guardrails        : active (advice, disclaimer, grounding)")
    print(f"  Cost guard        : active ($1.00/request limit)")
    print(f"  Audit logger      : active (hash-chain enabled)")
    print(f"  Swagger UI        : http://localhost:8000/docs")
    print("=" * 60)

    yield


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Healthcare RAG Platform",
    description=(
        "HIPAA-compliant RAG with PHI detection, guardrails, cost controls, "
        "and immutable audit logging. This demo uses synthetic data and "
        "requires no external API keys."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class QueryRequest(BaseModel):
    query: str = Field(..., description="Clinical query text", min_length=3, max_length=2000)
    top_k: int = Field(default=3, ge=1, le=10, description="Number of documents to retrieve")
    model: str = Field(default="gpt-3.5-turbo", description="Model for cost estimation")


class QueryResponse(BaseModel):
    request_id: str
    query_received: str
    phi_detected: bool
    phi_categories: list[str]
    query_after_redaction: str | None
    retrieved_documents: list[dict]
    guardrail_results: list[dict]
    cost_estimate_usd: float
    latency_ms: float
    audit_event_id: str


class EvalRequest(BaseModel):
    """Run evaluation on sample queries or custom input."""
    custom_query: str | None = Field(default=None, description="Optional custom query")
    custom_answer: str | None = Field(default=None, description="Optional custom answer")
    custom_contexts: list[str] | None = Field(default=None, description="Optional custom contexts")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "components": {
            "retriever": retriever is not None,
            "phi_detector": phi_detector is not None,
            "guardrails": guardrails is not None,
            "cost_guard": cost_guard is not None,
            "audit_logger": audit_logger is not None,
        },
        "documents_indexed": len(SYNTHETIC_DOCUMENTS),
    }


@app.post("/api/v1/query", response_model=QueryResponse)
async def query_rag(req: QueryRequest):
    """
    Full governance-aware RAG query pipeline.

    Steps:
    1. PHI detection & redaction on the incoming query
    2. Cost estimation & budget validation
    3. Hybrid retrieval (dense + BM25 with RRF)
    4. Guardrail checks on a simulated response
    5. Audit logging with hash-chain
    """
    start = time.perf_counter()
    request_id = f"req_{uuid.uuid4().hex[:16]}"

    # --- 1. PHI Detection ---
    phi_result = phi_detector.detect(req.query)
    safe_query = phi_result.anonymized_text if phi_result.has_phi else req.query

    if phi_result.has_phi:
        await audit_logger.log_phi_detection(
            request_id=request_id,
            phi_count=phi_result.phi_count,
            categories=[c.value for c in phi_result.categories_found],
            action_taken="redacted",
        )

    # --- 2. Cost Estimation ---
    estimate = cost_guard.estimate_cost(safe_query, model=req.model)
    try:
        cost_guard.validate_request(estimate)
    except CostLimitExceededError as exc:
        await audit_logger.log_cost_limit(
            request_id=request_id,
            estimated_cost=exc.estimated_cost,
            limit=exc.limit,
            limit_type=exc.limit_type,
        )
        raise HTTPException(status_code=429, detail=str(exc))

    # --- 3. Hybrid Retrieval ---
    rng = np.random.default_rng(hash(safe_query) % 2**32)
    query_embedding = rng.standard_normal(384).astype(np.float32)
    query_embedding = query_embedding / np.linalg.norm(query_embedding)

    retrieval_result = retriever.retrieve(
        query=safe_query,
        query_embedding=query_embedding,
        top_k=req.top_k,
    )

    retrieved_docs = [
        {
            "id": doc.id,
            "content": doc.content[:300] + ("..." if len(doc.content) > 300 else ""),
            "score": round(doc.score, 4),
            "metadata": doc.metadata,
        }
        for doc in retrieval_result.documents
    ]

    # --- 4. Guardrails ---
    simulated_answer = (
        f"Based on the retrieved clinical documents: "
        f"{retrieval_result.documents[0].content[:200] if retrieval_result.documents else 'No results'}. "
        f"Please consult with a healthcare provider for personalized guidance."
    )
    contexts = [d.content for d in retrieval_result.documents]
    gr_results = guardrails.check_response(simulated_answer, contexts=contexts, confidence=0.85)
    guardrail_dicts = [
        {"name": r.guardrail_name, "passed": r.passed, "reason": r.reason, "severity": r.severity}
        for r in gr_results
    ]

    # --- 5. Audit ---
    audit_event = await audit_logger.log_rag_query(
        query=safe_query,
        user_id="demo_user",
        request_id=request_id,
        retrieved_count=len(retrieved_docs),
        model=req.model,
        latency_ms=retrieval_result.latency_ms,
        cost_usd=estimate.total_cost_usd,
    )

    # Record usage
    cost_guard.record_usage(
        request_id=request_id,
        model=req.model,
        input_tokens=estimate.input_tokens,
        output_tokens=estimate.estimated_output_tokens // 2,
        latency_ms=retrieval_result.latency_ms,
    )

    latency_ms = (time.perf_counter() - start) * 1000

    return QueryResponse(
        request_id=request_id,
        query_received=req.query,
        phi_detected=phi_result.has_phi,
        phi_categories=[c.value for c in phi_result.categories_found],
        query_after_redaction=safe_query if phi_result.has_phi else None,
        retrieved_documents=retrieved_docs,
        guardrail_results=guardrail_dicts,
        cost_estimate_usd=round(estimate.total_cost_usd, 6),
        latency_ms=round(latency_ms, 2),
        audit_event_id=audit_event.event_id,
    )


@app.get("/api/v1/audit")
async def get_audit_log(limit: int = 50):
    """View recent audit log entries."""
    events = await audit_logger.query_events(limit=limit)
    return {
        "count": len(events),
        "events": [e.to_dict() for e in events],
    }


@app.get("/api/v1/cost")
async def get_cost_summary():
    """View cost usage summary."""
    return cost_guard.get_usage_summary()


@app.post("/api/v1/evaluate")
async def evaluate_rag(req: EvalRequest):
    """Run RAG evaluation metrics on sample or custom data."""
    if req.custom_query and req.custom_answer and req.custom_contexts:
        report = evaluator.evaluate(
            query=req.custom_query,
            answer=req.custom_answer,
            contexts=req.custom_contexts,
        )
        return report.to_dict()

    # Run evaluation on built-in sample queries
    examples = []
    for sample in SAMPLE_QUERIES:
        # Simulate retrieval + answer for evaluation
        rng = np.random.default_rng(hash(sample["query"]) % 2**32)
        query_emb = rng.standard_normal(384).astype(np.float32)
        query_emb = query_emb / np.linalg.norm(query_emb)

        result = retriever.retrieve(query=sample["query"], query_embedding=query_emb, top_k=3)
        contexts = [d.content for d in result.documents]
        answer = contexts[0][:200] if contexts else "No answer available."

        report = evaluator.evaluate(
            query=sample["query"],
            answer=answer,
            contexts=contexts,
        )
        examples.append({
            "query": sample["query"],
            "description": sample["description"],
            "evaluation": report.to_dict(),
        })

    return {"sample_evaluations": examples}


@app.get("/api/v1/sample-queries")
async def get_sample_queries():
    """Get sample queries you can try against the /api/v1/query endpoint."""
    return {
        "queries": [
            {"query": q["query"], "description": q["description"]}
            for q in SAMPLE_QUERIES
        ],
        "usage": "POST any query to /api/v1/query with {\"query\": \"your question here\"}",
    }


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run("demo.server:app", host="0.0.0.0", port=8000, reload=False)
