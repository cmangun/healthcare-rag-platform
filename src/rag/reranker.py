"""
Cross-Encoder Reranker

Provides precision reranking of retrieved documents using
cross-encoder models for healthcare RAG.
"""

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class RerankResult:
    """Result of reranking operation."""
    
    doc_id: str
    content: str
    original_score: float
    rerank_score: float
    final_rank: int


class CrossEncoderReranker:
    """
    Cross-encoder reranker for precision retrieval.
    
    Uses a cross-encoder model to score query-document pairs
    for more accurate relevance ranking.
    """
    
    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        batch_size: int = 32,
        max_length: int = 512,
    ):
        """
        Initialize reranker.
        
        Args:
            model_name: Cross-encoder model name.
            batch_size: Batch size for scoring.
            max_length: Maximum sequence length.
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self.max_length = max_length
        
        self._model: Any = None
    
    def rerank(
        self,
        query: str,
        documents: list[dict[str, Any]],
        top_k: int | None = None,
    ) -> list[RerankResult]:
        """
        Rerank documents using cross-encoder.
        
        Args:
            query: Query text.
            documents: List of documents with 'id', 'content', 'score'.
            top_k: Number of documents to return.
            
        Returns:
            Reranked documents.
        """
        if not documents:
            return []
        
        top_k = top_k or len(documents)
        
        # Score query-document pairs
        pairs = [(query, doc["content"]) for doc in documents]
        scores = self._score_pairs(pairs)
        
        # Create results with both scores
        results = []
        for doc, rerank_score in zip(documents, scores):
            results.append(
                RerankResult(
                    doc_id=doc["id"],
                    content=doc["content"],
                    original_score=doc.get("score", 0.0),
                    rerank_score=rerank_score,
                    final_rank=0,  # Will be set after sorting
                )
            )
        
        # Sort by rerank score
        results.sort(key=lambda x: x.rerank_score, reverse=True)
        
        # Set final ranks
        for i, result in enumerate(results[:top_k]):
            result.final_rank = i + 1
        
        return results[:top_k]
    
    def _score_pairs(
        self,
        pairs: list[tuple[str, str]],
    ) -> list[float]:
        """Score query-document pairs."""
        try:
            from sentence_transformers import CrossEncoder
            
            if self._model is None:
                self._model = CrossEncoder(
                    self.model_name,
                    max_length=self.max_length,
                )
            
            scores = self._model.predict(
                pairs,
                batch_size=self.batch_size,
                show_progress_bar=False,
            )
            
            return list(scores)
            
        except ImportError:
            logger.warning("sentence-transformers not installed, using fallback")
            return self._score_fallback(pairs)
    
    def _score_fallback(
        self,
        pairs: list[tuple[str, str]],
    ) -> list[float]:
        """Fallback scoring using term overlap."""
        scores = []
        
        for query, doc in pairs:
            query_terms = set(query.lower().split())
            doc_terms = set(doc.lower().split())
            
            # Jaccard similarity
            intersection = len(query_terms & doc_terms)
            union = len(query_terms | doc_terms)
            
            score = intersection / union if union > 0 else 0.0
            scores.append(score)
        
        return scores
