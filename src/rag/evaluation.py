"""
RAG Evaluation Framework

Provides comprehensive evaluation metrics for healthcare RAG systems
including faithfulness, relevance, and answer correctness.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """Result of RAG evaluation."""
    
    metric_name: str
    score: float
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class RAGEvaluationReport:
    """Complete RAG evaluation report."""
    
    query: str
    answer: str
    contexts: list[str]
    metrics: list[EvaluationResult]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def overall_score(self) -> float:
        """Calculate weighted overall score."""
        if not self.metrics:
            return 0.0
        return np.mean([m.score for m in self.metrics])
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query": self.query,
            "answer": self.answer,
            "contexts": self.contexts,
            "overall_score": self.overall_score,
            "metrics": [
                {
                    "name": m.metric_name,
                    "score": m.score,
                    "details": m.details,
                }
                for m in self.metrics
            ],
            "timestamp": self.timestamp.isoformat(),
        }


class RAGEvaluator:
    """
    RAG evaluation framework for healthcare applications.
    
    Implements metrics inspired by RAGAS:
    - Faithfulness: Is the answer grounded in the context?
    - Answer Relevance: Does the answer address the query?
    - Context Precision: Are retrieved contexts relevant?
    - Context Recall: Do contexts contain needed information?
    """
    
    def __init__(
        self,
        use_llm_eval: bool = True,
        embedding_model: str = "text-embedding-3-small",
    ):
        """
        Initialize evaluator.
        
        Args:
            use_llm_eval: Whether to use LLM for evaluation.
            embedding_model: Model for embedding-based metrics.
        """
        self.use_llm_eval = use_llm_eval
        self.embedding_model = embedding_model
    
    def evaluate(
        self,
        query: str,
        answer: str,
        contexts: list[str],
        ground_truth: str | None = None,
    ) -> RAGEvaluationReport:
        """
        Evaluate a RAG response.
        
        Args:
            query: Original query.
            answer: Generated answer.
            contexts: Retrieved contexts used.
            ground_truth: Expected answer (optional).
            
        Returns:
            RAGEvaluationReport with all metrics.
        """
        metrics = []
        
        # Faithfulness: Is answer grounded in context?
        faithfulness = self._evaluate_faithfulness(answer, contexts)
        metrics.append(faithfulness)
        
        # Answer relevance: Does answer address query?
        relevance = self._evaluate_answer_relevance(query, answer)
        metrics.append(relevance)
        
        # Context precision: Are contexts relevant to query?
        precision = self._evaluate_context_precision(query, contexts)
        metrics.append(precision)
        
        # Context utilization: How much context is used?
        utilization = self._evaluate_context_utilization(answer, contexts)
        metrics.append(utilization)
        
        # Answer correctness (if ground truth provided)
        if ground_truth:
            correctness = self._evaluate_correctness(answer, ground_truth)
            metrics.append(correctness)
        
        return RAGEvaluationReport(
            query=query,
            answer=answer,
            contexts=contexts,
            metrics=metrics,
        )
    
    def _evaluate_faithfulness(
        self,
        answer: str,
        contexts: list[str],
    ) -> EvaluationResult:
        """
        Evaluate if answer is faithful to contexts.
        
        Measures whether claims in the answer can be traced
        to the provided contexts.
        """
        if not contexts:
            return EvaluationResult(
                metric_name="faithfulness",
                score=0.0,
                details={"reason": "No contexts provided"},
            )
        
        # Simple heuristic: check term overlap
        answer_terms = set(answer.lower().split())
        context_terms = set()
        for ctx in contexts:
            context_terms.update(ctx.lower().split())
        
        # Proportion of answer terms found in context
        overlap = answer_terms & context_terms
        score = len(overlap) / len(answer_terms) if answer_terms else 0.0
        
        return EvaluationResult(
            metric_name="faithfulness",
            score=min(score * 1.5, 1.0),  # Scale up slightly
            details={
                "answer_terms": len(answer_terms),
                "context_terms": len(context_terms),
                "overlap": len(overlap),
            },
        )
    
    def _evaluate_answer_relevance(
        self,
        query: str,
        answer: str,
    ) -> EvaluationResult:
        """
        Evaluate if answer is relevant to query.
        
        Measures semantic similarity between query and answer.
        """
        query_terms = set(query.lower().split())
        answer_terms = set(answer.lower().split())
        
        # Jaccard similarity as proxy for relevance
        intersection = len(query_terms & answer_terms)
        union = len(query_terms | answer_terms)
        
        score = intersection / union if union > 0 else 0.0
        
        # Boost score if answer is substantive
        if len(answer.split()) > 20:
            score = min(score + 0.2, 1.0)
        
        return EvaluationResult(
            metric_name="answer_relevance",
            score=score,
            details={
                "query_terms": len(query_terms),
                "answer_terms": len(answer_terms),
                "overlap": intersection,
            },
        )
    
    def _evaluate_context_precision(
        self,
        query: str,
        contexts: list[str],
    ) -> EvaluationResult:
        """
        Evaluate precision of retrieved contexts.
        
        Measures how relevant the contexts are to the query.
        """
        if not contexts:
            return EvaluationResult(
                metric_name="context_precision",
                score=0.0,
                details={"reason": "No contexts"},
            )
        
        query_terms = set(query.lower().split())
        
        # Score each context
        scores = []
        for ctx in contexts:
            ctx_terms = set(ctx.lower().split())
            overlap = len(query_terms & ctx_terms)
            score = overlap / len(query_terms) if query_terms else 0.0
            scores.append(score)
        
        # Weight by position (earlier contexts should be more relevant)
        weights = [1 / (i + 1) for i in range(len(scores))]
        weighted_score = np.average(scores, weights=weights)
        
        return EvaluationResult(
            metric_name="context_precision",
            score=weighted_score,
            details={
                "context_scores": scores,
                "num_contexts": len(contexts),
            },
        )
    
    def _evaluate_context_utilization(
        self,
        answer: str,
        contexts: list[str],
    ) -> EvaluationResult:
        """
        Evaluate how much of the context is utilized.
        
        Measures information extraction efficiency.
        """
        if not contexts:
            return EvaluationResult(
                metric_name="context_utilization",
                score=0.0,
                details={"reason": "No contexts"},
            )
        
        answer_terms = set(answer.lower().split())
        
        # Track which context terms appear in answer
        utilized_terms = 0
        total_terms = 0
        
        for ctx in contexts:
            ctx_terms = set(ctx.lower().split())
            total_terms += len(ctx_terms)
            utilized_terms += len(ctx_terms & answer_terms)
        
        score = utilized_terms / total_terms if total_terms > 0 else 0.0
        
        return EvaluationResult(
            metric_name="context_utilization",
            score=score,
            details={
                "utilized_terms": utilized_terms,
                "total_context_terms": total_terms,
            },
        )
    
    def _evaluate_correctness(
        self,
        answer: str,
        ground_truth: str,
    ) -> EvaluationResult:
        """
        Evaluate answer correctness against ground truth.
        """
        answer_terms = set(answer.lower().split())
        truth_terms = set(ground_truth.lower().split())
        
        # F1-like score
        overlap = len(answer_terms & truth_terms)
        precision = overlap / len(answer_terms) if answer_terms else 0.0
        recall = overlap / len(truth_terms) if truth_terms else 0.0
        
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0 else 0.0
        )
        
        return EvaluationResult(
            metric_name="correctness",
            score=f1,
            details={
                "precision": precision,
                "recall": recall,
                "f1": f1,
            },
        )
    
    def batch_evaluate(
        self,
        examples: list[dict[str, Any]],
    ) -> dict[str, float]:
        """
        Evaluate a batch of examples.
        
        Args:
            examples: List of dicts with 'query', 'answer', 'contexts'.
            
        Returns:
            Aggregated metrics.
        """
        all_metrics: dict[str, list[float]] = {}
        
        for example in examples:
            report = self.evaluate(
                query=example["query"],
                answer=example["answer"],
                contexts=example["contexts"],
                ground_truth=example.get("ground_truth"),
            )
            
            for metric in report.metrics:
                if metric.metric_name not in all_metrics:
                    all_metrics[metric.metric_name] = []
                all_metrics[metric.metric_name].append(metric.score)
        
        # Aggregate
        return {
            name: np.mean(scores)
            for name, scores in all_metrics.items()
        }
