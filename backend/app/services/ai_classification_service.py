"""
AI Classification Service - Document classification using GPT-4o
Analyzes Arabic legal documents and extracts metadata automatically
"""

import os
import json
import time
from typing import Optional, Dict, Any
from openai import OpenAI, OpenAIError
from sqlalchemy.orm import Session

from app.models import Document, DocumentClassification, User


class AIClassificationService:
    """Service for classifying documents using GPT-4o"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = None
        
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        
        self.model = "gpt-4o"
    
    def _get_classification_prompt(self, document_text: str, language: str = "ar") -> str:
        """Generate the classification prompt for GPT-4o"""
        
        if language == "ar":
            system_prompt = """أنت مساعد قانوني متخصص في تحليل الوثائق القانونية المغربية.
مهمتك هي تحليل الوثيقة وتصنيفها بدقة.

قم بتحليل الوثيقة واستخراج المعلومات التالية بصيغة JSON:
- document_type: نوع الوثيقة (عقد، حكم قضائي، مذكرة، توكيل، محضر، شكاية، إلخ)
- legal_area: المجال القانوني (مدني، جنائي، تجاري، إداري، أسرة، عقاري، شغل، إلخ)
- parties_involved: الأطراف المعنية (الأسماء الكاملة)
- important_dates: التواريخ المهمة (التوقيع، الجلسات، المواعيد النهائية)
- urgency_level: مستوى الإلحاح (عادي، متوسط، عاجل، عاجل جدا)
- summary: ملخص موجز للوثيقة (2-3 جمل)
- keywords: كلمات مفتاحية مهمة

أجب فقط بصيغة JSON صحيحة، بدون أي نص إضافي."""
        else:
            system_prompt = """You are a legal assistant specialized in analyzing Moroccan legal documents.
Your task is to analyze and classify the document accurately.

Analyze the document and extract the following information in JSON format:
- document_type: Type of document (contract, court ruling, memo, power of attorney, minutes, complaint, etc.)
- legal_area: Legal area (civil, criminal, commercial, administrative, family, real estate, labor, etc.)
- parties_involved: Parties involved (full names)
- important_dates: Important dates (signing, hearings, deadlines)
- urgency_level: Urgency level (normal, medium, urgent, very_urgent)
- summary: Brief summary of the document (2-3 sentences)
- keywords: Important keywords

Respond only with valid JSON, no additional text."""
        
        return system_prompt
    
    async def classify_document(
        self,
        db: Session,
        document_id: int,
        firm_id: int,
        user_id: int,
        force_reclassify: bool = False
    ) -> Optional[DocumentClassification]:
        """
        Classify a document using GPT-4o
        
        Args:
            db: Database session
            document_id: ID of document to classify
            firm_id: Firm ID for tenant isolation
            user_id: ID of user requesting classification
            force_reclassify: If True, reclassify even if already classified
            
        Returns:
            DocumentClassification object or None if API key missing
        """
        
        # Check if API key is configured
        if not self.client:
            raise ValueError(
                "OPENAI_API_KEY not configured. Please set it in environment variables."
            )
        
        # Get the document
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.firm_id == firm_id
        ).first()
        
        if not document:
            raise ValueError(f"Document {document_id} not found for firm {firm_id}")
        
        # Check if already classified
        existing = db.query(DocumentClassification).filter(
            DocumentClassification.document_id == document_id,
            DocumentClassification.firm_id == firm_id
        ).first()
        
        if existing and not force_reclassify:
            return existing
        
        # Get OCR text
        ocr_text = document.ocr_text
        if not ocr_text or len(ocr_text.strip()) < 50:
            raise ValueError(
                "Document has no OCR text or text too short. Run OCR first."
            )
        
        # Limit text to ~10,000 characters to control costs
        text_to_analyze = ocr_text[:10000]
        
        start_time = time.time()
        
        try:
            # Call GPT-4o
            language = document.ocr_language or "ar"
            system_prompt = self._get_classification_prompt(text_to_analyze, language)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"الوثيقة:\n\n{text_to_analyze}"}
                ],
                temperature=0.3,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            
            processing_time = time.time() - start_time
            
            # Parse response
            result = json.loads(response.choices[0].message.content)
            
            # Create or update classification
            if existing:
                classification = existing
            else:
                classification = DocumentClassification(
                    document_id=document_id,
                    firm_id=firm_id,
                    classified_by=user_id
                )
                db.add(classification)
            
            # Update fields
            classification.document_type = result.get("document_type", "")
            classification.legal_area = result.get("legal_area", "")
            classification.parties_involved = json.dumps(result.get("parties_involved", []), ensure_ascii=False)
            classification.important_dates = json.dumps(result.get("important_dates", []), ensure_ascii=False)
            classification.urgency_level = result.get("urgency_level", "normal")
            classification.summary = result.get("summary", "")
            classification.keywords = json.dumps(result.get("keywords", []), ensure_ascii=False)
            classification.model_used = self.model
            classification.processing_time_seconds = processing_time
            classification.confidence_score = 0.85
            
            db.commit()
            db.refresh(classification)
            
            return classification
            
        except OpenAIError as e:
            raise Exception(f"OpenAI API error: {str(e)}")
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse GPT-4o response: {str(e)}")
        except Exception as e:
            raise Exception(f"Classification failed: {str(e)}")
    
    def get_classification(
        self,
        db: Session,
        document_id: int,
        firm_id: int
    ) -> Optional[DocumentClassification]:
        """Get existing classification for a document"""
        return db.query(DocumentClassification).filter(
            DocumentClassification.document_id == document_id,
            DocumentClassification.firm_id == firm_id
        ).first()
