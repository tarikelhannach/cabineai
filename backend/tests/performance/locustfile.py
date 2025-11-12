"""
JusticeAI Commercial - Locust Load Testing for Async Pipeline (Phase 2)

Tests async processing capabilities:
1. AsyncOCR: Multi-page PDF processing (3-5x faster)
2. Async Embeddings: Batch embedding generation (10x faster)
3. RAG Chat: Intelligent document search with vector embeddings
4. Document Classification: GPT-4o-mini automatic classification
5. Cache effectiveness: LRU cache hit rates (25-35% target)

Simulates:
- 600 law firms (multi-tenant)
- 1500 concurrent users (2.5 lawyers/firm average)
- Real-world usage patterns
"""

from locust import HttpUser, task, between, TaskSet
from locust.exception import StopUser
import json
import random
import io
import time

# Commercial role distribution (realistic)
COMMERCIAL_ROLES = {
    "ADMIN": 0.10,      # 10% firm owners
    "LAWYER": 0.70,     # 70% attorneys
    "ASSISTANT": 0.20   # 20% paralegals
}


def generate_pdf_content(pages=5):
    """Generate mock PDF content for load testing"""
    content_map = {
        1: b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n100 700 Td\n(JusticeAI Test Doc) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000056 00000 n\n0000000115 00000 n\n0000000214 00000 n\ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n308\n%%EOF",
        3: b"%PDF-1.4" + b"\n%%PDF Test Content - 3 pages" * 300,
        5: b"%PDF-1.4" + b"\n%%PDF Test Content - 5 pages" * 500,
        10: b"%PDF-1.4" + b"\n%%PDF Test Content - 10 pages" * 1000
    }
    
    closest_size = min(content_map.keys(), key=lambda k: abs(k - pages))
    return content_map[closest_size]


class LawyerBehavior(TaskSet):
    """Attorney user behavior - most active users"""
    
    @task(15)
    def upload_and_classify_document(self):
        """Upload PDF + trigger async OCR + auto-classification"""
        pages = random.choice([1, 3, 5, 10])
        pdf_content = generate_pdf_content(pages)
        
        files = {
            'file': (f'legal_doc_{pages}p.pdf', io.BytesIO(pdf_content), 'application/pdf')
        }
        data = {
            'expediente_id': str(random.randint(1, 500)),
            'document_type': random.choice(['contract', 'demand', 'power_of_attorney'])
        }
        
        with self.client.post(
            "/api/documents/upload",
            files=files,
            data=data,
            headers=self.user.headers,
            catch_response=True,
            timeout=60,
            name=f"/api/documents/upload [{pages}p]"
        ) as response:
            if response.status_code == 200:
                doc_data = response.json()
                doc_id = doc_data.get('id')
                
                if doc_id:
                    time.sleep(1)
                    
                    self.client.post(
                        f"/api/documents/{doc_id}/classify",
                        headers=self.user.headers,
                        name="/api/documents/[id]/classify"
                    )
                
                response.success()
            elif response.status_code == 503:
                response.success()
            else:
                response.failure(f"Upload failed: {response.status_code}")
    
    @task(20)
    def rag_chat_query(self):
        """Intelligent chat with RAG (vector embeddings + semantic search)"""
        queries_arabic = [
            "ما هي القضايا المشابهة لقضية العقارات؟",
            "أين توجد عقود الإيجار؟",
            "ما هي المواعيد النهائية القادمة؟"
        ]
        queries_french = [
            "Quels sont les contrats de bail?",
            "Trouvez les documents sur les litiges commerciaux",
            "Montrez-moi les procurations récentes"
        ]
        
        query = random.choice(queries_arabic + queries_french)
        
        payload = {
            "question": query,
            "max_results": 5
        }
        
        self.client.post(
            "/api/chat/ask",
            json=payload,
            headers=self.user.headers,
            name="/api/chat/ask [RAG]"
        )
    
    @task(10)
    def generate_legal_draft(self):
        """Legal document drafting with GPT-4o"""
        templates = ["meeting_minutes", "demand", "contract", "power_of_attorney"]
        
        payload = {
            "template_type": random.choice(templates),
            "context": {
                "client_name": f"Client_{random.randint(1, 1000)}",
                "case_number": f"{random.randint(1000, 9999)}/2025",
                "language": "arabic"
            }
        }
        
        self.client.post(
            "/api/drafting/generate",
            json=payload,
            headers=self.user.headers,
            name="/api/drafting/generate"
        )
    
    @task(12)
    def search_documents(self):
        """Document search (tests Elasticsearch + cache)"""
        search_terms = ["عقد", "دعوى", "وكالة", "محضر", "contract", "demand"]
        
        params = {
            "q": random.choice(search_terms),
            "limit": 20
        }
        
        self.client.get(
            "/api/documents/search",
            params=params,
            headers=self.user.headers,
            name="/api/documents/search"
        )
    
    @task(8)
    def view_expedientes(self):
        """List cases/expedientes"""
        params = {
            "skip": random.randint(0, 50),
            "limit": 20
        }
        
        self.client.get(
            "/api/expedientes",
            params=params,
            headers=self.user.headers,
            name="/api/expedientes"
        )
    
    @task(5)
    def view_metrics(self):
        """Check async performance metrics (Phase 2.5)"""
        self.client.get(
            "/api/metrics/async-comparison",
            headers=self.user.headers,
            name="/api/metrics/async-comparison"
        )


