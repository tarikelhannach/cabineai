# backend/app/services/ai_service.py - DeepSeek AI Integration

import asyncio
import json
import logging
from typing import Dict, Optional, Any
from openai import AsyncOpenAI
from ..config import settings

logger = logging.getLogger(__name__)


class AIService:
    """
    AI Service for intelligent legal document analysis using DeepSeek-V3.
    
    Provides three core capabilities:
    1. Document Classification (Contrat, Jugement, Facture, etc.)
    2. Metadata Extraction (Parties, Dates, Case Numbers, Amounts)
    3. Document Summarization (in original language: Arabic or French)
    """
    
    def __init__(self):
        """Initialize DeepSeek client with configuration from settings."""
        if not settings.ai_api_key:
            logger.warning("AI_API_KEY not configured. AI features will be disabled.")
            self.client = None
        else:
            self.client = AsyncOpenAI(
                api_key=settings.ai_api_key,
                base_url=settings.ai_base_url,
                timeout=settings.ai_timeout
            )
        
        self.model = settings.ai_model
        logger.info(f"AIService initialized with model: {self.model}")
    
    def is_enabled(self) -> bool:
        """Check if AI service is properly configured."""
        return self.client is not None
    
    async def classify_document(self, text: str) -> Optional[str]:
        """
        Classify legal document into predefined categories.
        
        Args:
            text: Extracted text from OCR
            
        Returns:
            Classification string (Contrat, Jugement, Facture, Statuts, Autre)
            or None if classification fails
        """
        if not self.is_enabled():
            logger.warning("AI service not enabled. Skipping classification.")
            return None
        
        try:
            # Truncate text to avoid token limits (first 4000 chars should be enough)
            truncated_text = text[:4000] if len(text) > 4000 else text
            
            # System prompt optimized for context caching (consistent across calls)
            system_prompt = """Eres un experto legal en leyes de Marruecos. 
Clasifica el documento en UNA de estas categorías exactas:
- Contrat (contrato)
- Jugement (sentencia/fallo judicial)
- Facture (factura)
- Statuts (estatutos sociales)
- Procuration (poder notarial)
- Demande (demanda judicial)
- Autre (otro tipo de documento)

Responde SOLO con el nombre de la categoría, sin explicaciones adicionales."""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Clasifica este documento:\n\n{truncated_text}"}
                ],
                temperature=0.1,  # Low temperature for consistent classification
                max_tokens=20
            )
            
            classification = response.choices[0].message.content.strip()
            logger.info(f"Document classified as: {classification}")
            return classification
            
        except Exception as e:
            # Handle rate limits with exponential backoff
            if "429" in str(e) or "rate_limit" in str(e).lower():
                logger.warning(f"Rate limit hit during classification: {str(e)}")
                # Let Celery handle retry with exponential backoff
                raise
            logger.error(f"Classification failed: {str(e)}")
            return None
    
    async def extract_metadata(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract structured metadata from legal document.
        
        Args:
            text: Extracted text from OCR
            
        Returns:
            Dictionary with extracted entities:
            {
                "parties": ["Partie A", "Partie B"],
                "dates": ["2024-01-15", "2024-06-30"],
                "case_number": "123/2024",
                "amounts": [{"value": 50000, "currency": "MAD"}],
                "language": "ar" or "fr"
            }
        """
        if not self.is_enabled():
            logger.warning("AI service not enabled. Skipping metadata extraction.")
            return None
        
        try:
            # Truncate text
            truncated_text = text[:6000] if len(text) > 6000 else text
            
            system_prompt = """Eres un experto en análisis de documentos legales de Marruecos.
Extrae las entidades clave del texto legal en formato JSON estricto.

Si el texto está en العربية (árabe), extrae los valores en su idioma original.
Si el texto está en français, extrae los valores en francés.

Devuelve un JSON con esta estructura exacta:
{
  "parties": ["lista de partes involucradas"],
  "dates": ["lista de fechas en formato YYYY-MM-DD si es posible"],
  "case_number": "número de caso/expediente si existe",
  "amounts": [{"value": número, "currency": "MAD/EUR/USD"}],
  "language": "ar" o "fr",
  "location": "ciudad/tribunal si se menciona"
}

Si no encuentras algún campo, usa null o lista vacía []."""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Extrae metadata de este documento:\n\n{truncated_text}"}
                ],
                temperature=0.2,
                max_tokens=500,
                response_format={"type": "json_object"}  # Force JSON mode
            )
            
            metadata_str = response.choices[0].message.content
            metadata = json.loads(metadata_str)
            
            logger.info(f"Metadata extracted: {len(metadata)} fields")
            return metadata
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse metadata JSON: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Metadata extraction failed: {str(e)}")
            return None
    
    async def summarize_document(self, text: str) -> Optional[str]:
        """
        Generate executive summary of legal document.
        
        Args:
            text: Extracted text from OCR
            
        Returns:
            Concise summary in the same language as the source document
        """
        if not self.is_enabled():
            logger.warning("AI service not enabled. Skipping summarization.")
            return None
        
        try:
            # Truncate text
            truncated_text = text[:8000] if len(text) > 8000 else text
            
            system_prompt = """Eres un experto legal especializado en documentos de Marruecos.

Genera un resumen ejecutivo conciso del documento legal.

IMPORTANTE:
1. Detecta el idioma principal (العربية árabe o Français francés)
2. Responde en ese MISMO idioma
3. El resumen debe ser de 3-5 frases máximo
4. Incluye: tipo de documento, partes principales, objeto/propósito, fechas clave

Si el documento está en árabe, responde en árabe.
Si el documento está en francés, responde en francés."""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Resume este documento:\n\n{truncated_text}"}
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            summary = response.choices[0].message.content.strip()
            logger.info(f"Summary generated: {len(summary)} characters")
            return summary
            
        except Exception as e:
            logger.error(f"Summarization failed: {str(e)}")
            return None
    
    async def process_document(self, text: str) -> Dict[str, Any]:
        """
        Process document with all AI capabilities in parallel.
        
        Args:
            text: Extracted text from OCR
            
        Returns:
            Dictionary with all AI results:
            {
                "classification": str,
                "metadata": dict,
                "summary": str,
                "error": str (if any operation failed)
            }
        """
        if not self.is_enabled():
            return {
                "classification": None,
                "metadata": None,
                "summary": None,
                "error": "AI service not configured"
            }
        
        try:
            # Run all three operations in parallel for efficiency
            results = await asyncio.gather(
                self.classify_document(text),
                self.extract_metadata(text),
                self.summarize_document(text),
                return_exceptions=True
            )
            
            # Handle results and exceptions
            classification = results[0] if not isinstance(results[0], Exception) else None
            metadata = results[1] if not isinstance(results[1], Exception) else None
            summary = results[2] if not isinstance(results[2], Exception) else None
            
            # Collect any errors
            errors = [str(r) for r in results if isinstance(r, Exception)]
            error_msg = "; ".join(errors) if errors else None
            
            return {
                "classification": classification,
                "metadata": metadata,
                "summary": summary,
                "error": error_msg
            }
            
        except Exception as e:
            logger.error(f"Document processing failed: {str(e)}")
            return {
                "classification": None,
                "metadata": None,
                "summary": None,
                "error": str(e)
            }


# Singleton instance
ai_service = AIService()
