from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
import logging

from ..services.metrics_service import MetricsService, metrics_service

router = APIRouter(prefix="/api/metrics", tags=["Performance Metrics"])
logger = logging.getLogger(__name__)


@router.get("/async-comparison")
async def get_async_vs_sync_comparison() -> Dict[str, Any]:
    """
    Compare async vs sync performance for OCR and embeddings
    
    Returns speedup factors and performance metrics for:
    - AsyncOCR vs Sync OCR (target: 3-5x faster)
    - Async Embeddings vs Sync Embeddings (target: 10x faster)
    - Cache hit rates
    """
    try:
        return metrics_service.get_async_vs_sync_comparison()
    except Exception as e:
        logger.error(f"Error getting async comparison metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache-stats")
async def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache performance statistics
    
    Returns cache hits, misses, and hit rate percentage
    """
    try:
        comparison = metrics_service.get_async_vs_sync_comparison()
        return comparison.get("cache", {})
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_metrics_summary() -> Dict[str, Any]:
    """
    Get complete metrics summary for all tracked operations
    """
    try:
        from ..services.metrics_service import MetricType
        from datetime import datetime
        
        all_metrics = {}
        for metric_type in MetricType:
            all_metrics[metric_type.value] = metrics_service.get_metrics(metric_type)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": all_metrics,
            "async_comparison": metrics_service.get_async_vs_sync_comparison()
        }
    except Exception as e:
        logger.error(f"Error getting metrics summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prometheus")
async def export_prometheus_format() -> str:
    """
    Export metrics in Prometheus format for monitoring
    """
    try:
        return metrics_service.export_prometheus_format()
    except Exception as e:
        logger.error(f"Error exporting Prometheus metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
