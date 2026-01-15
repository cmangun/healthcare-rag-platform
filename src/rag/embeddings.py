"""
Embedding Service

Provides embedding generation with caching and batch processing
for healthcare document retrieval.
"""

import hashlib
import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Embedding service with caching and healthcare optimizations.
    
    Features:
    - Multiple model support (OpenAI, local models)
    - Embedding caching for efficiency
    - Batch processing
    - Healthcare-specific preprocessing
    """
    
    def __init__(
        self,
        model_name: str = "text-embedding-3-small",
        cache_embeddings: bool = True,
        batch_size: int = 100,
    ):
        """
        Initialize embedding service.
        
        Args:
            model_name: Embedding model name.
            cache_embeddings: Whether to cache embeddings.
            batch_size: Batch size for processing.
        """
        self.model_name = model_name
        self.cache_embeddings = cache_embeddings
        self.batch_size = batch_size
        
        self._cache: dict[str, np.ndarray] = {}
        self._client: Any = None
        self._dimension: int | None = None
    
    def embed_texts(
        self,
        texts: list[str],
        show_progress: bool = False,
    ) -> np.ndarray:
        """
        Generate embeddings for texts.
        
        Args:
            texts: List of texts to embed.
            show_progress: Show progress bar.
            
        Returns:
            Numpy array of embeddings (N x D).
        """
        # Check cache first
        embeddings = []
        texts_to_embed = []
        cache_keys = []
        
        for text in texts:
            cache_key = self._get_cache_key(text)
            if self.cache_embeddings and cache_key in self._cache:
                embeddings.append(self._cache[cache_key])
            else:
                texts_to_embed.append(text)
                cache_keys.append(cache_key)
        
        # Embed remaining texts
        if texts_to_embed:
            new_embeddings = self._embed_batch(texts_to_embed)
            
            # Update cache
            for key, emb in zip(cache_keys, new_embeddings):
                if self.cache_embeddings:
                    self._cache[key] = emb
                embeddings.append(emb)
        
        return np.array(embeddings)
    
    def embed_query(self, query: str) -> np.ndarray:
        """
        Generate embedding for a single query.
        
        Args:
            query: Query text.
            
        Returns:
            Query embedding vector.
        """
        embeddings = self.embed_texts([query])
        return embeddings[0]
    
    def _embed_batch(self, texts: list[str]) -> list[np.ndarray]:
        """Embed a batch of texts."""
        if self.model_name.startswith("text-embedding"):
            return self._embed_openai(texts)
        else:
            return self._embed_local(texts)
    
    def _embed_openai(self, texts: list[str]) -> list[np.ndarray]:
        """Generate embeddings using OpenAI API."""
        try:
            from openai import OpenAI
            
            if self._client is None:
                self._client = OpenAI()
            
            embeddings = []
            for i in range(0, len(texts), self.batch_size):
                batch = texts[i:i + self.batch_size]
                response = self._client.embeddings.create(
                    model=self.model_name,
                    input=batch,
                )
                
                for item in response.data:
                    embeddings.append(np.array(item.embedding))
            
            return embeddings
            
        except ImportError:
            logger.warning("OpenAI not installed, using random embeddings")
            return self._embed_random(texts)
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return self._embed_random(texts)
    
    def _embed_local(self, texts: list[str]) -> list[np.ndarray]:
        """Generate embeddings using local model."""
        try:
            from sentence_transformers import SentenceTransformer
            
            if self._client is None:
                self._client = SentenceTransformer(self.model_name)
            
            embeddings = self._client.encode(
                texts,
                batch_size=self.batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
            
            return [emb for emb in embeddings]
            
        except ImportError:
            logger.warning("sentence-transformers not installed")
            return self._embed_random(texts)
    
    def _embed_random(self, texts: list[str]) -> list[np.ndarray]:
        """Generate random embeddings (for testing)."""
        dim = self._dimension or 1536
        return [np.random.randn(dim) for _ in texts]
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        return hashlib.md5(
            f"{self.model_name}:{text}".encode()
        ).hexdigest()
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        if self._dimension is None:
            # Infer from model
            test_emb = self.embed_query("test")
            self._dimension = len(test_emb)
        return self._dimension
    
    def clear_cache(self) -> None:
        """Clear embedding cache."""
        self._cache.clear()
        logger.info("Embedding cache cleared")
