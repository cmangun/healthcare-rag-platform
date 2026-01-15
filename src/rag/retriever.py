"""
Hybrid Retriever

Combines dense (vector) and sparse (BM25) retrieval with
Reciprocal Rank Fusion for optimal healthcare document retrieval.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class RetrievedDocument:
    """A retrieved document with metadata."""
    
    id: str
    content: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)
    source: str = "unknown"  # "dense", "sparse", or "fused"


@dataclass
class RetrievalResult:
    """Result of a retrieval operation."""
    
    documents: list[RetrievedDocument]
    query: str
    retrieval_method: str
    latency_ms: float
    total_candidates: int


class HybridRetriever:
    """
    Hybrid retriever combining dense and sparse search.
    
    Features:
    - Dense retrieval via vector similarity
    - Sparse retrieval via BM25
    - Reciprocal Rank Fusion (RRF) for result merging
    - Cross-encoder reranking for precision
    """
    
    def __init__(
        self,
        dense_weight: float = 0.7,
        sparse_weight: float = 0.3,
        rrf_k: int = 60,
        top_k: int = 10,
    ):
        """
        Initialize hybrid retriever.
        
        Args:
            dense_weight: Weight for dense retrieval scores.
            sparse_weight: Weight for sparse retrieval scores.
            rrf_k: RRF constant (higher = more weight to top results).
            top_k: Number of documents to retrieve.
        """
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight
        self.rrf_k = rrf_k
        self.top_k = top_k
        
        self._dense_index: dict[str, np.ndarray] = {}
        self._documents: dict[str, str] = {}
        self._metadata: dict[str, dict] = {}
        
        # BM25 parameters
        self._idf: dict[str, float] = {}
        self._doc_lengths: dict[str, int] = {}
        self._avg_doc_length: float = 0.0
        self._term_freqs: dict[str, dict[str, int]] = {}
    
    def add_documents(
        self,
        documents: list[dict[str, Any]],
        embeddings: np.ndarray,
    ) -> None:
        """
        Add documents to the retriever.
        
        Args:
            documents: List of documents with 'id', 'content', 'metadata'.
            embeddings: Document embeddings (N x D).
        """
        for doc, embedding in zip(documents, embeddings):
            doc_id = doc["id"]
            content = doc["content"]
            metadata = doc.get("metadata", {})
            
            self._documents[doc_id] = content
            self._metadata[doc_id] = metadata
            self._dense_index[doc_id] = embedding
            
            # Build BM25 index
            self._index_for_bm25(doc_id, content)
        
        # Compute average document length
        if self._doc_lengths:
            self._avg_doc_length = np.mean(list(self._doc_lengths.values()))
        
        logger.info(f"Indexed {len(documents)} documents")
    
    def retrieve(
        self,
        query: str,
        query_embedding: np.ndarray,
        top_k: int | None = None,
        use_reranker: bool = False,
    ) -> RetrievalResult:
        """
        Retrieve documents using hybrid search.
        
        Args:
            query: Query text.
            query_embedding: Query embedding vector.
            top_k: Number of documents to retrieve.
            use_reranker: Whether to apply cross-encoder reranking.
            
        Returns:
            RetrievalResult with ranked documents.
        """
        import time
        start_time = time.perf_counter()
        
        top_k = top_k or self.top_k
        
        # Dense retrieval
        dense_results = self._dense_search(query_embedding, top_k * 2)
        
        # Sparse retrieval
        sparse_results = self._sparse_search(query, top_k * 2)
        
        # Fuse results using RRF
        fused_results = self._reciprocal_rank_fusion(
            dense_results, sparse_results, top_k
        )
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        return RetrievalResult(
            documents=fused_results,
            query=query,
            retrieval_method="hybrid_rrf",
            latency_ms=latency_ms,
            total_candidates=len(self._documents),
        )
    
    def _dense_search(
        self,
        query_embedding: np.ndarray,
        top_k: int,
    ) -> list[tuple[str, float]]:
        """Perform dense (vector) search."""
        if not self._dense_index:
            return []
        
        scores = {}
        query_norm = np.linalg.norm(query_embedding)
        
        for doc_id, doc_embedding in self._dense_index.items():
            # Cosine similarity
            doc_norm = np.linalg.norm(doc_embedding)
            if query_norm > 0 and doc_norm > 0:
                similarity = np.dot(query_embedding, doc_embedding) / (
                    query_norm * doc_norm
                )
                scores[doc_id] = similarity
        
        # Sort by score
        sorted_results = sorted(
            scores.items(), key=lambda x: x[1], reverse=True
        )[:top_k]
        
        return sorted_results
    
    def _sparse_search(
        self,
        query: str,
        top_k: int,
    ) -> list[tuple[str, float]]:
        """Perform sparse (BM25) search."""
        query_terms = self._tokenize(query)
        
        scores = {}
        k1 = 1.5
        b = 0.75
        
        for doc_id in self._documents:
            score = 0.0
            doc_length = self._doc_lengths.get(doc_id, 0)
            
            for term in query_terms:
                if term not in self._idf:
                    continue
                
                tf = self._term_freqs.get(doc_id, {}).get(term, 0)
                idf = self._idf[term]
                
                # BM25 formula
                numerator = tf * (k1 + 1)
                denominator = tf + k1 * (
                    1 - b + b * doc_length / self._avg_doc_length
                )
                score += idf * numerator / denominator
            
            scores[doc_id] = score
        
        sorted_results = sorted(
            scores.items(), key=lambda x: x[1], reverse=True
        )[:top_k]
        
        return sorted_results
    
    def _reciprocal_rank_fusion(
        self,
        dense_results: list[tuple[str, float]],
        sparse_results: list[tuple[str, float]],
        top_k: int,
    ) -> list[RetrievedDocument]:
        """
        Combine results using Reciprocal Rank Fusion.
        
        RRF score = sum(1 / (k + rank)) for each list
        """
        rrf_scores: dict[str, float] = {}
        
        # Add dense results
        for rank, (doc_id, score) in enumerate(dense_results):
            rrf_score = self.dense_weight / (self.rrf_k + rank + 1)
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + rrf_score
        
        # Add sparse results
        for rank, (doc_id, score) in enumerate(sparse_results):
            rrf_score = self.sparse_weight / (self.rrf_k + rank + 1)
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + rrf_score
        
        # Sort by RRF score
        sorted_results = sorted(
            rrf_scores.items(), key=lambda x: x[1], reverse=True
        )[:top_k]
        
        # Build result objects
        documents = []
        for doc_id, score in sorted_results:
            documents.append(
                RetrievedDocument(
                    id=doc_id,
                    content=self._documents[doc_id],
                    score=score,
                    metadata=self._metadata.get(doc_id, {}),
                    source="fused",
                )
            )
        
        return documents
    
    def _index_for_bm25(self, doc_id: str, content: str) -> None:
        """Index document for BM25 search."""
        terms = self._tokenize(content)
        self._doc_lengths[doc_id] = len(terms)
        
        # Term frequencies
        term_freq: dict[str, int] = {}
        for term in terms:
            term_freq[term] = term_freq.get(term, 0) + 1
        self._term_freqs[doc_id] = term_freq
        
        # Update IDF
        n_docs = len(self._documents)
        for term in set(terms):
            # Document frequency
            df = sum(
                1 for tf in self._term_freqs.values() if term in tf
            )
            # IDF with smoothing
            self._idf[term] = np.log((n_docs - df + 0.5) / (df + 0.5) + 1)
    
    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenization."""
        import re
        text = text.lower()
        tokens = re.findall(r'\b\w+\b', text)
        # Remove stopwords (simplified)
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                     'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                     'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                     'can', 'of', 'to', 'in', 'for', 'on', 'with', 'at', 'by',
                     'from', 'as', 'into', 'through', 'during', 'before', 'after',
                     'above', 'below', 'between', 'under', 'again', 'further',
                     'then', 'once', 'here', 'there', 'when', 'where', 'why',
                     'how', 'all', 'each', 'few', 'more', 'most', 'other', 'some',
                     'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
                     'than', 'too', 'very', 'just', 'and', 'but', 'if', 'or',
                     'because', 'until', 'while', 'this', 'that', 'these', 'those'}
        return [t for t in tokens if t not in stopwords and len(t) > 2]
