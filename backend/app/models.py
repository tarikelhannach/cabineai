# backend/app/models.py - Multi-Tenant Commercial Models

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Enum, ForeignKey, Float, Date, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import enum

Base = declarative_base()

class SubscriptionTier(enum.Enum):
    BASIC = "basic"
    COMPLETE = "complete"

class SubscriptionStatus(enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    TRIAL = "trial"

class InvoiceStatus(enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"

class LanguagePreference(enum.Enum):
    ENGLISH = "en"
    FRENCH = "fr"
    ARABIC = "ar"

class UserRole(enum.Enum):
    # Commercial roles (active)
    ADMIN = "admin"
    LAWYER = "lawyer"
    ASSISTANT = "assistant"
    
    # Legacy governmental roles (deprecated, for backward compatibility)
    JUDGE = "judge"
    CLERK = "clerk"
    CITIZEN = "citizen"

class CaseStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    ARCHIVED = "archived"

# Enums adicionales requeridos por los esquemas Pydantic
class CaseType(enum.Enum):
    CIVIL = "civil"
    CRIMINAL = "criminal"
    ADMINISTRATIVE = "administrative"
    COMMERCIAL = "commercial"
    FAMILY = "family"

class Priority(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class DocumentType(enum.Enum):
    EVIDENCE = "evidence"
    RULING = "ruling"
    MOTION = "motion"
    BRIEF = "brief"
    OTHER = "other"

class SignatureStatus(enum.Enum):
    PENDING = "pending"
    SIGNED = "signed"
    FAILED = "failed"

class LegalDocumentType(enum.Enum):
    ACTA = "acta"
    DEMANDA = "demanda"
    CONTRATO = "contrato"
    PODER = "poder"
    ESCRITO = "escrito"
    DICTAMEN = "dictamen"
    OTHER = "other"

class DraftStatus(enum.Enum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"

class Firm(Base):
    __tablename__ = "firms"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(50))
    address = Column(Text)
    
    # Subscription fields
    subscription_tier = Column(Enum(SubscriptionTier), default=SubscriptionTier.BASIC, nullable=False)
    subscription_status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.TRIAL, nullable=False)
    subscription_start = Column(Date)
    subscription_end = Column(Date)
    
    # Billing fields
    implementation_fee_paid = Column(Boolean, default=False)
    monthly_fee_per_lawyer = Column(Integer, default=270)
    stripe_customer_id = Column(String(255), nullable=True)
    stripe_subscription_id = Column(String(255), nullable=True)
    
    # Preferences
    language_preference = Column(Enum(LanguagePreference), default=LanguagePreference.FRENCH, nullable=False)
    
    # Limits
    max_users = Column(Integer, default=50)
    max_documents = Column(Integer, default=100000)
    max_storage_gb = Column(Integer, default=500)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    users = relationship("User", back_populates="firm")
    documents = relationship("Document", back_populates="firm")
    expedientes = relationship("Expediente", back_populates="firm")
    invoices = relationship("Invoice", back_populates="firm")
    subscription = relationship("Subscription", back_populates="firm", uselist=False)
    
    def __repr__(self):
        return f"<Firm(id={self.id}, name='{self.name}', status='{self.subscription_status}')>"

class Subscription(Base):
    __tablename__ = "subscriptions"
    
    firm_id = Column(Integer, ForeignKey("firms.id"), primary_key=True)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.TRIAL, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)
    plan_tier = Column(Enum(SubscriptionTier), default=SubscriptionTier.BASIC, nullable=False)
    monthly_cost = Column(Float, nullable=False)
    next_billing_date = Column(Date)
    auto_renew = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    firm = relationship("Firm", back_populates="subscription")
    
    def __repr__(self):
        return f"<Subscription(firm_id={self.firm_id}, status='{self.status}', tier='{self.plan_tier}')>"

class Invoice(Base):
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True, index=True)
    firm_id = Column(Integer, ForeignKey("firms.id"), nullable=False)
    invoice_number = Column(String(50), unique=True, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="MAD")
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.PENDING, nullable=False)
    description = Column(Text)
    paid_date = Column(Date)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    firm = relationship("Firm", back_populates="invoices")
    
    def __repr__(self):
        return f"<Invoice(id={self.id}, invoice_number='{self.invoice_number}', status='{self.status}')>"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    firm_id = Column(Integer, ForeignKey("firms.id"), nullable=False, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.LAWYER, nullable=False)
    language = Column(Enum(LanguagePreference), default=LanguagePreference.FRENCH)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    totp_secret = Column(String(32), nullable=True)
    totp_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    firm = relationship("Firm", back_populates="users")
    expedientes = relationship("Expediente", foreign_keys="Expediente.owner_id", back_populates="owner")
    documents = relationship("Document", back_populates="uploaded_by_user")
    audit_logs = relationship("AuditLog", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}', firm_id={self.firm_id})>"

