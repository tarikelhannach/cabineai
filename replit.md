# JusticeAI Commercial - Multi-Tenant SaaS Platform

### Overview
This project is a multi-tenant SaaS platform for law firms, transformed from the governmental JusticeAI system. It features a FastAPI backend (port 8000) and React frontend (port 5000) designed for commercial use by 600+ independent law firms. Key capabilities include complete tenant isolation (firm-based), subscription billing management with modern billing dashboard, document digitization with OCR (50K pages using QARI-OCR/EasyOCR/Tesseract), multi-language support (French, Arabic, English with RTL), and secure case (expediente) management. The platform uses a subscription model with implementation fees (20,600-30,600 MAD) and monthly per-lawyer fees (270-405 MAD).

### User Preferences
- **Languages**: Multi-language support (French as default, Arabic, English) - Spanish removed for commercial version
- **UI Framework**: Material-UI with modern design
- **Theme**: Dark/Light mode with purple gradient
- **Authentication**: JWT-based with localStorage persistence and firm-based tenant isolation
- **RTL Support**: Automatic RTL layout for Arabic language
- **Language Persistence**: Selected language stored in localStorage
- **Commercial Roles**: Admin (firm owner), Lawyer (attorney), Assistant (paralegal)

### System Architecture
The system is built with a decoupled multi-tenant architecture, prioritizing firm-level data isolation, subscription management, and commercial scalability.

#### Multi-Tenancy Implementation
- **Firm Model**: Central tenant entity with subscription management, billing configuration, and language preferences
- **Data Isolation**: All models (User, Document, Expediente, AuditLog) include firm_id foreign key with indexed filtering
- **Middleware**: TenantMiddleware ensures automatic firm_id-based query filtering; LanguageMiddleware detects Accept-Language headers
- **Subscription Validation**: BillingService validates active subscriptions before allowing operations like document uploads

#### UI/UX Decisions
The frontend features a modern, responsive design with a purple gradient theme, glassmorphism effects, and dark/light mode. It includes a responsive sidebar, dynamic content rendering, and role-specific dashboards for Admin (firm owner), Lawyer (attorney), and Assistant (paralegal) users. Multi-language support with `react-i18next` includes full Right-to-Left (RTL) layout for Arabic, with French as the default language. WCAG 2.1 AA compliance is met with skip navigation, ARIA labels, keyboard support, and verified color contrast.

#### Technical Implementations
- **Frontend**: React 18 with Vite, Material-UI (MUI) v5, React Router v6, Axios, and `react-i18next`.
- **Backend**: FastAPI, Python 3.11, SQLAlchemy for ORM, and PostgreSQL.
- **Multi-Tenancy**: Firm-based tenant isolation with TenantMiddleware and LanguageMiddleware for i18n.
- **Billing & Subscriptions**: BillingService handles fee calculation (270 MAD/lawyer/month), invoice generation, and subscription validation.
- **Authentication**: JWT-based using `python-jose` and `passlib[bcrypt]`, with 2FA (TOTP) and firm-scoped tokens.
- **Role-Based Access Control (RBAC)**: Implemented on both frontend and backend for granular access based on commercial roles (Admin, Lawyer, Assistant). Legacy governmental roles (Judge, Clerk, Citizen) kept for backward compatibility.
- **Expediente Management**: Commercial case management with client names, matter types, assigned lawyers, and RBAC.
- **Document Management**: Secure upload/download with firm_id isolation, OCR processing, Elasticsearch indexing, and subscription validation.
- **Internationalization**: Dynamic language switching and RTL adjustments for French (default), Arabic, and English. Spanish removed for commercial version.
- **OCR Processing**: Multi-engine system with automatic selection:
  - QARI-OCR (state-of-the-art Arabic, requires GPU)
  - EasyOCR (fast multi-language)
  - Tesseract (reliable fallback)
