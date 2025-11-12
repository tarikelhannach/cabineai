# backend/app/main.py - Aplicación Principal FastAPI

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import os
from datetime import datetime
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from .middleware.rate_limit import ip_limiter, user_limiter, strict_limiter

# Setup logging básico
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuración básica para testing
class BasicSettings:
    def __init__(self):
        self.debug = os.getenv('DEBUG', 'true').lower() == 'true'
        self.environment = os.getenv('ENVIRONMENT', 'testing')
        self.allowed_origins = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000,http://localhost:8080')
        self.allowed_hosts = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1')

settings = BasicSettings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    try:
        hsm_type = os.getenv('HSM_TYPE', 'software_fallback')
        environment = os.getenv('ENVIRONMENT', 'testing')
        
        if environment == 'production' and hsm_type in ['software', 'software_fallback']:
            logger.critical("❌ PRODUCTION ENVIRONMENT DETECTED WITH SOFTWARE HSM")
            logger.critical("❌ Software HSM is NOT ALLOWED in production environments")
            logger.critical(f"❌ Current HSM type: {hsm_type}")
            logger.critical("❌ Please configure PKCS#11 or Azure Key Vault for production")
            raise ValueError(
                "CRITICAL: Software HSM cannot be used in production. "
                "Configure HSM_TYPE to 'pkcs11' or 'azure_keyvault' for production deployment."
            )
        
        if environment == 'production':
            logger.info(f"✅ Production environment validated with HSM type: {hsm_type}")
        else:
            logger.info(f"✅ {environment.capitalize()} environment started with HSM type: {hsm_type}")
        
        # Initialize Elasticsearch indices
        try:
            from .services.elasticsearch_service import get_elasticsearch_service
            es_service = get_elasticsearch_service()
            es_service.create_indices()
            logger.info("✅ Elasticsearch indices initialized successfully")
        except Exception as es_error:
            logger.warning(f"⚠️ Elasticsearch initialization failed (search disabled): {es_error}")
        
        logger.info("Sistema Judicial Digital iniciado correctamente")
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Sistema Judicial Digital cerrando...")

# Crear aplicación FastAPI
app = FastAPI(
    title="JusticeAI Commercial - Multi-Tenant Law Firm Platform",
    description="SaaS platform for law firms with OCR, document management, billing, and multi-language support (FR/AR/EN)",
    version="2.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Configure rate limiters
app.state.limiter = user_limiter
app.state.ip_limiter = ip_limiter
app.state.strict_limiter = strict_limiter

# Add rate limit exception handler
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add SlowAPI middleware for automatic rate limit headers
app.add_middleware(SlowAPIMiddleware)

# CORS configurado para Marruecos - Allow all origins in development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else settings.allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health", tags=["🏥 Health"])
async def health_check():
    """
    Health check completo del sistema
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "system": "Sistema Judicial Digital - Marruecos"
    }

# Root endpoint
@app.get("/", tags=["🏛️ System Info"])
async def root():
    """
    Información principal del sistema
    """
    return {
        "system": "Sistema Judicial Digital",
        "country": "🇲🇦 Reino de Marruecos",
        "version": "1.0.0",
        "description": "Sistema completo de digitalización judicial con compliance gubernamental",
        "features": [
            "Gestión de Casos Judiciales",
            "Procesamiento OCR Multi-idioma (AR/FR/ES)",
            "Búsqueda Semántica Avanzada",
            "Firma Digital HSM",
            "Auditoría y Compliance",
            "Escalabilidad Gubernamental",
            "Autenticación de Dos Factores (2FA)",
            "Dashboard de Administración",
            "Monitoreo en Tiempo Real"
        ],
        "api_docs": "/docs" if settings.debug else "Disponible en entorno desarrollo",
        "health": "/health"
    }

# Endpoint de métricas
@app.get("/metrics", tags=["📊 Metrics"])
async def get_metrics():
    """
    Métricas del sistema para monitoreo
    """
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "application": {
            "environment": settings.environment,
            "debug": settings.debug,
            "version": "1.0.0"
        }
    }

# Add tenant and language middleware
from .middleware.tenant import TenantMiddleware
from .middleware.language import LanguageMiddleware

app.add_middleware(TenantMiddleware)
app.add_middleware(LanguageMiddleware)

# Include routers
from .routes import auth, cases, documents, users, audit, search, signatures, billing, ai_classification, chat

app.include_router(auth.router, prefix="/api")
app.include_router(billing.router, prefix="/api")  # Billing routes for SaaS
app.include_router(cases.router, prefix="/api")
app.include_router(documents.router)
app.include_router(users.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(search.router)
app.include_router(signatures.router)
app.include_router(ai_classification.router)  # AI Classification with GPT-4o
app.include_router(chat.router)  # Chat RAG with GPT-4o

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Manejador global de excepciones
    """
    logger.error(f"Global exception on {request.url}: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": "Error interno del servidor" if not settings.debug else str(exc),
            "path": str(request.url.path),
            "timestamp": datetime.utcnow().isoformat()
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="localhost",
        port=int(os.getenv("BACKEND_PORT", 8000)),
        reload=settings.debug
    )
