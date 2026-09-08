import uuid
from datetime import datetime, timezone
from typing import Optional, List, Any
from sqlalchemy import String, Integer, Float, Boolean, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processing_status: Mapped[str] = mapped_column(String(32), default="uploaded", nullable=False)
    extraction_status: Mapped[str] = mapped_column(String(32), default="not_started", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    evidence_units: Mapped[List["EvidenceUnit"]] = relationship("EvidenceUnit", back_populates="document", cascade="all, delete-orphan")
    facts: Mapped[List["Fact"]] = relationship("Fact", back_populates="document", cascade="all, delete-orphan")


class EvidenceUnit(Base):
    __tablename__ = "evidence_units"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    clean_text: Mapped[str] = mapped_column(Text, nullable=False)
    location_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="evidence_units")
    facts: Mapped[List["Fact"]] = relationship("Fact", back_populates="evidence_unit", cascade="all, delete-orphan")


class Fact(Base):
    __tablename__ = "facts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_id: Mapped[str] = mapped_column(String(36), ForeignKey("evidence_units.id", ondelete="CASCADE"), nullable=False, index=True)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    
    # Core subject-predicate-value triple representation
    subject: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    predicate: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    value_type: Mapped[str] = mapped_column(String(64), nullable=False, default="text")
    unit: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    
    # Context & Provenance
    temporal_context: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    geographic_scope: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    operating_scope: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    qualifiers: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    verbatim_quote: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Metadata & Quality Assurance
    is_inferred: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    extraction_confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    extraction_status: Mapped[str] = mapped_column(String(32), default="grounded", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="facts")
    evidence_unit: Mapped["EvidenceUnit"] = relationship("EvidenceUnit", back_populates="facts")
    embedding: Mapped[Optional["FactEmbedding"]] = relationship("FactEmbedding", back_populates="fact", cascade="all, delete-orphan", uselist=False)


class FactEmbedding(Base):
    __tablename__ = "fact_embeddings"

    fact_id: Mapped[str] = mapped_column(String(36), ForeignKey("facts.id", ondelete="CASCADE"), primary_key=True)
    vector: Mapped[List[float]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    fact: Mapped["Fact"] = relationship("Fact", back_populates="embedding")


class FactRelationship(Base):
    __tablename__ = "fact_relationships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_fact_id: Mapped[str] = mapped_column(String(36), ForeignKey("facts.id", ondelete="CASCADE"), nullable=False, index=True)
    target_fact_id: Mapped[str] = mapped_column(String(36), ForeignKey("facts.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Category: CORROBORATED | CONTRADICTED | CONTEXTUALLY_RECONCILED | REASONING_FAILURE
    relationship_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    reasoning_summary: Mapped[str] = mapped_column(Text, nullable=False)
    reconciliation_context: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    source_fact: Mapped["Fact"] = relationship("Fact", foreign_keys=[source_fact_id])
    target_fact: Mapped["Fact"] = relationship("Fact", foreign_keys=[target_fact_id])