- **Search**: Elasticsearch full-text search with fuzzy matching, highlighting, and multi-language analyzers.
- **Digital Signatures**: HSM-based document signing (PKCS#11, Azure Key Vault, Software fallback).
- **CI/CD Pipeline**: Automated testing, security scanning, and deployment via GitHub Actions. Includes multi-stage pipeline, quality gates (70% backend coverage), Trivy, Safety, NPM audit, and Locust performance testing (1500 concurrent users).
- **Audit Logging**: Comprehensive logging of all user actions in PostgreSQL for security and compliance.
- **Rate Limiting**: Implemented with SlowAPI to prevent brute force attacks and spam.

#### Artificial Intelligence Architecture (Planned)
**Critical Requirement**: ALL documents are in Arabic, requiring LLM with excellent Arabic language understanding.

**Selected LLM**: **GPT-4o** (OpenAI/Azure)
- **Reasoning**: Best-in-class Arabic language performance, multimodal capabilities, 200K context window
- **Deployment Strategy**:
  - **Phase 1 (MVP)**: OpenAI API with Zero Data Retention contract
  - **Phase 2 (Production)**: Azure OpenAI Service (France Central region for GDPR compliance)
  - **Phase 3 (Enterprise)**: Hybrid model (Azure OpenAI + on-premise for ultra-sensitive cases)

**AI Capabilities** (To be implemented):
1. **Automatic Document Classification**:
   - OCR extraction → GPT-4o analysis
   - Classifies: document type, legal area, parties involved, important dates, urgency level
   - Saves 95% of time (10 min → 30 sec per document)

2. **Intelligent Chat (RAG)**:
   - Natural language search across all documents and cases
   - Multi-language support (Arabic, French, English)
   - Semantic search with embeddings (OpenAI text-embedding-3-large)
   - Answers with source citations

3. **Legal Document Drafting Assistant**:
   - Generates drafts: meeting minutes, demands, contracts, powers of attorney
   - Arabic-language templates following Moroccan legal standards
   - Review and edit workflow for lawyer approval

4. **Semantic Search**:
   - Concept-based search (not just keywords)
   - Finds similar cases and legal precedents
   - Cross-lingual understanding

**Security Measures for AI**:
- **Zero Data Retention**: 0-day retention policy with LLM providers
- **Data Anonymization**: PII removed before sending to LLM
- **Tenant Isolation**: Hard-coded firm_id filtering in vector database queries
- **Prompt Injection Protection**: Input sanitization, system prompt locking
- **Hallucination Mitigation**: RAG-only responses, mandatory citations, human review for critical documents
- **Incident Response**: Automated detection and 4-phase response workflow
- **Compliance**: GDPR-compliant with Azure OpenAI (EU data residency)

**Technical Specifications**:
- **Cost**: ~$4,180/month for 600 firms (Azure OpenAI in France Central)
- **Latency**: P50: 2.5 seconds, P95: 5.8 seconds
- **Throughput**: 100K tokens per minute (with Azure quota)
- **Data Residency**: France Central (EU) for compliance
- **Staffing**: 1 FTE DevOps + Azure Admin

**Documentation**: See `JUSTICEAI_COMMERCIAL_TECHNICAL_SPECIFICATION.md` for complete technical details, security analysis, cost models, and implementation roadmap.

#### System Design Choices
- **Microservices-oriented**: Clear separation between frontend and backend.
- **Scalability**: Configured for Autoscale deployment.
- **Security-first**: Emphasizes JWT, RBAC, field-level permissions, deny-by-default, and rate limiting.
- **Localization**: Robust multi-language and RTL support.
- **AI-Enhanced**: Planned integration of GPT-4o for document classification, intelligent search, and drafting assistance.

### External Dependencies

#### Backend
- **Framework**: `fastapi`, `uvicorn`
- **Database ORM**: `sqlalchemy`
- **Database Driver**: `psycopg2-binary` (PostgreSQL)
- **Authentication**: `python-jose[cryptography]`, `passlib[bcrypt]`, `pyotp`, `qrcode[pil]`
- **File Handling**: `python-multipart`
- **Data Validation**: `pydantic[email]`
- **Rate Limiting**: `slowapi`
- **Caching**: `redis`
- **OCR (Basic)**: `pytesseract`, `pdf2image`, `PyMuPDF`, `Pillow`
- **OCR (Advanced - Optional)**: `transformers`, `torch`, `accelerate`, `bitsandbytes`, `qwen-vl-utils`, `easyocr`, `opencv-python-headless`
- **Testing/Dev**: `pytest`, `pytest-cov`, `pytest-asyncio`, `black`, `flake8`, `isort`, `mypy`, `locust`

#### Frontend
- **Framework**: `react`, `react-dom`, `vite`
- **UI Library**: `@mui/material`, `@emotion/react`, `@emotion/styled`, `@mui/icons-material`
- **Routing**: `react-router-dom`
- **HTTP Client**: `axios`
- **Internationalization**: `i18next`, `react-i18next`, `i18next-browser-languagedetector`