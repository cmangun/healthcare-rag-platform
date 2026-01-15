# Prompt Lineage

> Prompts are first-class governed assets.
>
> ## Why Prompt Versioning Matters
>
> In regulated environments, prompts are not just engineering - they are policy. A prompt change can:
>
> - Alter clinical recommendations
> - - Change regulatory interpretations
>   - - Introduce new failure modes
>     - - Affect audit trail completeness
>      
>       - Every prompt change must be **tracked, approved, and reversible**.
>      
>       - ---
>
> ## Current Production Prompts
>
> ### PROMPT-RAG-SEC-004 (Primary Healthcare RAG)
>
> | Field | Value |
> |-------|-------|
> | Template ID | PROMPT-RAG-SEC-004 |
> | Version | v1.7 |
> | Status | PRODUCTION |
> | Effective Date | 2025-02-01 |
> | Change Reason | Added regulatory grounding instructions |
> | Approved By | Compliance Lead |
> | Next Review | 2025-04-01 |
>
> ### Model Configuration
>
> | Parameter | Value |
> |-----------|-------|
> | Provider | OpenAI |
> | Model | gpt-4-turbo-2024-04-09 |
> | Temperature | 0.2 |
> | Max Tokens | 2048 |
> | Context Window | 128,000 |
> | Deployment Tier | Non-Patient Facing |
>
> ---
>
> ## Version History
>
> | Version | Date | Change | Approved By |
> |---------|------|--------|-------------|
> | v1.7 | 2025-02-01 | Added regulatory grounding | Compliance Lead |
> | v1.6 | 2025-01-15 | Improved citation format | ML Lead |
> | v1.5 | 2025-01-02 | Added confidence scoring | ML Lead |
> | v1.4 | 2024-12-15 | Reduced hallucination | Compliance Lead |
> | v1.3 | 2024-12-01 | Initial production release | VP Engineering |
>
> ---
>
> ## Prompt Change Process
>
> ### 1. Proposal
>
> Required fields:
> - Proposal ID
> - - Current version
>   - - Proposed version
>     - - Change description
>       - - Rationale
>         - - Risk assessment
>           - - Testing plan
>            
>             - ### 2. Review
>            
>             - | Reviewer | Role | Required |
>             - |----------|------|----------|
>             - | ML Lead | Technical | Yes |
> | Compliance Lead | Regulatory | Yes |
> | Legal | Legal review | Conditional |
> | VP Engineering | Final approval | Conditional |
>
> ### 3. Testing
>
> - Unit tests with edge cases
> - - A/B test with 5% traffic for 48 hours
>   - - Manual review of 100 responses
>    
>     - ### 4. Deployment
>    
>     - - Canary deployment strategy
>       - - Initial traffic: 5%
>         - - Duration: 48 hours
>           - - Success criteria defined
>             - - Rollback triggers defined
>              
>               - ---
>
> ## Audit Trail Requirements
>
> Every prompt invocation logs:
>
> - Trace ID (UUID)
> - - Timestamp (ISO 8601)
>   - - Prompt template ID and version
>     - - Prompt hash (SHA-256)
>       - - Model provider and version
>         - - Output hash
>           - - Token count
>             - - Confidence score
>              
>               - ---
>
> ## Emergency Rollback
>
> Maximum time from decision to rollback complete: **5 minutes**
>
> Rollback command:
> ```
> ./prompt-manager.sh rollback --template=PROMPT-RAG-SEC-004 --target-version=v1.6
> ```
>
> ---
>
> ## Related Documents
>
> - [AUDIT-TRACEABILITY.md](./AUDIT-TRACEABILITY.md) - Full audit chain
> - - [VALIDATION-GATES.md](./VALIDATION-GATES.md) - Deployment gates
>   - - [PLAYBOOK-REGULATED-AI.md](./PLAYBOOK-REGULATED-AI.md) - Operational playbook
