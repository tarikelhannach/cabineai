import hashlib
import json
from functools import lru_cache
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class CacheService:
    def __init__(self):
        self._embedding_cache: Dict[str, Dict[str, Any]] = {}
        self._classification_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = timedelta(hours=24)
        
    def _generate_key(self, text: str, model: str = "") -> str:
        content = f"{model}:{text}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _is_expired(self, cached_data: Dict[str, Any]) -> bool:
        if "timestamp" not in cached_data:
            return True
        cached_time = datetime.fromisoformat(cached_data["timestamp"])
        return datetime.now() - cached_time > self._cache_ttl
    
    def get_embedding(self, text: str, model: str = "text-embedding-3-large") -> Optional[List[float]]:
        key = self._generate_key(text, model)
        if key in self._embedding_cache:
            cached = self._embedding_cache[key]
            if not self._is_expired(cached):
                logger.debug(f"✅ Embedding cache HIT for key {key[:8]}...")
                return cached["embedding"]
            else:
                del self._embedding_cache[key]
                logger.debug(f"❌ Embedding cache EXPIRED for key {key[:8]}...")
        logger.debug(f"❌ Embedding cache MISS for key {key[:8]}...")
        return None
    
    def set_embedding(self, text: str, embedding: List[float], model: str = "text-embedding-3-large"):
        key = self._generate_key(text, model)
        self._embedding_cache[key] = {
            "embedding": embedding,
            "timestamp": datetime.now().isoformat()
        }
        logger.debug(f"💾 Cached embedding for key {key[:8]}...")
    
    def get_classification(self, document_id: int) -> Optional[Dict[str, Any]]:
        key = str(document_id)
        if key in self._classification_cache:
            cached = self._classification_cache[key]
            if not self._is_expired(cached):
                logger.debug(f"✅ Classification cache HIT for document {document_id}")
                return cached["classification"]
            else:
                del self._classification_cache[key]
                logger.debug(f"❌ Classification cache EXPIRED for document {document_id}")
        logger.debug(f"❌ Classification cache MISS for document {document_id}")
        return None
    
    def set_classification(self, document_id: int, classification: Dict[str, Any]):
        key = str(document_id)
        self._classification_cache[key] = {
            "classification": classification,
            "timestamp": datetime.now().isoformat()
        }
        logger.debug(f"💾 Cached classification for document {document_id}")
    
    def invalidate_document_classification(self, document_id: int):
        key = str(document_id)
        if key in self._classification_cache:
            del self._classification_cache[key]
            logger.debug(f"🗑️ Invalidated classification cache for document {document_id}")
    
    def get_cache_stats(self) -> Dict[str, int]:
        return {
            "embedding_cache_size": len(self._embedding_cache),
            "classification_cache_size": len(self._classification_cache),
            "total_cache_items": len(self._embedding_cache) + len(self._classification_cache)
        }
    
    def clear_all(self):
        self._embedding_cache.clear()
        self._classification_cache.clear()
        logger.info("🗑️ Cleared all caches")


cache_service = CacheService()
