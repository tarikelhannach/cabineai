# ⚖️ CabineAI - Intelligent Legal SaaS for Morocco

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-Commercial-green)
![Python](https://img.shields.io/badge/python-3.11-blue)
![React](https://img.shields.io/badge/react-18.2-blue)
![Docker](https://img.shields.io/badge/docker-ready-blue)

**The ultimate digital assistant for Moroccan Lawyers: Digitize, Categorize, and Automate.**

[Features](#features) •
[Installation](#installation) •
[Tech Stack](#tech-stack) •
[Support](#support)

</div>

---

## 📋 Overview

**CabineAI** is a cutting-edge SaaS platform designed specifically for **Moroccan lawyers and law firms**. It solves the chaos of paper archives by providing a complete solution to **digitize, categorize, and manage** legal documents with the power of Artificial Intelligence.

Unlike generic tools, CabineAI is built for the **Moroccan legal context**, supporting Arabic, French, and Spanish with native RTL layouts and specialized legal AI models.

### 🎯 Core Value Proposition

- **📄 Digitalize Everything**: Convert physical archives into searchable digital assets with **100% accurate Arabic OCR** (featuring Human-in-the-Loop verification).
- **🤖 AI Categorization**: Automatically classify documents (judgments, contracts, evidence) using advanced LLMs.
- **🧠 Legal AI Assistant**: Chat with your documents and draft legal texts using an AI trained on Moroccan law.
- **🔒 Secure & Compliant**: Enterprise-grade security for sensitive client data.

---

## ✨ Key Features

### 1. Intelligent Document Digitalization
- **High-Accuracy OCR**: Specialized engines (QARI) for Arabic, plus French and Spanish support.
- **Human-in-the-Loop Verification**: A dedicated split-screen interface to review and correct OCR output, ensuring **100% accuracy** for critical files.
- **Full-Text Search**: Instantly find any document by content, not just filename.

### 2. AI-Powered Organization
- **Auto-Categorization**: The system reads your documents and tags them by type, legal area, urgency, and parties involved.
- **Smart Summaries**: Get instant AI summaries of long legal texts.
- **Entity Extraction**: Automatically extract dates, names, and amounts.

### 3. LLM Legal Assistant
- **Contextual Chat**: Ask questions about your cases and get answers based on your uploaded documents (RAG).
- **Drafting Assistant**: Generate legal drafts, contracts, and correspondence using custom templates.
- **Multi-Language**: Seamlessly switch between Arabic and French.

### 4. Practice Management
- **Case Files (Dossiers)**: Organize documents by client and case.
- **Role-Based Access**: Manage permissions for partners, associates, and secretaries.
- **Audit Logs**: Track every action for security and accountability.

---

## 🏗️ Tech Stack

Built with a modern, scalable architecture to ensure speed and reliability.

### Backend
- **Framework**: FastAPI (Python 3.11)
- **AI/LLM**: OpenAI GPT-4o, QARI-OCR, Tesseract
- **Database**: PostgreSQL 15 (with pgvector for AI search)
- **Search**: Elasticsearch 8.11
- **Queue**: Celery + Redis

### Frontend
- **Framework**: React 18 + Vite
- **UI Library**: Material-UI (MUI) v5
- **Languages**: Full i18n support (AR/FR/ES) with automatic RTL.

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Security**: JWT Auth, Rate Limiting, HSM Integration

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- OpenAI API Key (for AI features)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/cabineai/platform.git
cd cabineai

# 2. Configure environment
cp .env.example .env
# Edit .env to add your OPENAI_API_KEY and DB credentials

# 3. Start the platform
docker-compose up -d

# 4. Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs
```

---

## 🔒 Security & Privacy

We take client confidentiality seriously.
- **Data Isolation**: Multi-tenant architecture ensures your firm's data is strictly isolated.
- **Encryption**: All data is encrypted at rest and in transit.
- **Audit Trails**: Complete history of who accessed or modified any document.

---

## 📞 Contact & Support

For sales inquiries or technical support:
- **Email**: contact@cabineai.ma
- **Web**: www.cabineai.ma

---

<div align="center">
Made with ❤️ for the Moroccan Legal Community
</div>
