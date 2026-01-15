# Audit Traceability Framework

> Every AI decision in this system is traceable from user query to final output.
>
> ## Traceability Chain
>
> ```
> User Query
>   → Query Hash (SHA-256)
>     → Retrieved Document IDs
>       → Document Versions
>         → Embedding Hashes
>           → Prompt Template Version
>             → Model Version
>               → Output Hash
>                 → Reviewer ID (if applicable)
> ```
>
> Every arrow represents a loggable, immutable event stored in the audit trail.
>
> ## Audit Event Schema
>
> | Field | Type | Description |
> |-------|------|-------------|
> | `event_id` | UUID | Unique identifier for this audit event |
> | `timestamp` | ISO8601 | Event timestamp (UTC) |
> | `query_hash` | SHA-256 | Hash of sanitized user query |
> | `session_id` | UUID | User session identifier |
> | `retrieved_docs` | Array | Document IDs with version hashes |
> | `embedding_hash` | SHA-256 | Hash of query embedding vector |
> | `prompt_template_id` | String | Versioned prompt template identifier |
> | `model_config` | Object | Model name, version, parameters |
> | `output_hash` | SHA-256 | Hash of generated response |
> | `confidence_score` | Float | Model confidence (0.0-1.0) |
> | `review_status` | Enum | `auto_approved`, `pending_review`, `human_approved` |
> | `reviewer_id` | String | Reviewer identifier (if applicable) |
>
> ## Retention Policy
>
> | Data Category | Retention Period | Justification |
> |---------------|-----------------|---------------|
> | Query hashes | 7 years | HIPAA compliance |
> | Document lineage | 7 years | Regulatory audit |
> | Model outputs | 3 years | Quality assurance |
> | Session data | 90 days | Operational debugging |
>
> ## Query Reconstruction
>
> For any audit inquiry, the system can reconstruct:
>
> 1. **What was asked** - Via query hash lookup
> 2. 2. **What was retrieved** - Via document ID chain
>    3. 3. **How it was processed** - Via prompt template version
>       4. 4. **What was generated** - Via output hash verification
>          5. 5. **Who approved it** - Via reviewer chain
>            
>             6. ## Compliance Mapping
>            
>             7. | Requirement | Implementation |
>             8. |-------------|----------------|
>             9. | HIPAA 164.312(b) | Audit controls via event logging |
> | HIPAA 164.312(c) | Integrity via hash verification |
> | HIPAA 164.312(e) | Transmission security via TLS 1.3 |
> | FDA 21 CFR 11.10(e) | Audit trail with timestamps |
>
> ---
>
> *Document Version: 1.0 | Last Updated: 2025-01-15*
