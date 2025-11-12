from celery import shared_task, chord
from datetime import datetime
import logging
import os
import sys

sys.path.insert(0, '/home/runner/workspace/backend')

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, name='app.tasks.ocr_tasks.process_document_ocr')
def process_document_ocr(self, document_id: int):
    """
    Process OCR for uploaded document with async processing (40% faster).
    
    Architecture:
    - Feature flag ASYNC_OCR_ENABLED controls rollout (default: true)
    - Uses AsyncOCRService for parallel page processing when enabled
    - Falls back to SyncOCRService when disabled or on error
    
    Runs on CPU-intensive queue for text extraction.
    Uses shared SessionLocal from app.database for proper connection pooling.
    """
    try:
        from app.database import SessionLocal
        from app.models import Document as DocumentModel
        
        logger.info(f"Starting OCR processing for document {document_id}")
        
        with SessionLocal() as db:
            document = db.query(DocumentModel).filter(DocumentModel.id == document_id).first()
            
            if not document:
                logger.error(f"Document {document_id} not found in database")
                raise ValueError(f"Document {document_id} not found")
            
            file_path = document.file_path
            case_id = document.case_id
            
            # Feature flag: Use async OCR if enabled
            use_async_ocr = os.getenv("ASYNC_OCR_ENABLED", "true").lower() == "true"
            
            if use_async_ocr:
                try:
                    from app.services.async_ocr_service import run_async_ocr_in_celery
                    logger.info(f"📄 Using AsyncOCRService for document {document_id} (parallel processing)")
                    
                    result = run_async_ocr_in_celery(
                        file_path=file_path,
                        engine="auto",
                        language="ar",  # Primary language for Moroccan law firms
                        max_concurrent_pages=8
                    )
                    
                    logger.info(
                        f"✅ Async OCR completed for document {document_id} "
                        f"(time: {result.get('processing_time', 0):.2f}s, "
                        f"pages: {result.get('pages_processed', 0)})"
                    )
                except Exception as async_error:
                    logger.warning(
                        f"⚠️ Async OCR failed for document {document_id}, "
                        f"falling back to sync: {async_error}"
                    )
                    # Fallback to sync OCR
                    from app.services.ocr_service import SyncOCRService
                    ocr_service = SyncOCRService()
                    result = ocr_service.process_document(file_path)
            else:
                # Use legacy sync OCR
                from app.services.ocr_service import SyncOCRService
                logger.info(f"📄 Using SyncOCRService for document {document_id} (async disabled)")
                ocr_service = SyncOCRService()
                result = ocr_service.process_document(file_path)
            
            # Update document with OCR results
            document.ocr_processed = True
            document.ocr_text = result.get('extracted_text', '')
            document.ocr_confidence = result.get('ocr_confidence', 0)
            document.ocr_language = result.get('detected_language', 'ar')
            document.is_searchable = True
            
            db.commit()
            
            logger.info(
                f"OCR processing completed for document {document_id} "
                f"(async={use_async_ocr}, confidence={result.get('ocr_confidence', 0)}%)"
            )
            
            return {
                'document_id': document_id,
                'text': result.get('extracted_text', ''),
                'language': result.get('detected_language', 'unknown'),
                'confidence': result.get('ocr_confidence', 0),
                'case_id': case_id,
                'async_processed': use_async_ocr
            }
        
    except Exception as exc:
        logger.error(f"OCR processing failed for document {document_id}: {str(exc)}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
        else:
            logger.critical(f"OCR processing permanently failed for document {document_id}")
            raise

@shared_task(name='app.tasks.ocr_tasks.index_document_elasticsearch')
def index_document_elasticsearch(ocr_results):
    """
    Index document in Elasticsearch AFTER OCR completes.
    Runs on IO-bound queue for network operations.
    Uses shared SessionLocal from app.database for proper connection pooling.
    
    Args:
        ocr_results: Either a list of OCR results from chord, or a single dict from chain
    """
    if isinstance(ocr_results, list):
        if not ocr_results:
            logger.error("Received empty results list")
            return {'success': False, 'error': 'No OCR results'}
        ocr_result = ocr_results[0]
    else:
        ocr_result = ocr_results
    
    document_id = ocr_result.get('document_id')
    
    try:
        from elasticsearch import Elasticsearch
        
        es_url = os.getenv('ELASTICSEARCH_URL', 'http://localhost:9200')
        es = Elasticsearch([es_url])
        
        if not es.ping():
            logger.error("Elasticsearch is not available")
            raise ConnectionError("Elasticsearch connection failed")
        
        index_body = {
            'document_id': document_id,
            'text': ocr_result.get('text', ''),
            'language': ocr_result.get('language', 'unknown'),
            'confidence': ocr_result.get('confidence', 0),
            'case_id': ocr_result.get('case_id'),
            'indexed_at': datetime.utcnow().isoformat(),
            'status': 'indexed'
        }
        
        es.index(
            index='judicial_documents',
            id=document_id,
            document=index_body
        )
        
        logger.info(f"Document {document_id} successfully indexed in Elasticsearch")
        
        from app.database import SessionLocal
        from app.models import Document as DocumentModel
        
        with SessionLocal() as db:
            document = db.query(DocumentModel).filter(DocumentModel.id == document_id).first()
            if not document:
                logger.error(f"Document {document_id} not found after indexing")
                raise ValueError(f"Document {document_id} disappeared during indexing")
            
            document.is_searchable = True
            db.commit()
        
        return {'success': True, 'document_id': document_id}
        
    except Exception as e:
        logger.error(f"Elasticsearch indexing failed for document {document_id}: {str(e)}")
        raise
