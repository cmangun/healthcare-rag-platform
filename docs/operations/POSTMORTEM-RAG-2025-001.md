# Post-Mortem: RAG Embedding Drift Incident

## Incident Header

| Field | Value |
|-------|-------|
| **Incident ID** | RAG-2025-001 |
| **System** | Healthcare RAG Platform |
| **Severity** | SEV-2 (Clinical Risk - Non-Patient Facing) |
| **Date Detected** | 2025-01-10 09:42 UTC |
| **Date Resolved** | 2025-01-10 11:08 UTC |
| **Duration** | 86 minutes |
| **Owner** | Forward Deployed AI Engineer |

## Executive Summary

An increase in hallucinated regulatory references was detected following a content ingestion update. No patient-facing outputs were affected. The system correctly degraded to human review mode within SLA.

## Timeline

| Time (UTC) | Event |
|------------|-------|
| 09:42 | Monitoring flagged spike in low-confidence answers |
| 09:47 | RAG confidence threshold breached (< 0.75) |
| 09:51 | Automatic fallback to retrieval-only mode |
| 10:03 | Root cause identified: embedding drift |
| 10:22 | Re-index initiated |
| 11:08 | System restored to full operation |

## Root Cause Analysis

A document ingestion pipeline update altered chunk boundaries, causing semantic dilution in embeddings and retrieval mismatch.

### Why Existing Controls Didn't Prevent It

Embedding drift detection was operating on weekly cadence, while ingestion changes occurred intra-day.

```
[Content Update]
      |
      v
[Ingestion Pipeline]
      |
      v
[Embedding Generation] <-- drift introduced here
      |
      v
[Vector Store]
      |
      v
[Retriever] <-- low relevance scores detected
      |
      v
[Confidence Gate] <-- triggered automatic fallback
      |
      v
[Human Review Fallback]
```

## Corrective Actions

| Action | Owner | Status |
|--------|-------|--------|
| Add ingestion-triggered re-evaluation hooks | Platform Team | Complete |
| Tighten chunk size invariants | ML Team | Complete |
| Introduce drift monitoring at retrieval layer | SRE | Complete |

## Preventive Measures

- [ ] Change gates for ingestion pipelines
- [ ] - [x] Canary embedding evaluation
- [ ] - [x] Mandatory rollback plans for semantic index updates
- [ ] - [x] Real-time drift monitoring dashboard

- [ ] ## Key Insight

- [ ] > The system did not fail because the model hallucinated. It failed because semantic invariants were not enforced at ingestion time. This was a **system design oversight**, not a model defect.

- [ ] ## Lessons Learned

- [ ] 1. Treat embeddings as versioned artifacts with drift SLAs
- [ ] 2. Ingestion changes require same rigor as model deployments
- [ ] 3. Graceful degradation proved critical - no patient harm occurred
