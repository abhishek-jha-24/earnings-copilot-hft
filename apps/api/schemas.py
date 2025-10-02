"""
Pydantic models for API request/response schemas.
"""

from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field


# Subscription schemas
class SubscriptionCreate(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol")
    channels: List[Literal["ws", "slack", "email"]] = Field(..., description="Notification channels")


class SubscriptionResponse(BaseModel):
    id: int
    user_id: str
    ticker: str
    channels: List[str]
    created_at: str


# Document schemas
class DocEvent(BaseModel):
    event: Literal["NEW_DOC_INGESTED"]
    doc_id: str
    ticker: str
    period: Optional[str]
    doc_type: str
    received_at: str


# KPI schemas
class Provenance(BaseModel):
    doc: str
    page: int
    table: str
    row: int
    col: int


class KpiRow(BaseModel):
    ticker: str
    period: str
    metric: str
    value: float
    unit: str
    yoy_change: Optional[float] = None
    qoq_change: Optional[float] = None
    consensus: Optional[float] = None
    surprise: Optional[float] = None
    provenance: Provenance
    confidence: float
    needs_review: bool
    extracted_at: str


class KpiResponse(BaseModel):
    ticker: str
    period: str
    metric: str
    current_value: float
    unit: str
    yoy_change: Optional[float] = None
    qoq_change: Optional[float] = None
    consensus: Optional[float] = None
    surprise: Optional[float] = None
    provenance: Provenance
    confidence: float


# Delta schemas
class DeltaRow(BaseModel):
    ticker: str
    period: str
    metric: str
    current_value: float
    previous_value: float
    delta_abs: float
    delta_pct: float
    consensus: Optional[float] = None
    surprise: Optional[float] = None
    significance: Literal["material", "minor", "negligible"]
    provenance: Provenance


# Signal schemas
class Citation(BaseModel):
    doc: str
    page: int
    table: str
    text: str


class SignalResponse(BaseModel):
    ticker: str
    period: Optional[str] = None
    action: Literal["BUY", "SELL", "HOLD"]
    confidence: float
    reasons: List[str]
    citations: List[Citation]
    blocked_reason: Optional[str] = None
    generated_at: str


# Compliance schemas
class ComplianceRule(BaseModel):
    rule_id: str
    scope_class: Optional[str] = None
    scope_tickers: List[str]
    initial_margin: float
    maintenance_margin: float
    effective_date: str
    provenance: Provenance
    confidence: float


class ComplianceAlert(BaseModel):
    event: Literal["COMPLIANCE_ALERT"]
    ticker: str
    message: str
    effective_date: str
    citations: List[Citation]
    exposure_guidance: Optional[str] = None


# Search schemas
class SearchResult(BaseModel):
    doc: str
    page: int
    text: str
    score: float
    ticker: Optional[str] = None


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    total_results: int


# Upload schemas
class UploadResponse(BaseModel):
    doc_id: str
    ticker: str
    period: Optional[str]
    doc_type: str
    status: str
    message: str


# SSE Event schemas
class SSEEvent(BaseModel):
    event: str
    data: Dict[str, Any]


class NewSignalReady(BaseModel):
    event: Literal["NEW_SIGNAL_READY"]
    ticker: str
    action: str
    confidence: float
    citations: List[Citation]


# Export schemas
class MemoRequest(BaseModel):
    ticker: str
    period: str
    include_citations: bool = True
    include_compliance: bool = True


# Error schemas
class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
