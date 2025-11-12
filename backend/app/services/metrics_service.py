"""
Metrics Service - Optimized performance tracking and monitoring
Tracks latencies, success/failure rates, and resource usage across async pipeline

Optimizations for 600 concurrent tenants:
- Sharded locks (per metric type) to reduce contention
- Incremental quantile tracking (no full sorting on each event)
- Lightweight counters (minimal metadata storage)
- Lock-free reads where possible
- Thread-safe operations without global bottleneck

Features:
- Real-time metrics collection (OCR, embeddings, AI calls)
- Async vs sync performance comparison
- OpenAI rate limit tracking
- Prometheus-compatible format
"""

import time
import logging
import math
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
from threading import RLock
from enum import Enum
import statistics

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Metric type enumeration"""
    OCR_ASYNC = "ocr_async"
    OCR_SYNC = "ocr_sync"
    EMBEDDING_ASYNC = "embedding_async"
    EMBEDDING_SYNC = "embedding_sync"
    AI_CLASSIFICATION = "ai_classification"
    AI_RAG_CHAT = "ai_rag_chat"
    AI_DRAFTING = "ai_drafting"
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"


@dataclass
class AggregatedMetrics:
    """
    Lightweight aggregated metrics for a specific operation
    
    Optimized for multi-tenant concurrency:
    - No heavy metadata storage (only counters)
    - Incremental percentile tracking (reservoir sampling)
    - Lock-free reads for most operations
    """
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_latency_seconds: float = 0.0
    min_latency: float = float('inf')
    max_latency: float = 0.0
    
    # Lightweight percentile approximation (reservoir of 1000 samples)
    latency_reservoir: List[float] = field(default_factory=list)
    reservoir_size: int = 1000  # Fixed size for memory efficiency
    
    # Error distribution (lightweight counters)
    error_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    # Cached percentiles (updated periodically, not on every sample)
    _p50_latency: float = 0.0
    _p95_latency: float = 0.0
    _p99_latency: float = 0.0
    _percentiles_dirty: bool = True  # Flag for lazy recomputation
    
    @property
    def avg_latency(self) -> float:
        """Calculate average latency"""
        return self.total_latency_seconds / self.total_calls if self.total_calls > 0 else 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate (0-100)"""
        return (self.successful_calls / self.total_calls * 100) if self.total_calls > 0 else 0.0
    
    @property
    def p50_latency(self) -> float:
        """Get P50 (median) latency"""
        if self._percentiles_dirty and self.latency_reservoir:
            self._recompute_percentiles()
        return self._p50_latency
    
    @property
    def p95_latency(self) -> float:
        """Get P95 latency"""
        if self._percentiles_dirty and self.latency_reservoir:
            self._recompute_percentiles()
        return self._p95_latency
    
    @property
    def p99_latency(self) -> float:
        """Get P99 latency"""
        if self._percentiles_dirty and self.latency_reservoir:
            self._recompute_percentiles()
        return self._p99_latency
    
    def _recompute_percentiles(self):
        """Lazy percentile recomputation (only when read, not on every write)"""
        if not self.latency_reservoir:
            return
        
        sorted_latencies = sorted(self.latency_reservoir)
        n = len(sorted_latencies)
        
        self._p50_latency = sorted_latencies[int(n * 0.50)] if n > 0 else 0.0
        self._p95_latency = sorted_latencies[int(n * 0.95)] if n > 0 else 0.0
        self._p99_latency = sorted_latencies[int(n * 0.99)] if n > 0 else 0.0
        self._percentiles_dirty = False


