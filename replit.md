# JusticeAI Commercial - Multi-Tenant SaaS Platform

### Overview
This project is a multi-tenant SaaS platform for law firms, transformed from the governmental JusticeAI system. It features a FastAPI backend and React frontend designed for commercial use by 600+ independent law firms. Key capabilities include complete tenant isolation (firm-based), subscription billing management, document digitization with OCR (50K pages), multi-language support (French, Arabic, English with RTL), and secure case (expediente) management. The platform uses a subscription model with implementation fees (20-30K MAD) and monthly per-lawyer fees (270 MAD).

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

#### System Design Choices
- **Microservices-oriented**: Clear separation between frontend and backend.
- **Scalability**: Configured for Autoscale deployment.
- **Security-first**: Emphasizes JWT, RBAC, field-level permissions, deny-by-default, and rate limiting.
- **Localization**: Robust multi-language and RTL support.

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