class Expediente(Base):
    __tablename__ = "expedientes"
    
    id = Column(Integer, primary_key=True, index=True)
    firm_id = Column(Integer, ForeignKey("firms.id"), nullable=False, index=True)
    expediente_number = Column(String(100), index=True, nullable=False)
    client_name = Column(String(500), nullable=False)
    matter_type = Column(Enum(CaseType), default=CaseType.CIVIL, nullable=False)
    description = Column(Text)
    status = Column(Enum(CaseStatus), default=CaseStatus.PENDING, nullable=False)
    priority = Column(Enum(Priority), default=Priority.MEDIUM)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_lawyer_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    firm = relationship("Firm", back_populates="expedientes")
    owner = relationship("User", foreign_keys=[owner_id], back_populates="expedientes")
    assigned_lawyer = relationship("User", foreign_keys=[assigned_lawyer_id])
    documents = relationship("Document", back_populates="expediente")
    
    def __repr__(self):
        return f"<Expediente(id={self.id}, expediente_number='{self.expediente_number}', client='{self.client_name}', firm_id={self.firm_id})>"

# Legacy alias for backward compatibility during migration
Case = Expediente

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    firm_id = Column(Integer, ForeignKey("firms.id"), nullable=False, index=True)
    filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_size = Column(Integer)
    mime_type = Column(String(100))
    expediente_id = Column(Integer, ForeignKey("expedientes.id"))
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    ocr_processed = Column(Boolean, default=False)
    ocr_text = Column(Text)
    ocr_confidence = Column(Integer)
    ocr_language = Column(String(10))
    is_searchable = Column(Boolean, default=False)
    is_signed = Column(Boolean, default=False)
    signature_hash = Column(String(500))
    
    # Verification fields
    is_verified = Column(Boolean, default=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    
    # AI Processing fields
    ai_summary = Column(Text, nullable=True)
    ai_classification = Column(String(100), nullable=True)
    ai_metadata = Column(JSONB, nullable=True)
    ai_processed = Column(Boolean, default=False)
    ai_processed_at = Column(DateTime(timezone=True), nullable=True)
    ai_error = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    firm = relationship("Firm", back_populates="documents")
    expediente = relationship("Expediente", back_populates="documents")
    uploaded_by_user = relationship("User", back_populates="documents")
    
    def __repr__(self):
        return f"<Document(id={self.id}, filename='{self.filename}', firm_id={self.firm_id})>"

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    firm_id = Column(Integer, ForeignKey("firms.id"), index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100))
    resource_id = Column(Integer)
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    details = Column(Text)
    status = Column(String(50), default="success")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action='{self.action}', user_id={self.user_id}, firm_id={self.firm_id})>"

class DocumentClassification(Base):
    __tablename__ = "document_classifications"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    firm_id = Column(Integer, ForeignKey("firms.id"), nullable=False, index=True)
    
    # Classification results from GPT-4o
    document_type = Column(String(100))
    legal_area = Column(String(200))
    parties_involved = Column(Text)
    important_dates = Column(Text)
    urgency_level = Column(String(50))
    summary = Column(Text)
    keywords = Column(Text)
    
    # AI metadata
    model_used = Column(String(50), default="gpt-4o")
    confidence_score = Column(Float)
    processing_time_seconds = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    classified_by = Column(Integer, ForeignKey("users.id"))
    
    def __repr__(self):
        return f"<DocumentClassification(id={self.id}, document_id={self.document_id}, document_type='{self.document_type}')>"

