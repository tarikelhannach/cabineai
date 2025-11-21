#!/usr/bin/env python3
# backend/scripts/test_ai.py - Test DeepSeek AI Integration

"""
Test script for DeepSeek AI service.
Tests API connection, classification, metadata extraction, and summarization.

Usage:
    cd backend
    python scripts/test_ai.py
"""

import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.services.ai_service import ai_service
from app.config import settings


# Sample legal texts for testing
SAMPLE_TEXTS = {
    "contrat_fr": """
CONTRAT DE LOCATION
Entre les soussignés:
- M. Ahmed BENALI, propriétaire, demeurant à Casablanca
- Mme. Fatima ALAMI, locataire, demeurant à Rabat

Il a été convenu ce qui suit:
Article 1: Le propriétaire loue à la locataire un appartement situé au 123 Avenue Mohammed V, Casablanca.
Article 2: Le loyer mensuel est fixé à 5000 MAD (cinq mille dirhams).
Article 3: La durée du bail est de 12 mois à compter du 1er janvier 2024.

Fait à Casablanca, le 15 décembre 2023
""",
    
    "jugement_ar": """
المملكة المغربية
المحكمة الابتدائية بالدار البيضاء

حكم رقم: 2024/123
بتاريخ: 15 يناير 2024

القضية المدنية رقم: 456/2023

الأطراف:
المدعي: السيد محمد الإدريسي
المدعى عليه: شركة البناء المغربية

الموضوع: المطالبة بمبلغ 100,000 درهم

الحكم:
بعد الاطلاع على الوثائق والاستماع للطرفين، تقرر المحكمة:
1. إلزام المدعى عليه بدفع مبلغ 100,000 درهم للمدعي
2. تحميل المدعى عليه المصاريف القضائية

صدر الحكم علنا في 15 يناير 2024
""",
    
    "facture_fr": """
FACTURE N° 2024-001

Société: Cabinet Juridique Marocain
Adresse: 45 Rue Hassan II, Rabat
Tél: +212 5 37 12 34 56

Client: M. Youssef TAZI
Date: 20 janvier 2024
Date d'échéance: 20 février 2024

Prestations:
- Consultation juridique (3 heures) .......... 3,000 MAD
- Rédaction de contrat ...................... 2,500 MAD
- Frais de dossier .......................... 500 MAD

Total HT: 6,000 MAD
TVA (20%): 1,200 MAD
Total TTC: 7,200 MAD

Paiement par virement bancaire
"""
}


async def test_ai_service():
    """Test all AI service capabilities."""
    
    print("=" * 70)
    print("🧪 TESTING DEEPSEEK AI SERVICE")
    print("=" * 70)
    print()
    
    # Check configuration
    print("📋 Configuration:")
    print(f"   API Key: {'✅ Configured' if settings.ai_api_key else '❌ Missing'}")
    print(f"   Base URL: {settings.ai_base_url}")
    print(f"   Model: {settings.ai_model}")
    print(f"   Timeout: {settings.ai_timeout}s")
    print(f"   Service Enabled: {'✅ Yes' if ai_service.is_enabled() else '❌ No'}")
    print()
    
    if not ai_service.is_enabled():
        print("❌ ERROR: AI service not configured!")
        print("   Please set AI_API_KEY in your .env file")
        print("   Get your API key from: https://platform.deepseek.com")
        return
    
    # Test each sample document
    for doc_type, text in SAMPLE_TEXTS.items():
        print("-" * 70)
        print(f"📄 Testing: {doc_type}")
        print("-" * 70)
        print()
        
        # Test classification
        print("1️⃣ Classification:")
        classification = await ai_service.classify_document(text)
        if classification:
            print(f"   ✅ Result: {classification}")
        else:
            print("   ❌ Failed")
        print()
        
        # Test metadata extraction
        print("2️⃣ Metadata Extraction:")
        metadata = await ai_service.extract_metadata(text)
        if metadata:
            print("   ✅ Extracted:")
            for key, value in metadata.items():
                print(f"      - {key}: {value}")
        else:
            print("   ❌ Failed")
        print()
        
        # Test summarization
        print("3️⃣ Summarization:")
        summary = await ai_service.summarize_document(text)
        if summary:
            print(f"   ✅ Summary:")
            print(f"      {summary}")
        else:
            print("   ❌ Failed")
        print()
    
    # Test parallel processing
    print("=" * 70)
    print("🚀 Testing Parallel Processing (all 3 operations at once)")
    print("=" * 70)
    print()
    
    test_text = SAMPLE_TEXTS["contrat_fr"]
    results = await ai_service.process_document(test_text)
    
    print("Results:")
    print(f"   Classification: {results.get('classification', 'N/A')}")
    print(f"   Metadata: {len(results.get('metadata', {}))} fields extracted")
    print(f"   Summary: {len(results.get('summary', ''))} characters")
    if results.get('error'):
        print(f"   ⚠️ Errors: {results['error']}")
    else:
        print("   ✅ No errors")
    print()
    
    print("=" * 70)
    print("✅ AI SERVICE TEST COMPLETED")
    print("=" * 70)


def main():
    """Main entry point."""
    try:
        asyncio.run(test_ai_service())
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
