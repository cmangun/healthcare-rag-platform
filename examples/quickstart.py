"""
Healthcare RAG Platform - Quickstart Example

This example demonstrates:
1. PHI detection and anonymization
2. Healthcare guardrails
3. RAG evaluation metrics
4. Audit logging

Requirements:
    pip install -e .

For full documentation, see: https://github.com/cmangun/healthcare-rag-platform
"""

from src.governance.phi_detector import PHIDetector
from src.governance.guardrails import HealthcareGuardrails
from src.rag.evaluation import RAGEvaluator
from src.governance.audit_logger import AuditLogger, AuditConfig, ComplianceMode


def demo_phi_detection():
    """Demonstrate PHI detection and anonymization."""
    print("\n" + "=" * 60)
    print("1. PHI DETECTION")
    print("=" * 60)
    
    detector = PHIDetector()
    
    clinical_note = """
    Patient John Smith (DOB: 03/15/1985, MRN: 12345678) was admitted on 01/10/2024.
    Contact: john.smith@email.com, (555) 123-4567
    SSN: 123-45-6789
    Diagnosis: Type 2 Diabetes Mellitus
    """
    
    result = detector.detect(clinical_note)
    
    print(f"\nPHI detected: {result.phi_detected}")
    print(f"Risk level: {result.risk_level}")
    print(f"\nIdentified PHI ({len(result.identifiers)} items):")
    for entity in result.identifiers:
        print(f"  - {entity.phi_type.value}: '{entity.value}'")
    
    anonymized = detector.anonymize(clinical_note, strategy="replace")
    print("\nAnonymized text:")
    print(anonymized)


def demo_guardrails():
    """Demonstrate healthcare guardrails."""
    print("\n" + "=" * 60)
    print("2. HEALTHCARE GUARDRAILS")
    print("=" * 60)
    
    guardrails = HealthcareGuardrails(
        require_disclaimer=True,
        min_confidence=0.7,
    )
    
    query = "What medication should I take for chest pain?"
    response = "You should take 325mg of aspirin immediately."
    
    result = guardrails.check_response(
        response=response,
        query=query,
        context_relevance_score=0.4
    )
    
    print(f"\nQuery: {query}")
    print(f"Response: {response}")
    print(f"\nGuardrail passed: {result.passed}")
    print(f"Reason: {result.reason}")
    print(f"Severity: {result.severity}")


def demo_evaluation():
    """Demonstrate RAG evaluation."""
    print("\n" + "=" * 60)
    print("3. RAG EVALUATION")
    print("=" * 60)
    
    evaluator = RAGEvaluator(use_llm_eval=False)
    
    query = "What are the contraindications for metformin?"
    answer = "Metformin is contraindicated in patients with severe renal impairment."
    contexts = [
        "Metformin contraindications include severe renal impairment (eGFR < 30).",
    ]
    
    report = evaluator.evaluate(
        query=query,
        answer=answer,
        contexts=contexts,
    )
    
    print(f"\nQuery: {query}")
    print(f"Answer: {answer}")
    print(f"\nOverall Score: {report.overall_score:.2f}")
    print("Metrics:")
    for metric in report.metrics:
        print(f"  - {metric.metric_name}: {metric.score:.2f}")


def demo_audit_logging():
    """Demonstrate audit logging."""
    print("\n" + "=" * 60)
    print("4. AUDIT LOGGING (FDA 21 CFR Part 11)")
    print("=" * 60)
    
    config = AuditConfig(
        compliance_mode=ComplianceMode.FDA_21_CFR_PART_11,
        enable_hash_chain=True,
    )
    
    logger = AuditLogger(config)
    
    entry = logger.log_event(
        action="clinical_query",
        user_id="clinician_001",
        details={
            "query": "metformin contraindications",
            "phi_detected": False,
            "confidence": 0.85,
        }
    )
    
    print(f"\nAudit Entry ID: {entry.entry_id}")
    print(f"Timestamp: {entry.timestamp}")
    print(f"Hash: {entry.hash[:32]}...")
    print(f"Compliance Mode: {entry.compliance_mode.value}")
    
    is_valid = logger.verify_chain()
    print(f"\nAudit chain integrity: {'✓ Valid' if is_valid else '✗ Invalid'}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("HEALTHCARE RAG PLATFORM - QUICKSTART DEMO")
    print("=" * 60)
    
    demo_phi_detection()
    demo_guardrails()
    demo_evaluation()
    demo_audit_logging()
    
    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)
    print("\nFor more examples, see:")
    print("  - https://github.com/cmangun/healthcare-rag-platform")
    print("  - https://github.com/cmangun/mlops-healthcare-platform")
    print("  - https://github.com/cmangun/clinical-nlp-pipeline")
