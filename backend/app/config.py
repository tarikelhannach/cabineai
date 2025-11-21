# backend/app/config.py - Configuración Simplificada

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    """Configuración básica del sistema"""
    
    def __init__(self):
        # Información del sistema
        self.app_name = os.getenv("APP_NAME", "Sistema Judicial Digital - Marruecos")
        self.app_version = os.getenv("APP_VERSION", "1.0.0")
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        
        # Base de datos
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./test.db")
        
        # Redis
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        # Seguridad
        secret_key = os.getenv("SECRET_KEY")
        if not secret_key:
            if self.environment == "production":
                raise ValueError(
                    "SECRET_KEY is required in production. "
                    "Set SECRET_KEY environment variable to a secure random string (minimum 32 characters)."
                )
            secret_key = "test-secret-key-minimum-32-characters"
        elif len(secret_key) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        self.secret_key = secret_key
        
        self.algorithm = os.getenv("ALGORITHM", "HS256")
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
        self.refresh_token_expire_days = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
        
        # CORS - Strict in production
        if self.environment == "production":
            allowed_origins = os.getenv("ALLOWED_ORIGINS")
            if not allowed_origins:
                raise ValueError(
                    "ALLOWED_ORIGINS is required in production. "
                    "Set ALLOWED_ORIGINS environment variable to comma-separated list of allowed origins."
                )
            self.allowed_origins = allowed_origins
        else:
            self.allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8080")
        
        self.allowed_hosts = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1")
        
        # Rate limiting
        self.rate_limit_per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
        self.rate_limit_per_hour = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))
        
        # Configuración específica para Marruecos
        self.morocco_timezone = os.getenv("MOROCCO_TIMEZONE", "Africa/Casablanca")
        self.default_language = os.getenv("DEFAULT_LANGUAGE", "ar")
        
        # OCR
        self.ocr_languages = os.getenv("OCR_LANGUAGES", "ara+fra+spa")
        
        # HSM
        self.hsm_type = os.getenv("HSM_TYPE", "software_fallback")
        
        # Auditoría
        self.enable_audit_logging = os.getenv("ENABLE_AUDIT_LOGGING", "true").lower() == "true"

        # Email / SMTP
        self.smtp_host = os.getenv("SMTP_HOST")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.smtp_tls = os.getenv("SMTP_TLS", "true").lower() == "true"

# Singleton
settings = Settings()
