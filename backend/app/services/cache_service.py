import hashlib
import json
from collections import OrderedDict
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from threading import Lock
import logging

logger = logging.getLogger(__name__)


class CacheService:
    """Thread-safe in-memory LRU cache with TTL and size limits"""
    
    def __init__(self):
        # LRU caches (OrderedDict maintains insertion order)
        self._embedding_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._classification_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        
        # Thread safety
        self._lock = Lock()
        
        # Cache configuration (1 hour TTL as per architect requirements)
        self._cache_ttl = timedelta(hours=1)
        
        # Size limits to prevent unbounded memory growth
        self._max_embedding_entries = 10000  # ~40MB max
        self._max_classification_entries = 5000  # ~10MB max
        
    def _generate_key(self, text: str, model: str = "") -> str:
        """Generate cache key from text and model"""
        content = f"{model}:{text}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _is_expired(self, cached_data: Dict[str, Any]) -> bool:
        """Check if cached entry has expired"""
        if "timestamp" not in cached_data:
            return True
        cached_time = datetime.fromisoformat(cached_data["timestamp"])
        return datetime.now() - cached_time > self._cache_ttl
    
    def _evict_lru_if_needed(self, cache: OrderedDict, max_size: int):
        """Evict oldest entries if cache exceeds max size (LRU eviction)"""
        while len(cache) >= max_size:
            # Remove oldest entry (FIFO/LRU behavior)
            oldest_key = next(iter(cache))
            del cache[oldest_key]
            logger.debug(f"🗑️ LRU eviction: removed key {oldest_key[:8] if isinstance(oldest_key, str) else oldest_key}...")
    
    def get_embedding(self, text: str, model: str = "text-embedding-3-large") -> Optional[List[float]]:
        """Get cached embedding if available and not expired"""
        key = self._generate_key(text, model)
        
        with self._lock:
            if key in self._embedding_cache:
                cached = self._embedding_cache[key]
                
                if not self._is_expired(cached):
                    # Move to end (most recently used)
                    self._embedding_cache.move_to_end(key)
                    logger.debug(f"✅ Embedding cache HIT for key {key[:8]}...")
                    return cached["embedding"]
                else:
                    # Remove expired entry
                    del self._embedding_cache[key]
                    logger.debug(f"❌ Embedding cache EXPIRED for key {key[:8]}...")
            
            logger.debug(f"❌ Embedding cache MISS for key {key[:8]}...")
            return None
    
    def set_embedding(self, text: str, embedding: List[float], model: str = "text-embedding-3-large"):
        """Cache embedding with LRU eviction if cache is full"""
        key = self._generate_key(text, model)
        
        with self._lock:
            # Evict LRU entries if at capacity
            self._evict_lru_if_needed(self._embedding_cache, self._max_embedding_entries)
            
            # Add new entry (will be at the end = most recent)
            self._embedding_cache[key] = {
                "embedding": embedding,
                "timestamp": datetime.now().isoformat()
            }
            logger.debug(f"💾 Cached embedding for key {key[:8]}...")
    
    def get_classification(self, document_id: int) -> Optional[Dict[str, Any]]:
        """Get cached classification if available and not expired"""
        key = str(document_id)
        
        with self._lock:
            if key in self._classification_cache:
                cached = self._classification_cache[key]
                
                if not self._is_expired(cached):
                    # Move to end (most recently used)
                    self._classification_cache.move_to_end(key)
                    logger.debug(f"✅ Classification cache HIT for document {document_id}")
                    return cached["classification"]
                else:
                    # Remove expired entry
                    del self._classification_cache[key]
                    logger.debug(f"❌ Classification cache EXPIRED for document {document_id}")
            
            logger.debug(f"❌ Classification cache MISS for document {document_id}")
            return None
    
    def set_classification(self, document_id: int, classification: Dict[str, Any]):
        """Cache classification with LRU eviction if cache is full"""
        key = str(document_id)
        
        with self._lock:
            # Evict LRU entries if at capacity
            self._evict_lru_if_needed(self._classification_cache, self._max_classification_entries)
            
            # Add new entry (will be at the end = most recent)
            self._classification_cache[key] = {
                "classification": classification,
                "timestamp": datetime.now().isoformat()
            }
            logger.debug(f"💾 Cached classification for document {document_id}")
    
    def invalidate_document_classification(self, document_id: int):
        """Remove classification from cache (e.g., when force_reclassify=True)"""
        key = str(document_id)
        
        with self._lock:
            if key in self._classification_cache:
                del self._classification_cache[key]
                logger.debug(f"🗑️ Invalidated classification cache for document {document_id}")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics for monitoring"""
        with self._lock:
            return {
                "embedding_cache_size": len(self._embedding_cache),
                "classification_cache_size": len(self._classification_cache),
                "embedding_cache_max": self._max_embedding_entries,
                "classification_cache_max": self._max_classification_entries
            }
    
    def clear_expired_entries(self):
        """Proactively clear all expired entries (can be called periodically)"""
        with self._lock:
            # Clear expired embeddings
            expired_embeddings = [
                key for key, value in self._embedding_cache.items()
                if self._is_expired(value)
            ]
            for key in expired_embeddings:
                del self._embedding_cache[key]
            
            # Clear expired classifications
            expired_classifications = [
                key for key, value in self._classification_cache.items()
                if self._is_expired(value)
            ]
            for key in expired_classifications:
                del self._classification_cache[key]
            
            if expired_embeddings or expired_classifications:
                logger.info(
                    f"🧹 Cleared {len(expired_embeddings)} expired embeddings "
                    f"and {len(expired_classifications)} expired classifications"
                )


# Global singleton instance
cache_service = CacheService()
