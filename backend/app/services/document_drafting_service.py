"""
Legal Document Drafting Service using GPT-4o
Generates legal documents in Arabic following Moroccan legal standards
"""

import os
import time
import json
import re
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from datetime import datetime
from openai import OpenAI

from ..models import (
    DocumentTemplate, GeneratedDocument, LegalDocumentType, DraftStatus, User
)


class DocumentDraftingService:
    """
    Service for generating legal documents using GPT-4o.
    
    Features:
    - Template-based generation with placeholder replacement
    - Free-form generation from user prompts
    - Arabic language optimization
    - Moroccan legal standards compliance
    - Lazy-loading OpenAI client for graceful degradation
    """
    
    def __init__(self):
        """Initialize service with lazy OpenAI client loading"""
        self._openai_client = None
    
    def _ensure_openai_client(self) -> OpenAI:
        """
        Lazy-load OpenAI client only when needed for AI operations.
        Raises ValueError if API key is not configured.
        """
        if self._openai_client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "OpenAI API key not configured. Please add your OpenAI API key to secrets."
                )
            self._openai_client = OpenAI(api_key=api_key)
        return self._openai_client
    
    def generate_from_template(
        self,
        template_id: int,
        placeholders: Dict[str, str],
        firm_id: int,
        user_id: int,
        db: Session,
        expediente_id: Optional[int] = None,
        additional_instructions: Optional[str] = None
    ) -> GeneratedDocument:
        """
        Generate a legal document from a template with placeholder replacement.
        
        Args:
            template_id: ID of the template to use
            placeholders: Dict mapping placeholder names to values
            firm_id: Firm ID for tenant isolation
            user_id: User ID creating the document
            db: Database session
            expediente_id: Optional case ID to associate
            additional_instructions: Optional additional instructions for GPT-4o
        
        Returns:
            GeneratedDocument instance
        
        Raises:
            ValueError: If template not found or API key missing
        """
        # Verify template exists and belongs to firm
        template = db.query(DocumentTemplate).filter(
            DocumentTemplate.id == template_id,
            DocumentTemplate.firm_id == firm_id,
            DocumentTemplate.is_active == True
        ).first()
        
        if not template:
            raise ValueError(f"Template {template_id} not found or not accessible")
        
        # Replace placeholders in template
        content = str(template.template_content)  # Convert to string for type safety
        for key, value in placeholders.items():
            placeholder_pattern = f"{{{{{key}}}}}"
            content = content.replace(placeholder_pattern, str(value))
        
        # Use GPT-4o to enhance and polish the document
        start_time = time.time()
        
        client = self._ensure_openai_client()
        
        system_prompt = """أنت محامٍ مغربي خبير متخصص في صياغة الوثائق القانونية وفق القانون المغربي.

السياق القانوني المغربي:
- النظام القانوني: مزيج من القانون المدني الفرنسي والشريعة الإسلامية
- القوانين المرجعية: قانون الالتزامات والعقود (ظهير 1913)، مدونة الأسرة (2004)، قانون المسطرة المدنية، قانون المسطرة الجنائية، قانون الشغل، مدونة التجارة
- المحاكم: محاكم ابتدائية، استئنافية، محكمة النقض، محاكم تجارية، محاكم إدارية

مهمتك: تحسين وصقل الوثيقة القانونية المقدمة، مع التأكد من:
1. الامتثال الدقيق للمعايير القانونية المغربية والإشارة إلى المواد القانونية ذات الصلة
2. الصياغة القانونية الدقيقة والاحترافية باستخدام المصطلحات القانونية المغربية المعتمدة
3. الهيكل القانوني الصحيح (مقدمة، أطراف، شروط، توقيعات، إلخ)
4. ذكر المواعيد القانونية والآجال المنصوص عليها في القانون المغربي
5. الوضوح والدقة في التعبير مع تجنب الغموض

قم بإرجاع الوثيقة المحسنة فقط، دون أي تعليقات إضافية."""

        user_prompt = f"""الوثيقة الأصلية:

{content}

{f"تعليمات إضافية: {additional_instructions}" if additional_instructions else ""}

قم بتحسين هذه الوثيقة مع الحفاظ على جميع المعلومات المهمة."""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,  # Lower temperature for legal precision
            max_tokens=4000
        )
        
        generation_time = time.time() - start_time
        enhanced_content = response.choices[0].message.content or content  # Fallback to original if None
        
        # Create generated document
        generated_doc = GeneratedDocument(
            firm_id=firm_id,
            template_id=template_id,
            expediente_id=expediente_id,
            document_type=template.template_type,
            title=f"{template.name} - {time.strftime('%Y-%m-%d %H:%M')}",
            content=enhanced_content,
            status=DraftStatus.DRAFT,
            user_input=json.dumps(placeholders, ensure_ascii=False),
            generation_metadata=json.dumps({
                "placeholders": placeholders,
                "additional_instructions": additional_instructions,
                "template_name": template.name
            }, ensure_ascii=False),
            model_used="gpt-4o",
            generation_time_seconds=generation_time,
            created_by=user_id
        )
        
        db.add(generated_doc)
        db.commit()
        db.refresh(generated_doc)
        
        return generated_doc
    
    def generate_from_prompt(
        self,
        document_type: LegalDocumentType,
        user_prompt: str,
        firm_id: int,
        user_id: int,
        db: Session,
        expediente_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> GeneratedDocument:
        """
        Generate a legal document from a free-form user prompt.
        
        Args:
            document_type: Type of legal document to generate
            user_prompt: User's description of what they need
            firm_id: Firm ID for tenant isolation
            user_id: User ID creating the document
            db: Database session
            expediente_id: Optional case ID to associate
            context: Optional context data (case info, client info, etc.)
        
        Returns:
            GeneratedDocument instance
        
        Raises:
            ValueError: If API key missing
        """
        start_time = time.time()
        
        client = self._ensure_openai_client()
        
        # Document type specific system prompts
        type_prompts = {
            LegalDocumentType.ACTA: "محضر اجتماع قانوني",
            LegalDocumentType.DEMANDA: "عريضة دعوى",
            LegalDocumentType.CONTRATO: "عقد قانوني",
            LegalDocumentType.PODER: "توكيل قانوني",
            LegalDocumentType.ESCRITO: "مذكرة قانونية",
            LegalDocumentType.DICTAMEN: "رأي قانوني",
            LegalDocumentType.OTHER: "وثيقة قانونية"
        }
        
        doc_type_ar = type_prompts.get(document_type, "وثيقة قانونية")
        
        system_prompt = f"""أنت محامٍ مغربي خبير متخصص في صياغة الوثائق القانونية وفق القانون المغربي.

السياق القانوني المغربي:
- النظام القانوني: مزيج من القانون المدني الفرنسي والشريعة الإسلامية
- القوانين المرجعية: قانون الالتزامات والعقود (ظهير 1913)، مدونة الأسرة (2004)، قانون المسطرة المدنية، قانون المسطرة الجنائية، قانون الشغل، مدونة التجارة
- المحاكم المختصة: محاكم ابتدائية، استئنافية، محكمة النقض، محاكم تجارية، محاكم إدارية

مهمتك: إنشاء {doc_type_ar} احترافية وفقاً للمعايير القانونية المغربية.

يجب أن تتضمن الوثيقة:
1. صياغة قانونية دقيقة ومهنية باللغة العربية الفصحى
2. المصطلحات القانونية المغربية المعتمدة رسمياً
3. الهيكل القانوني الصحيح (ديباجة، أطراف، موضوع، شروط، توقيعات)
4. الإشارة إلى المواد القانونية ذات الصلة من التشريعات المغربية
5. ذكر المواعيد والآجال القانونية المنصوص عليها
6. الامتثال الكامل للتشريعات المغربية النافذة
7. الوضوح والدقة في التعبير مع تجنب الغموض

قم بإنشاء الوثيقة كاملة، محكمة الصياغة، وجاهزة للاستخدام المباشر."""

        context_str = ""
        if context:
            context_str = f"\n\nمعلومات سياقية:\n{json.dumps(context, ensure_ascii=False, indent=2)}"
        
        user_message = f"""المطلوب: {user_prompt}{context_str}

قم بإنشاء {doc_type_ar} كاملة وفقاً لهذه المتطلبات."""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,  # Lower temperature for legal precision
            max_tokens=4000
        )
        
        generation_time = time.time() - start_time
        content = response.choices[0].message.content or ""
        
        # Extract title from first line or use default
        first_line = content.split('\n')[0] if content else doc_type_ar
        title = first_line[:200] if len(first_line) < 500 else f"{doc_type_ar} - {time.strftime('%Y-%m-%d %H:%M')}"
        
        # Create generated document
        generated_doc = GeneratedDocument(
            firm_id=firm_id,
            template_id=None,  # No template used
            expediente_id=expediente_id,
            document_type=document_type,
            title=title,
            content=content,
            status=DraftStatus.DRAFT,
            user_input=user_prompt,
            generation_metadata=json.dumps({
                "context": context,
                "generation_method": "free_prompt"
            }, ensure_ascii=False),
            model_used="gpt-4o",
            generation_time_seconds=generation_time,
            created_by=user_id
        )
        
        db.add(generated_doc)
        db.commit()
        db.refresh(generated_doc)
        
        return generated_doc
    
    def update_document_status(
        self,
        document_id: int,
        new_status: DraftStatus,
        firm_id: int,
        user_id: int,
        db: Session,
        review_notes: Optional[str] = None
    ) -> GeneratedDocument:
        """
        Update the status of a generated document (review workflow).
        
        Args:
            document_id: ID of the generated document
            new_status: New status to set
            firm_id: Firm ID for tenant isolation
            user_id: User ID performing the action
            db: Database session
            review_notes: Optional review notes
        
        Returns:
            Updated GeneratedDocument instance
        
        Raises:
            ValueError: If document not found
        """
        doc = db.query(GeneratedDocument).filter(
            GeneratedDocument.id == document_id,
            GeneratedDocument.firm_id == firm_id
        ).first()
        
        if not doc:
            raise ValueError(f"Document {document_id} not found or not accessible")
        
        doc.status = new_status  # type: ignore
        
        if new_status == DraftStatus.REVIEWED:
            doc.reviewed_by = user_id  # type: ignore
            doc.reviewed_at = datetime.now()  # type: ignore
        elif new_status == DraftStatus.APPROVED:
            doc.approved_by = user_id  # type: ignore
            doc.approved_at = datetime.now()  # type: ignore
        
        if review_notes:
            doc.review_notes = review_notes  # type: ignore
        
        db.commit()
        db.refresh(doc)
        
        return doc
    
    def get_document(
        self,
        document_id: int,
        firm_id: int,
        db: Session
    ) -> GeneratedDocument:
        """
        Get a generated document by ID with tenant isolation.
        
        Args:
            document_id: ID of the generated document
            firm_id: Firm ID for tenant isolation
            db: Database session
        
        Returns:
            GeneratedDocument instance
        
        Raises:
            ValueError: If document not found
        """
        doc = db.query(GeneratedDocument).filter(
            GeneratedDocument.id == document_id,
            GeneratedDocument.firm_id == firm_id
        ).first()
        
        if not doc:
            raise ValueError(f"Document {document_id} not found or not accessible")
        
        return doc
    
    def list_documents(
        self,
        firm_id: int,
        db: Session,
        status: Optional[DraftStatus] = None,
        document_type: Optional[LegalDocumentType] = None,
        expediente_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[GeneratedDocument]:
        """
        List generated documents with filtering and tenant isolation.
        
        Args:
            firm_id: Firm ID for tenant isolation
            db: Database session
            status: Optional status filter
            document_type: Optional document type filter
            expediente_id: Optional case ID filter
            limit: Maximum number of results
            offset: Pagination offset
        
        Returns:
            List of GeneratedDocument instances
        """
        query = db.query(GeneratedDocument).filter(
            GeneratedDocument.firm_id == firm_id
        )
        
        if status:
            query = query.filter(GeneratedDocument.status == status)
        
        if document_type:
            query = query.filter(GeneratedDocument.document_type == document_type)
        
        if expediente_id:
            query = query.filter(GeneratedDocument.expediente_id == expediente_id)
        
        query = query.order_by(GeneratedDocument.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        return query.all()
