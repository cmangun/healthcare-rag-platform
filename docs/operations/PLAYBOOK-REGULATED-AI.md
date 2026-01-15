# Playbook: How We Build Regulated AI

> AI fails socially before it fails technically.
>
> This playbook codifies our approach to deploying AI systems in regulated healthcare environments.
>
> ---
>
> ## Core Principles
>
> ### 1. Safety is not a feature. It's the architecture.
>
> If safety can be turned off, it will be turned off. Safety must be **structural**, not configurational.
>
> ### 2. Every AI decision needs a deterministic fallback.
>
> | AI Confidence | Action |
> |---------------|--------|
> | High | AI answer |
> | Low | Retrieval-only + human review |
> | Retrieval Failed | Cached answer + escalation |
> | Everything Failed | Static response + immediate alert |
>
> **No silent failures. Ever.**
>
> ### 3. Instrument first, optimize later.
>
> You cannot improve what you cannot measure. Telemetry is not overhead. It's oxygen.
>
> ---
>
> ## Phase 1: Define Safety Boundaries
>
> ### Surface Classification
>
> | Surface Type | Definition | Allowable Failure Modes |
> |--------------|------------|------------------------|
> | Patient-facing | Directly influences patient care | **None** - human-in-loop required |
> | Clinician-facing | Supports clinical decisions | Low-confidence flagging |
> | Administrative | Back-office operations | Graceful degradation |
> | Internal | Developer/analyst tools | Standard retry logic |
>
> ---
>
> ## Phase 2: Design for Degradation
>
> Every system component must have a defined degradation path:
>
> - FULL_AI: RAG + LLM generation
> - - RETRIEVAL_ONLY: Return docs, no generation
>   - - CACHED_RESPONSE: Pre-computed for common queries
>     - - STATIC_FALLBACK: Hardcoded safe response
>       - - HUMAN_ESCALATION: Direct to support queue
>        
>         - ### Degradation Triggers
>        
>         - | Trigger | Threshold | Action |
>         - |---------|-----------|--------|
>         - | Confidence below threshold | < 0.65 | Drop to retrieval-only |
> | Latency exceeded | > 5s | Return cached + async complete |
> | Error rate spike | > 5% (1 min window) | Circuit breaker open |
> | Dependency failure | Any critical path | Cached fallback |
> | Cost anomaly | > 2x baseline | Rate limit + alert |
>
> ---
>
> ## Phase 3: Instrument First
>
> ### Required Telemetry (Non-Negotiable)
>
> - **Latency**: P50, P95, P99
> - - **Quality**: Confidence score, retrieval relevance
>   - - **Cost**: Tokens in/out, cost USD
>     - - **Audit**: Trace ID, document versions, model version
>      
>       - ### Alert Hierarchy
>      
>       - | Level | Response Time | Escalation |
>       - |-------|---------------|------------|
>       - | P1 - Patient Safety | Immediate | VP Eng + Legal |
> | P2 - Service Down | 15 min | On-call engineer |
> | P3 - Degraded | 1 hour | Team lead |
> | P4 - Warning | Next business day | Ticket created |
>
> ---
>
> ## Phase 4: Ship with Kill Switches
>
> ### Required Kill Switches
>
> - ai_generation_enabled - Can disable all LLM calls
> - - retrieval_enabled - Can disable vector search
>   - - guardrails_enabled - Should NEVER be disabled in prod
>     - - human_review_bypass - Emergency only, audit logged
>       - - model_version_override - Pin to specific model version
>        
>         - **Maximum time from decision to rollback complete: 5 minutes.**
>        
>         - ---
>
> ## Organizational Guidance
>
> | Centralize | Distribute |
> |------------|------------|
> | Safety standards | Model training |
> | Audit requirements | Feature development |
> | Deployment gates | Domain expertise |
> | Incident response | Day-to-day operations |
> | Cost governance | Performance optimization |
>
> **Do NOT centralize AI ownership in a single team. Distribute execution, centralize governance.**
>
> ---
>
> ## What This Achieves
>
> With this playbook, you are no longer evaluated as:
>
> > "A strong AI engineer"
> >
> > You are evaluated as:
> >
> > > "The person we trust when the system fails at 2am under audit."
