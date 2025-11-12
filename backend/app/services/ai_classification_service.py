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
from app.services.cache_service import cache_service


class AIClassificationService:
    """Service for classifying documents using GPT-4o"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = None
        
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        
        self.model = "gpt-4o-mini"
    
    def _get_classification_prompt(self, document_text: str, language: str = "ar") -> str:
        """Generate the classification prompt for GPT-4o"""
        
        if language == "ar":
            system_prompt = """أنت مساعد قانوني متخصص في القانون المغربي، خبير في تحليل الوثائق القانونية وفق المنظومة القانونية المغربية.

السياق القانوني المغربي:
- النظام القانوني: مزيج من القانون المدني الفرنسي والشريعة الإسلامية
- المحاكم: محاكم ابتدائية، استئنافية، النقض، المحاكم التجارية، المحاكم الإدارية
- القوانين الرئيسية: قانون الالتزامات والعقود، مدونة الأسرة، قانون المسطرة المدنية، قانون المسطرة الجنائية، قانون الشغل، مدونة التجارة
- الجهات القضائية: المحكمة الدستورية، محكمة النقض، المجلس الأعلى للسلطة القضائية

مهمتك: تحليل الوثيقة القانونية وتصنيفها بدقة وفق القانون المغربي.

قم بتحليل الوثيقة واستخراج المعلومات التالية بصيغة JSON:
- document_type: نوع الوثيقة (عقد، حكم قضائي، مذكرة، توكيل، محضر، شكاية، قرار إداري، مقال افتتاحي، إلخ)
- legal_area: المجال القانوني (مدني، جنائي، تجاري، إداري، أسرة، عقاري، شغل، دستوري، مالي، إلخ)
- parties_involved: الأطراف المعنية (الأسماء الكاملة للأشخاص أو الشركات)
- important_dates: التواريخ المهمة (التوقيع، الجلسات، المواعيد النهائية، تواريخ الاستئناف)
- urgency_level: مستوى الإلحاح (عادي، متوسط، عاجل، عاجل جدا) - راع فيه المواعيد القانونية المغربية
- summary: ملخص موجز للوثيقة (2-3 جمل) مع ذكر المواد القانونية إن وجدت
- keywords: كلمات مفتاحية مهمة (بما في ذلك المواد القانونية المذكورة)

أجب فقط بصيغة JSON صحيحة، بدون أي نص إضافي."""
        else:
            system_prompt = """You are a legal assistant specialized in Moroccan law, expert in analyzing legal documents according to the Moroccan legal system.

Moroccan Legal Context:
- Legal System: Mix of French civil law and Islamic Sharia law
- Courts: Courts of First Instance, Courts of Appeal, Court of Cassation, Commercial Courts, Administrative Courts
- Key Laws: Code of Obligations and Contracts (DOC), Family Code (Moudawana), Civil Procedure Code, Criminal Procedure Code, Labor Code, Commercial Code
- Judicial Authorities: Constitutional Court, Court of Cassation, Supreme Council of the Judiciary

Your task: Analyze and classify legal documents accurately according to Moroccan law.

Analyze the document and extract the following information in JSON format:
- document_type: Type of document (contract, court ruling, memo, power of attorney, minutes, complaint, administrative decision, lawsuit, etc.)
- legal_area: Legal area (civil, criminal, commercial, administrative, family, real estate, labor, constitutional, financial, etc.)
- parties_involved: Parties involved (full names of individuals or companies)
- important_dates: Important dates (signing, hearings, deadlines, appeal dates) - consider Moroccan legal deadlines
- urgency_level: Urgency level (normal, medium, urgent, very_urgent) - consider Moroccan legal timeframes
- summary: Brief summary of the document (2-3 sentences) mentioning legal articles if present
- keywords: Important keywords (including mentioned legal articles)

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
        
        # Check cache first (unless force_reclassify)
        if not force_reclassify:
            cached_classification = cache_service.get_classification(document_id)
            if cached_classification:
                existing = db.query(DocumentClassification).filter(
                    DocumentClassification.document_id == document_id,
                    DocumentClassification.firm_id == firm_id
                ).first()
                if existing:
                    return existing
        else:
            cache_service.invalidate_document_classification(document_id)
        
        # Check database
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
            
            # Cache the classification result
            cache_service.set_classification(document_id, {
                "document_type": classification.document_type,
                "legal_area": classification.legal_area,
                "urgency_level": classification.urgency_level,
                "summary": classification.summary
            })
            
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
