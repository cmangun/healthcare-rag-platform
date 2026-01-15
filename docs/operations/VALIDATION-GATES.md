# Validation Gates

Production deployment gates for the Healthcare RAG Platform. **No gate pass = No deploy.**

## Pre-Deployment Gates

| Gate | Description | Pass Criteria | Automated |
|------|-------------|---------------|-----------|
| Data Integrity | Source documents verified | 100% checksum match | Yes |
| Retrieval Quality | Precision@5 on test set | ≥ 0.85 | Yes |
| Hallucination Rate | Manual review sample (n=50) | ≤ 2% | No |
| Latency | P95 response time | ≤ 2.0s | Yes |
| Cost | Cost per answer | ≤ $0.012 | Yes |
| PHI Detection | PHI leak test suite | 0 leaks | Yes |
| Guardrail Coverage | All safety checks active | 100% | Yes |

## Gate Enforcement

```yaml
# .github/workflows/validation-gates.yml
validation_gates:
  data_integrity:
    threshold: 1.0  # 100%
    blocking: true

  retrieval_precision:
    threshold: 0.85
    blocking: true

  p95_latency_ms:
    threshold: 2000
    blocking: true

  cost_per_query:
    threshold: 0.012
    blocking: true

  phi_leaks:
    threshold: 0
    blocking: true
```

## Continuous Monitoring Gates

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| Embedding Drift | >3% | >6% | Re-index triggered |
| Confidence Scores | <0.80 avg | <0.70 avg | Human review fallback |
| Error Rate | >1% | >3% | Circuit breaker |
| Latency P99 | >3s | >5s | Auto-scale / alert |

## Manual Review Requirements

The following require human sign-off before production:

- [ ] Prompt template changes reviewed by Compliance Lead
- [ ] - [ ] Model version updates approved by ML Lead
- [ ] - [ ] Document source additions verified by Domain Expert
- [ ] - [ ] Configuration changes reviewed by SRE

- [ ] ## Gate Bypass Protocol

- [ ] **Emergency bypass requires:**
- [ ] 1. Written justification from Engineering Lead
- [ ] 2. Time-boxed exception (max 24 hours)
- [ ] 3. Incident ticket created
- [ ] 4. Post-deployment review scheduled

- [ ] > No silent bypasses. Every exception is logged and reviewed.
