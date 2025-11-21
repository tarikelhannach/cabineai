from celery import shared_task, chord
from datetime import datetime
import logging
import os
import sys

sys.path.insert(0, '/home/runner/workspace/backend')

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, name='app.tasks.ocr_tasks.process_document_ocr', 
             soft_time_limit=60)  # 60s soft limit (30s AI timeout + 30s buffer)
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
            
            # AI Processing (NEW): Process document with DeepSeek AI
            extracted_text = result.get('extracted_text', '')
            if extracted_text and len(extracted_text.strip()) > 50:  # Only process if meaningful text
                try:
                    from app.services.ai_service import ai_service
                    import asyncio
                    
                    logger.info(f"Starting AI processing for document {document_id}")
                    
                    # Run AI processing (async in sync context)
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    ai_results = loop.run_until_complete(ai_service.process_document(extracted_text))
                    loop.close()
                    
                    # Update document with AI results
                    document.ai_classification = ai_results.get('classification')
                    document.ai_metadata = ai_results.get('metadata')
                    document.ai_summary = ai_results.get('summary')
                    document.ai_processed = True
                    document.ai_processed_at = datetime.utcnow()
                    
                    if ai_results.get('error'):
                        document.ai_error = ai_results['error']
                        logger.warning(f"AI processing completed with errors for document {document_id}: {ai_results['error']}")
                    else:
                        logger.info(f"✅ AI processing completed successfully for document {document_id}")
                    
                    db.commit()
                    
                except Exception as ai_exc:
                    # Graceful degradation: Log error but don't fail the entire task
                    error_str = str(ai_exc)
                    
                    # Handle rate limits with exponential backoff
                    if "429" in error_str or "rate_limit" in error_str.lower():
                        logger.warning(f"Rate limit hit for document {document_id}, will retry")
                        document.ai_error = f"Rate limit (will retry): {error_str}"
                        db.commit()
                        # Retry with exponential backoff (60s, 120s, 240s)
                        raise self.retry(exc=ai_exc, countdown=60 * (2 ** self.request.retries))
                    
                    logger.error(f"AI processing failed for document {document_id}: {error_str}")
                    document.ai_error = error_str
                    document.ai_processed = False
                    db.commit()
            else:
                logger.info(f"Skipping AI processing for document {document_id} (insufficient text)")
            
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