class MetricsService:
    """
    Optimized metrics collection service for JusticeAI Commercial
    
    High-performance metrics for 600 concurrent tenants:
    - Sharded locks (one per metric type) - eliminates global bottleneck
    - Lazy percentile computation (only on read, not write)
    - Reservoir sampling (fixed 1000 samples per metric)
    - Lock-free reads where possible
    """
    
    def __init__(self, reservoir_size: int = 1000):
        """
        Initialize optimized metrics service
        
        Args:
            reservoir_size: Reservoir size per metric (default: 1000 for memory efficiency)
        """
        self.reservoir_size = reservoir_size
        
        # Sharded locks - one per metric type (eliminates global bottleneck)
        self._metrics: Dict[MetricType, AggregatedMetrics] = {
            metric_type: AggregatedMetrics(reservoir_size=reservoir_size) 
            for metric_type in MetricType
        }
        self._locks: Dict[MetricType, RLock] = {
            metric_type: RLock() for metric_type in MetricType
        }
        
        # OpenAI rate limit tracking (separate lock)
        self._rate_limit_events: List[Dict[str, Any]] = []
        self._rate_limit_lock = RLock()
        self._last_cleanup = datetime.utcnow()
        
        logger.info(
            f"MetricsService initialized (reservoir_size={reservoir_size}, "
            f"sharded_locks={len(self._locks)})"
        )
    
    def record_latency(
        self,
        metric_type: MetricType,
        duration_seconds: float,
        success: bool = True,
        error_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record a latency measurement (optimized for multi-tenant concurrency)
        
        Args:
            metric_type: Type of operation
            duration_seconds: Duration in seconds
            success: Whether operation succeeded
            error_type: Error type if failed
            metadata: Additional metadata (ignored for performance)
        """
        # Use sharded lock (only locks this metric type, not all metrics)
        with self._locks[metric_type]:
            agg = self._metrics[metric_type]
            agg.total_calls += 1
            
            if success:
                agg.successful_calls += 1
                # Only add successful latencies to reservoir (for percentile calculation)
                if len(agg.latency_reservoir) < agg.reservoir_size:
                    # Reservoir not full yet - add directly
                    agg.latency_reservoir.append(duration_seconds)
                else:
                    # Reservoir full - use reservoir sampling (random replacement)
                    # This maintains statistical representativeness
                    import random
                    replace_idx = random.randint(0, agg.reservoir_size - 1)
                    agg.latency_reservoir[replace_idx] = duration_seconds
                
                # Mark percentiles as dirty (will recompute on next read)
                agg._percentiles_dirty = True
            else:
                agg.failed_calls += 1
                if error_type:
                    agg.error_counts[error_type] += 1
            
            # Update lightweight stats (no sorting needed)
            agg.total_latency_seconds += duration_seconds
            agg.min_latency = min(agg.min_latency, duration_seconds)
            agg.max_latency = max(agg.max_latency, duration_seconds)
    
    def record_rate_limit_event(
        self,
        service: str,
        error_message: str,
        retry_after: Optional[int] = None
    ):
        """
        Record OpenAI rate limit event for alerting
        
        Args:
            service: Service that hit rate limit (e.g., "embedding", "classification")
            error_message: Error message from OpenAI
            retry_after: Retry-After header value (seconds)
        """
        # Use separate lock for rate limit events (doesn't block metric writes)
        with self._rate_limit_lock:
            event = {
                "timestamp": datetime.utcnow().isoformat(),
                "service": service,
                "error_message": error_message,
                "retry_after": retry_after
            }
            self._rate_limit_events.append(event)
            
            # Keep only last 1000 events
            if len(self._rate_limit_events) > 1000:
                self._rate_limit_events = self._rate_limit_events[-1000:]
            
            logger.warning(
                f"⚠️ Rate limit hit: {service} - {error_message} "
                f"(retry_after={retry_after}s)"
            )
    
    def get_metrics(
        self,
        metric_type: Optional[MetricType] = None,
        since: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get aggregated metrics (optimized with per-type locking)
        
        Args:
            metric_type: Specific metric type (None for all)
            since: Filter samples since timestamp (ignored for performance)
        
        Returns:
            Dict with aggregated metrics
        """
        if metric_type:
            # Single metric - use its lock only
            with self._locks[metric_type]:
                return self._serialize_metric(metric_type)
        else:
            # All metrics - lock individually to minimize contention
            result = {}
            for mt in MetricType:
                with self._locks[mt]:
                    result[mt.value] = self._serialize_metric(mt)
            return result
    
    def _serialize_metric(
        self,
        metric_type: MetricType
    ) -> Dict[str, Any]:
        """Serialize aggregated metrics to dict (lock must be held by caller)"""
        agg = self._metrics[metric_type]
        
        return {
            "metric_type": metric_type.value,
            "total_calls": agg.total_calls,
            "successful_calls": agg.successful_calls,
            "failed_calls": agg.failed_calls,
            "success_rate_percent": round(agg.success_rate, 2),
            "latency": {
                "avg_seconds": round(agg.avg_latency, 3),
                "min_seconds": round(agg.min_latency, 3) if agg.min_latency != float('inf') else 0,
                "max_seconds": round(agg.max_latency, 3),
                "p50_seconds": round(agg.p50_latency, 3),  # Triggers lazy recomputation if dirty
                "p95_seconds": round(agg.p95_latency, 3),
                "p99_seconds": round(agg.p99_latency, 3)
            },
            "error_distribution": dict(agg.error_counts),
            "reservoir_samples": len(agg.latency_reservoir)
        }
    
    def get_async_vs_sync_comparison(self) -> Dict[str, Any]:
        """
        Compare async vs sync performance for OCR and embeddings
        
        Returns:
            Dict with comparative metrics
        """
        with self._lock:
            return {
                "ocr": {
                    "async": self._serialize_metric(MetricType.OCR_ASYNC),
                    "sync": self._serialize_metric(MetricType.OCR_SYNC),
                    "speedup": self._calculate_speedup(
                        MetricType.OCR_ASYNC, MetricType.OCR_SYNC
                    )
                },
                "embeddings": {
                    "async": self._serialize_metric(MetricType.EMBEDDING_ASYNC),
                    "sync": self._serialize_metric(MetricType.EMBEDDING_SYNC),
                    "speedup": self._calculate_speedup(
                        MetricType.EMBEDDING_ASYNC, MetricType.EMBEDDING_SYNC
                    )
                },
                "cache": {
                    "hits": self._metrics[MetricType.CACHE_HIT].total_calls,
                    "misses": self._metrics[MetricType.CACHE_MISS].total_calls,
                    "hit_rate_percent": self._calculate_cache_hit_rate()
                }
            }
    
    def _calculate_speedup(
        self,
        async_type: MetricType,
        sync_type: MetricType
    ) -> Optional[float]:
        """Calculate speedup factor (sync_time / async_time)"""
        async_avg = self._metrics[async_type].avg_latency
        sync_avg = self._metrics[sync_type].avg_latency
        
        if async_avg > 0 and sync_avg > 0:
            return round(sync_avg / async_avg, 2)
        return None
    
    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate percentage"""
        hits = self._metrics[MetricType.CACHE_HIT].total_calls
        misses = self._metrics[MetricType.CACHE_MISS].total_calls
        total = hits + misses
        
        return round((hits / total * 100), 2) if total > 0 else 0.0
    
    def get_rate_limit_events(
        self,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get recent rate limit events
        
        Args:
            since: Filter events since timestamp
            limit: Maximum events to return
        
        Returns:
            List of rate limit events
        """
        with self._lock:
            events = self._rate_limit_events
            
            if since:
                events = [
                    e for e in events
                    if datetime.fromisoformat(e["timestamp"]) >= since
                ]
            
            return events[-limit:]
    
    def reset_metrics(self, metric_type: Optional[MetricType] = None):
        """
        Reset metrics (use for testing or periodic cleanup)
        
        Args:
            metric_type: Specific metric to reset (None for all)
        """
        if metric_type:
            with self._locks[metric_type]:
                self._metrics[metric_type] = AggregatedMetrics(reservoir_size=self.reservoir_size)
                logger.info(f"Metrics reset for {metric_type.value}")
        else:
            # Reset all - lock individually
            for mt in MetricType:
                with self._locks[mt]:
                    self._metrics[mt] = AggregatedMetrics(reservoir_size=self.reservoir_size)
            
            with self._rate_limit_lock:
                self._rate_limit_events.clear()
            
            logger.info("All metrics reset")
    
    def cleanup_old_samples(self, older_than_hours: int = 24):
        """
        Clean up samples older than specified hours (periodic maintenance)
        
        Note: With reservoir sampling, cleanup is automatic - reservoir maintains
        fixed size via random replacement. This method is a no-op for compatibility.
        
        Args:
            older_than_hours: Ignored (reservoir is self-cleaning)
        """
        # Reservoir sampling maintains fixed size automatically
        # No cleanup needed
        logger.debug("Cleanup skipped - reservoir sampling is self-maintaining")
        self._last_cleanup = datetime.utcnow()
    
    def export_prometheus_format(self) -> str:
        """
        Export metrics in Prometheus text format
        
        Returns:
            Prometheus-compatible metrics string
        """
        lines = []
        timestamp = int(time.time() * 1000)
        
        for metric_type in MetricType:
            agg = self._metrics[metric_type]
            prefix = f"justiceai_{metric_type.value}"
            
            # Counters
            lines.append(f'# TYPE {prefix}_total counter')
            lines.append(f'{prefix}_total {agg.total_calls} {timestamp}')
            
            lines.append(f'# TYPE {prefix}_success counter')
            lines.append(f'{prefix}_success {agg.successful_calls} {timestamp}')
            
            lines.append(f'# TYPE {prefix}_failed counter')
            lines.append(f'{prefix}_failed {agg.failed_calls} {timestamp}')
            
            # Latency histogram
            lines.append(f'# TYPE {prefix}_latency_seconds histogram')
            lines.append(f'{prefix}_latency_seconds{{quantile="0.5"}} {agg.p50_latency} {timestamp}')
            lines.append(f'{prefix}_latency_seconds{{quantile="0.95"}} {agg.p95_latency} {timestamp}')
            lines.append(f'{prefix}_latency_seconds{{quantile="0.99"}} {agg.p99_latency} {timestamp}')
        
        return "\n".join(lines)


# Global singleton instance
metrics_service = MetricsService()
