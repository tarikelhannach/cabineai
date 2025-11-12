# JusticeAI Commercial - Multi-Tenant SaaS Platform

### Overview
This project is a multi-tenant SaaS platform for law firms, transitioning from the governmental JusticeAI system. It provides a FastAPI backend and React frontend designed for commercial use by over 600 independent law firms. Key features include complete tenant isolation, subscription billing, document digitization with OCR, multi-language support (French, Arabic, English), and secure case management. The platform operates on a subscription model with implementation and per-lawyer monthly fees, aiming to optimize legal workflows and significantly reduce document processing times.

### User Preferences
- **Languages**: Multi-language support (French as default, Arabic, English)
- **UI Framework**: Material-UI with modern design
- **Theme**: Dark/Light mode with purple gradient
- **Authentication**: JWT-based with localStorage persistence and firm-based tenant isolation
- **RTL Support**: Automatic RTL layout for Arabic language
- **Language Persistence**: Selected language stored in localStorage
- **Commercial Roles**: Admin (firm owner), Lawyer (attorney), Assistant (paralegal)

### System Architecture
The system employs a decoupled multi-tenant architecture focused on firm-level data isolation, subscription management, and commercial scalability.

#### UI/UX Decisions
The frontend features a responsive, modern design with a purple gradient theme, glassmorphism effects, and dark/light modes. It includes role-specific dashboards, multi-language support with `react-i18next`, full Right-to-Left (RTL) layout for Arabic, and WCAG 2.1 AA compliance for accessibility.

#### Technical Implementations
- **Frontend**: React 18, Vite, Material-UI v5, React Router v6, Axios, `react-i18next`.
- **Backend**: FastAPI, Python 3.11, SQLAlchemy, PostgreSQL.
- **Multi-Tenancy**: Firm-based isolation with `TenantMiddleware` and `LanguageMiddleware`.
- **Billing & Subscriptions**: `BillingService` for fee calculation, invoicing, and subscription validation.
- **Authentication**: JWT-based with `python-jose`, `passlib[bcrypt]`, 2FA, and firm-scoped tokens.
- **Role-Based Access Control (RBAC)**: Granular access for Admin, Lawyer, and Assistant roles on both frontend and backend.
- **Expediente Management**: Commercial case management with client, matter, and lawyer assignments, and RBAC.
- **Document Management**: Secure upload/download, OCR processing, Elasticsearch indexing, and subscription validation.
- **Internationalization**: Dynamic language switching and RTL adjustments for French, Arabic, and English.
- **OCR Processing**: Multi-engine system using QARI-OCR, EasyOCR, and Tesseract.
- **Search**: Elasticsearch for full-text search with fuzzy matching and multi-language support.
- **Digital Signatures**: HSM-based document signing (PKCS#11, Azure Key Vault, Software fallback).
- **CI/CD Pipeline**: Automated testing, security scanning, and deployment via GitHub Actions with quality gates.
- **Audit Logging**: Comprehensive logging of user actions in PostgreSQL.
- **Rate Limiting**: Implemented with SlowAPI.

#### Artificial Intelligence Architecture
The AI architecture leverages **GPT-4o** for its superior Arabic language performance and multimodal capabilities.
- **Deployment Strategy**: Currently using OpenAI API with Zero Data Retention, transitioning to Azure OpenAI Service (France Central) for production and potentially a hybrid model for enterprise.
- **AI Capabilities**:
    1.  **Automatic Document Classification**: Classifies document type, legal area, parties, dates, and urgency using OCR extraction and GPT-4o analysis, saving significant time.
    2.  **Intelligent Chat (RAG)**: Natural language search across documents and cases with multi-language support, semantic search, source citations, and relevance scoring.
    3.  **Legal Document Drafting Assistant**: Generates various legal document drafts in Arabic following Moroccan legal standards, with a review and approval workflow.
- **Security Measures**: Zero Data Retention, PII anonymization, tenant isolation, prompt injection protection, hallucination mitigation (RAG-only, citations, human review), incident response, and GDPR compliance.
- **Performance Optimizations**:
    - **Caching & Model Routing**: LRU cache for embeddings and classification, and intelligent model selection (GPT-4o-mini for previews, GPT-4o for final outputs) to optimize cost and performance. Integrated Moroccan legal knowledge into prompts.
    - **Async Processing Pipeline**: `AsyncOCRService` for parallel multi-page PDF processing and `AsyncEmbeddingService` for batch embedding generation, both leveraging ThreadPoolExecutor and semaphore backpressure for efficiency. Includes Celery integration for async/sync fallback.
    - **Metrics & Monitoring System**: `MetricsService` with sharded locks, reservoir sampling, and lazy percentile computation to collect performance metrics (OCR, embeddings, cache hit rates, AI service performance) without bottlenecks, supporting 600 concurrent tenants.
- **Load Testing Infrastructure**: Locust configuration simulating 600 law firms and 1500 concurrent users across various commercial roles and scenarios (OCR load, RAG chat, embedding generation, document drafting), aiming for significant latency reduction and OCR/embedding speedup.

#### System Design Choices
- **Microservices-oriented**: Clear separation between frontend and backend.
- **Scalability**: Configured for Autoscale deployment.
- **Security-first**: Emphasizes JWT, RBAC, field-level permissions, deny-by-default, and rate limiting.
- **Localization**: Robust multi-language and RTL support.
- **AI-Enhanced**: Integration of GPT-4o for document classification, intelligent search, and drafting assistance.

### External Dependencies

#### Backend
- **Framework**: `fastapi`, `uvicorn`
- **Database ORM**: `sqlalchemy`
- **Database Driver**: `psycopg2-binary` (PostgreSQL)
- **Authentication**: `python-jose[cryptography]`, `passlib[bcrypt]`, `pyotp`, `qrcode[pil]`
- **Rate Limiting**: `slowapi`
- **Caching**: `redis`
- **OCR**: `pytesseract`, `pdf2image`, `PyMuPDF`, `Pillow`, `easyocr`
- **AI/ML**: `transformers`, `torch`, `accelerate`, `bitsandbytes`, `qwen-vl-utils`, `opencv-python-headless`

#### Frontend
- **Framework**: `react`, `react-dom`, `vite`
- **UI Library**: `@mui/material`, `@emotion/react`, `@emotion/styled`, `@mui/icons-material`
- **Routing**: `react-router-dom`
- **HTTP Client**: `axios`
- **Internationalization**: `i18next`, `react-i18next`, `i18next-browser-languagedetector`