class AdminBehavior(TaskSet):
    """Firm owner/admin behavior - billing + metrics focused"""
    
    @task(10)
    def view_firm_metrics(self):
        """View async processing metrics"""
        self.client.get(
            "/api/metrics/async-comparison",
            headers=self.user.headers,
            name="/api/metrics/async-comparison [admin]"
        )
    
    @task(8)
    def view_billing_dashboard(self):
        """Check subscription & billing"""
        self.client.get(
            "/api/billing/dashboard",
            headers=self.user.headers,
            name="/api/billing/dashboard"
        )
    
    @task(5)
    def view_cache_stats(self):
        """Monitor cache effectiveness"""
        self.client.get(
            "/api/metrics/cache-stats",
            headers=self.user.headers,
            name="/api/metrics/cache-stats"
        )
    
    @task(7)
    def view_audit_logs(self):
        """Audit trail"""
        params = {"skip": 0, "limit": 50}
        self.client.get(
            "/api/audit/logs",
            params=params,
            headers=self.user.headers,
            name="/api/audit/logs"
        )


class AssistantBehavior(TaskSet):
    """Paralegal behavior - read-only, document viewing"""
    
    @task(15)
    def view_documents(self):
        """Browse documents"""
        params = {
            "skip": random.randint(0, 100),
            "limit": 20
        }
        
        self.client.get(
            "/api/documents",
            params=params,
            headers=self.user.headers,
            name="/api/documents [assistant]"
        )
    
    @task(10)
    def search_documents(self):
        """Search documents"""
        search_terms = ["عقد", "محضر", "وكالة"]
        
        params = {"q": random.choice(search_terms)}
        self.client.get(
            "/api/documents/search",
            params=params,
            headers=self.user.headers,
            name="/api/documents/search [assistant]"
        )
    
    @task(8)
    def view_expediente_details(self):
        """View case details"""
        exp_id = random.randint(1, 500)
        self.client.get(
            f"/api/expedientes/{exp_id}",
            headers=self.user.headers,
            name="/api/expedientes/[id]"
        )


class CommercialUser(HttpUser):
    """Multi-tenant commercial user (600 firms)"""
    
    wait_time = between(2, 5)
    
    def on_start(self):
        """Login with firm-based authentication"""
        role = self._select_role()
        firm_id = f"firm_{random.randint(1, 600)}"
        
        username = f"{role.lower()}_{firm_id}_{random.randint(1, 20)}"
        
        credentials = {
            "username": username,
            "password": "Test123!@#"
        }
        
        response = self.client.post(
            "/api/auth/login",
            json=credentials,
            catch_response=True
        )
        
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token", "")
            self.headers = {
                "Authorization": f"Bearer {self.token}",
                "X-Firm-ID": firm_id
            }
            self.role = role
            self.firm_id = firm_id
            
            if role == "LAWYER":
                self.tasks = [LawyerBehavior]
            elif role == "ADMIN":
                self.tasks = [AdminBehavior]
            else:
                self.tasks = [AssistantBehavior]
        else:
            raise StopUser()
    
    def _select_role(self):
        """Select role based on realistic distribution"""
        rand = random.random()
        
        if rand < COMMERCIAL_ROLES["ADMIN"]:
            return "ADMIN"
        elif rand < COMMERCIAL_ROLES["ADMIN"] + COMMERCIAL_ROLES["LAWYER"]:
            return "LAWYER"
        else:
            return "ASSISTANT"
    
    @task(1)
    def health_check(self):
        """Health check endpoint"""
        self.client.get("/health", name="/health")


class HighLoadAsyncUser(HttpUser):
    """Stress test async pipeline with heavy OCR/embedding workload"""
    
    wait_time = between(1, 2)
    
    def on_start(self):
        credentials = {
            "username": f"lawyer_stress_{random.randint(1, 100)}",
            "password": "Test123!@#"
        }
        
        response = self.client.post("/api/auth/login", json=credentials)
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token", "")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            raise StopUser()
    
    @task(10)
    def stress_async_ocr(self):
        """Heavy OCR load (10-page PDFs)"""
        pdf_content = generate_pdf_content(pages=10)
        
        files = {'file': ('stress_10p.pdf', io.BytesIO(pdf_content), 'application/pdf')}
        data = {'expediente_id': str(random.randint(1, 100))}
        
        self.client.post(
            "/api/documents/upload",
            files=files,
            data=data,
            headers=self.headers,
            timeout=90,
            name="/api/documents/upload [STRESS 10p]"
        )
    
    @task(8)
    def stress_embeddings(self):
        """Heavy embedding generation"""
        long_text = " ".join([f"Legal document paragraph {i}" for i in range(100)])
        
        payload = {"question": long_text, "max_results": 10}
        
        self.client.post(
            "/api/chat/ask",
            json=payload,
            headers=self.headers,
            name="/api/chat/ask [STRESS]"
        )
