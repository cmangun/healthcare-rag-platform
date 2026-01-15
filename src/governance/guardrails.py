"""
Healthcare RAG Guardrails

Provides safety guardrails for healthcare RAG including:
- Content filtering
- Hallucination detection
- Medical accuracy validation
- Response quality gates
"""

import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class GuardrailResult:
    """Result of guardrail check."""
    
    passed: bool
    guardrail_name: str
    reason: str
    severity: str = "warning"  # "info", "warning", "critical"
    details: dict[str, Any] | None = None


class HealthcareGuardrails:
    """
    Guardrails for healthcare RAG responses.
    
    Implements safety checks:
    - Medical advice disclaimers
    - Unsupported claim detection
    - Harmful content filtering
    - Confidence thresholds
    """
    
    # Medical terms that require careful handling
    SENSITIVE_MEDICAL_TERMS = {
        "diagnosis", "diagnose", "prescribed", "prescription",
        "treatment", "cure", "dosage", "medication",
        "surgery", "procedure", "terminal", "fatal",
        "overdose", "suicide", "self-harm",
    }
    
    # Phrases that suggest medical advice
    ADVICE_PATTERNS = [
        r"you should (take|stop|start|increase|decrease)",
        r"i recommend (taking|starting|stopping)",
        r"(take|use) \d+ (mg|ml|tablets|pills)",
        r"(increase|decrease|change) your (dose|dosage|medication)",
    ]
    
    # Required disclaimer patterns
    DISCLAIMER_PATTERNS = [
        r"consult.*(doctor|physician|healthcare|provider)",
        r"not (medical|professional) advice",
        r"speak (to|with).*(healthcare|medical|doctor)",
    ]
    
    def __init__(
        self,
        require_disclaimer: bool = True,
        min_confidence: float = 0.7,
        max_sensitive_terms: int = 5,
    ):
        """
        Initialize guardrails.
        
        Args:
            require_disclaimer: Require medical disclaimers.
            min_confidence: Minimum confidence for responses.
            max_sensitive_terms: Max sensitive terms without disclaimer.
        """
        self.require_disclaimer = require_disclaimer
        self.min_confidence = min_confidence
        self.max_sensitive_terms = max_sensitive_terms
    
    def check_response(
        self,
        response: str,
        contexts: list[str] | None = None,
        confidence: float | None = None,
    ) -> list[GuardrailResult]:
        """
        Run all guardrail checks on a response.
        
        Args:
            response: Generated response text.
            contexts: Source contexts (for grounding check).
            confidence: Response confidence score.
            
        Returns:
            List of guardrail results.
        """
        results = []
        
        # Check for sensitive medical content
        results.append(self._check_sensitive_content(response))
        
        # Check for medical advice patterns
        results.append(self._check_advice_patterns(response))
        
        # Check for disclaimer when needed
        results.append(self._check_disclaimer(response))
        
        # Check grounding in contexts
        if contexts:
            results.append(self._check_grounding(response, contexts))
        
        # Check confidence threshold
        if confidence is not None:
            results.append(self._check_confidence(confidence))
        
        # Check response quality
        results.append(self._check_response_quality(response))
        
        return results
    
    def _check_sensitive_content(self, response: str) -> GuardrailResult:
        """Check for sensitive medical terms."""
        response_lower = response.lower()
        found_terms = []
        
        for term in self.SENSITIVE_MEDICAL_TERMS:
            if term in response_lower:
                found_terms.append(term)
        
        if len(found_terms) > self.max_sensitive_terms:
            return GuardrailResult(
                passed=False,
                guardrail_name="sensitive_content",
                reason=f"Response contains {len(found_terms)} sensitive medical terms",
                severity="warning",
                details={"terms": found_terms},
            )
        
        return GuardrailResult(
            passed=True,
            guardrail_name="sensitive_content",
            reason="Sensitive content within limits",
            severity="info",
            details={"terms": found_terms},
        )
    
    def _check_advice_patterns(self, response: str) -> GuardrailResult:
        """Check for medical advice patterns."""
        response_lower = response.lower()
        found_patterns = []
        
        for pattern in self.ADVICE_PATTERNS:
            matches = re.findall(pattern, response_lower)
            if matches:
                found_patterns.extend(matches)
        
        if found_patterns:
            return GuardrailResult(
                passed=False,
                guardrail_name="medical_advice",
                reason="Response contains direct medical advice patterns",
                severity="critical",
                details={"patterns": found_patterns[:5]},
            )
        
        return GuardrailResult(
            passed=True,
            guardrail_name="medical_advice",
            reason="No direct medical advice detected",
            severity="info",
        )
    
    def _check_disclaimer(self, response: str) -> GuardrailResult:
        """Check for required medical disclaimer."""
        if not self.require_disclaimer:
            return GuardrailResult(
                passed=True,
                guardrail_name="disclaimer",
                reason="Disclaimer not required",
                severity="info",
            )
        
        response_lower = response.lower()
        
        # Check if response contains medical terms
        has_medical_content = any(
            term in response_lower
            for term in self.SENSITIVE_MEDICAL_TERMS
        )
        
        if not has_medical_content:
            return GuardrailResult(
                passed=True,
                guardrail_name="disclaimer",
                reason="No medical content, disclaimer not needed",
                severity="info",
            )
        
        # Check for disclaimer
        has_disclaimer = any(
            re.search(pattern, response_lower)
            for pattern in self.DISCLAIMER_PATTERNS
        )
        
        if has_disclaimer:
            return GuardrailResult(
                passed=True,
                guardrail_name="disclaimer",
                reason="Medical disclaimer present",
                severity="info",
            )
        
        return GuardrailResult(
            passed=False,
            guardrail_name="disclaimer",
            reason="Medical content present without disclaimer",
            severity="warning",
        )
    
    def _check_grounding(
        self,
        response: str,
        contexts: list[str],
    ) -> GuardrailResult:
        """Check if response is grounded in contexts."""
        if not contexts:
            return GuardrailResult(
                passed=False,
                guardrail_name="grounding",
                reason="No contexts provided for grounding check",
                severity="warning",
            )
        
        response_sentences = response.split('.')
        context_text = ' '.join(contexts).lower()
        
        grounded_sentences = 0
        total_sentences = 0
        
        for sentence in response_sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue
            
            total_sentences += 1
            
            # Check if key terms from sentence appear in context
            sentence_terms = set(sentence.lower().split())
            # Remove common words
            sentence_terms = {
                t for t in sentence_terms
                if len(t) > 3 and t not in {'this', 'that', 'with', 'from'}
            }
            
            if sentence_terms:
                overlap = sum(1 for t in sentence_terms if t in context_text)
                if overlap / len(sentence_terms) > 0.3:
                    grounded_sentences += 1
        
        if total_sentences == 0:
            grounding_ratio = 1.0
        else:
            grounding_ratio = grounded_sentences / total_sentences
        
        passed = grounding_ratio >= 0.5
        
        return GuardrailResult(
            passed=passed,
            guardrail_name="grounding",
            reason=f"{grounding_ratio:.0%} of sentences grounded in context",
            severity="warning" if not passed else "info",
            details={
                "grounded_sentences": grounded_sentences,
                "total_sentences": total_sentences,
                "grounding_ratio": grounding_ratio,
            },
        )
    
    def _check_confidence(self, confidence: float) -> GuardrailResult:
        """Check confidence threshold."""
        passed = confidence >= self.min_confidence
        
        return GuardrailResult(
            passed=passed,
            guardrail_name="confidence",
            reason=f"Confidence {confidence:.2f} {'meets' if passed else 'below'} threshold {self.min_confidence}",
            severity="warning" if not passed else "info",
            details={"confidence": confidence, "threshold": self.min_confidence},
        )
    
    def _check_response_quality(self, response: str) -> GuardrailResult:
        """Check basic response quality."""
        issues = []
        
        # Check length
        word_count = len(response.split())
        if word_count < 10:
            issues.append("Response too short")
        elif word_count > 1000:
            issues.append("Response excessively long")
        
        # Check for incomplete sentences
        if response.strip() and not response.strip()[-1] in '.!?':
            issues.append("Response may be incomplete")
        
        # Check for repetition
        sentences = response.split('.')
        if len(sentences) > 2:
            unique_starts = set(s.strip()[:20] for s in sentences if s.strip())
            if len(unique_starts) < len(sentences) * 0.5:
                issues.append("Response contains repetitive content")
        
        passed = len(issues) == 0
        
        return GuardrailResult(
            passed=passed,
            guardrail_name="response_quality",
            reason="Response quality check " + ("passed" if passed else f"failed: {', '.join(issues)}"),
            severity="info" if passed else "warning",
            details={"issues": issues, "word_count": word_count},
        )
    
    def enforce(
        self,
        response: str,
        contexts: list[str] | None = None,
        confidence: float | None = None,
        block_on_critical: bool = True,
    ) -> tuple[bool, str, list[GuardrailResult]]:
        """
        Enforce guardrails and optionally block response.
        
        Args:
            response: Generated response.
            contexts: Source contexts.
            confidence: Confidence score.
            block_on_critical: Block response on critical failures.
            
        Returns:
            Tuple of (allowed, modified_response, results).
        """
        results = self.check_response(response, contexts, confidence)
        
        critical_failures = [
            r for r in results
            if not r.passed and r.severity == "critical"
        ]
        
        if critical_failures and block_on_critical:
            blocked_response = (
                "I apologize, but I cannot provide a response to this query "
                "as it may require medical advice. Please consult with a "
                "qualified healthcare provider for personalized guidance."
            )
            return False, blocked_response, results
        
        # Add disclaimer if needed
        disclaimer_result = next(
            (r for r in results if r.guardrail_name == "disclaimer"),
            None
        )
        
        if disclaimer_result and not disclaimer_result.passed:
            response = response + (
                "\n\n*Disclaimer: This information is for educational purposes "
                "only and should not be considered medical advice. Please "
                "consult with a healthcare provider for personalized guidance.*"
            )
        
        return True, response, results