class ChatConversation(Base):
    __tablename__ = "chat_conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    firm_id = Column(Integer, ForeignKey("firms.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    title = Column(String(500), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")
    user = relationship("User")
    
    def __repr__(self):
        return f"<ChatConversation(id={self.id}, firm_id={self.firm_id}, title='{self.title}')>"

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("chat_conversations.id"), nullable=False, index=True)
    firm_id = Column(Integer, ForeignKey("firms.id"), nullable=False, index=True)
    
    role = Column(String(50), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    sources = Column(Text)  # JSON array of document references
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    conversation = relationship("ChatConversation", back_populates="messages")
    
    def __repr__(self):
        return f"<ChatMessage(id={self.id}, conversation_id={self.conversation_id}, role='{self.role}')>"

class DocumentEmbedding(Base):
    __tablename__ = "document_embeddings"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    firm_id = Column(Integer, ForeignKey("firms.id"), nullable=False, index=True)
    
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    embedding = Column(Vector(1536))  # text-embedding-3-large with dimensions=1536 (optimized for pgvector)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    document = relationship("Document")
    
    __table_args__ = (
        Index('ix_document_embeddings_firm_id_document_id', 'firm_id', 'document_id'),
    )
    
    def __repr__(self):
        return f"<DocumentEmbedding(id={self.id}, document_id={self.document_id}, chunk_index={self.chunk_index})>"

class DocumentTemplate(Base):
    __tablename__ = "document_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    firm_id = Column(Integer, ForeignKey("firms.id"), nullable=False, index=True)
    
    template_type = Column(Enum(LegalDocumentType), nullable=False, index=True)
    name = Column(String(500), nullable=False)
    description = Column(Text)
    template_content = Column(Text, nullable=False)  # Arabic template with {{placeholders}}
    placeholders = Column(Text)  # JSON array of placeholder names and descriptions
    
    is_default = Column(Boolean, default=False)  # System-provided templates
    is_active = Column(Boolean, default=True)
    
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    creator = relationship("User")
    generated_documents = relationship("GeneratedDocument", back_populates="template")
    
    __table_args__ = (
        Index('ix_document_templates_firm_id_type', 'firm_id', 'template_type'),
    )
    
    def __repr__(self):
        return f"<DocumentTemplate(id={self.id}, firm_id={self.firm_id}, type='{self.template_type}', name='{self.name}')>"

class GeneratedDocument(Base):
    __tablename__ = "generated_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    firm_id = Column(Integer, ForeignKey("firms.id"), nullable=False, index=True)
    template_id = Column(Integer, ForeignKey("document_templates.id"), nullable=True, index=True)
    expediente_id = Column(Integer, ForeignKey("expedientes.id"), nullable=True, index=True)
    
    document_type = Column(Enum(LegalDocumentType), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)  # Generated Arabic document
    
    status = Column(Enum(DraftStatus), default=DraftStatus.DRAFT, nullable=False, index=True)
    
    # User input and AI metadata
    user_input = Column(Text)  # Original user prompt/parameters
    generation_metadata = Column(Text)  # JSON with placeholders filled, generation params
    model_used = Column(String(50), default="gpt-4o")
    generation_time_seconds = Column(Float)
    
    # Workflow tracking
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    review_notes = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    template = relationship("DocumentTemplate", back_populates="generated_documents")
    creator = relationship("User", foreign_keys=[created_by])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    approver = relationship("User", foreign_keys=[approved_by])
    expediente = relationship("Expediente")
    
    __table_args__ = (
        Index('ix_generated_documents_firm_id_status', 'firm_id', 'status'),
        Index('ix_generated_documents_firm_id_created_by', 'firm_id', 'created_by'),
    )
    
    def __repr__(self):
        return f"<GeneratedDocument(id={self.id}, firm_id={self.firm_id}, type='{self.document_type}', status='{self.status}')>"
