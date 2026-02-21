"""
Run sample queries against the demo server.

Usage:
    # After docker compose up:
    docker compose exec app python -m demo.run_queries

    # Or standalone:
    python -m demo.run_queries
"""

from __future__ import annotations

import json
import sys

import httpx

BASE_URL = "http://localhost:8000"


def main() -> None:
    print("\n" + "=" * 70)
    print("Healthcare RAG Platform — Sample Query Runner")
    print("=" * 70)

    client = httpx.Client(base_url=BASE_URL, timeout=30)

    # Health check
    try:
        r = client.get("/health")
        r.raise_for_status()
        health = r.json()
        print(f"\n[OK] Server healthy — {health['documents_indexed']} documents indexed")
    except httpx.ConnectError:
        print("\n[ERROR] Cannot connect to server. Is it running on port 8000?")
        sys.exit(1)

    # Get sample queries
    r = client.get("/api/v1/sample-queries")
    samples = r.json()["queries"]

    for i, sample in enumerate(samples, 1):
        print(f"\n{'─' * 70}")
        print(f"Query {i}: {sample['description']}")
        print(f"{'─' * 70}")
        print(f"  Input: {sample['query'][:100]}{'...' if len(sample['query']) > 100 else ''}")

        r = client.post("/api/v1/query", json={"query": sample["query"]})
        result = r.json()

        print(f"  Request ID     : {result['request_id']}")
        print(f"  PHI detected   : {result['phi_detected']}")
        if result["phi_detected"]:
            print(f"  PHI categories : {', '.join(result['phi_categories'])}")
            print(f"  Redacted query : {result['query_after_redaction'][:80]}...")
        print(f"  Docs retrieved : {len(result['retrieved_documents'])}")
        for doc in result["retrieved_documents"]:
            print(f"    - [{doc['id']}] score={doc['score']} | {doc['content'][:60]}...")
        print(f"  Guardrails     : {sum(1 for g in result['guardrail_results'] if g['passed'])}/{len(result['guardrail_results'])} passed")
        for g in result["guardrail_results"]:
            status = "PASS" if g["passed"] else "FAIL"
            print(f"    [{status}] {g['name']}: {g['reason']}")
        print(f"  Cost estimate  : ${result['cost_estimate_usd']:.6f}")
        print(f"  Latency        : {result['latency_ms']:.1f} ms")
        print(f"  Audit event    : {result['audit_event_id'][:16]}...")

    # Run evaluation
    print(f"\n{'─' * 70}")
    print("RAG Evaluation (RAGAS-style metrics on sample data)")
    print(f"{'─' * 70}")
    r = client.post("/api/v1/evaluate", json={})
    evals = r.json()["sample_evaluations"]
    for ev in evals:
        metrics = ev["evaluation"]["metrics"]
        overall = ev["evaluation"]["overall_score"]
        print(f"\n  Query: {ev['query'][:60]}...")
        print(f"  Overall: {overall:.2f}")
        for m in metrics:
            print(f"    {m['name']:25s} {m['score']:.2f}")

    # Show audit log
    print(f"\n{'─' * 70}")
    print("Audit Log (last 5 entries)")
    print(f"{'─' * 70}")
    r = client.get("/api/v1/audit", params={"limit": 5})
    for event in r.json()["events"][-5:]:
        print(f"  [{event['event_type']}] {event['action']} → {event['outcome']} | {event['event_hash'][:12]}...")

    # Cost summary
    print(f"\n{'─' * 70}")
    print("Cost Summary")
    print(f"{'─' * 70}")
    r = client.get("/api/v1/cost")
    cost = r.json()
    print(f"  Requests : {cost['request_count']}")
    print(f"  Total    : ${cost.get('total_cost_usd', 0):.6f}")

    print(f"\n{'=' * 70}")
    print("Demo complete. Explore more at http://localhost:8000/docs")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    main()
