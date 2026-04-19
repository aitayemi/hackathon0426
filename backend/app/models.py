"""Pydantic data models — matches the incident schema from the architecture doc."""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from datetime import datetime


class SourceType(str, Enum):
    SUPPLIER = "supplier"
    LOGISTICS = "logistics"
    WEATHER = "weather"
    NEWS = "news"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Status(str, Enum):
    OPEN = "open"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    MONITORING = "monitoring"
    MITIGATING = "mitigating"
    ESCALATED = "escalated"
    RESOLVED = "resolved"


class ResponseScore(str, Enum):
    DO_NOTHING = "do_nothing"
    MONITOR = "monitor"
    MITIGATE = "mitigate"
    ESCALATE = "escalate"


class IncidentInput(BaseModel):
    """Incoming disruption event from supplier/logistics feed."""
    incidentId: Optional[str] = None
    sourceType: SourceType
    sourceName: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    region: str
    affectedLane: Optional[str] = None
    supplier: Optional[str] = None
    event: str
    affectedProducts: list[str] = []
    priorityCustomers: list[str] = []


class RecommendedAction(BaseModel):
    action: str
    reason: str
    priority: int


class AnalysisResult(BaseModel):
    """Claude's structured JSON output."""
    incidentId: str
    severity: Severity
    summary: str
    impactedAreas: list[str]
    likelyCause: str
    recommendedActions: list[RecommendedAction]
    confidence: float = Field(ge=0, le=1)
    escalate: bool
    escalationReason: Optional[str] = None


class ResponseCard(BaseModel):
    """Decision card shown to operations users."""
    incidentId: str
    timestamp: datetime
    sourceType: SourceType
    sourceName: str
    region: str
    severity: Severity
    status: Status
    summary: str
    impactedAreas: list[str]
    likelyCause: str
    recommendedActions: list[RecommendedAction]
    confidence: float
    responseScore: ResponseScore
    escalate: bool
    escalationReason: Optional[str] = None
    enrichment: Optional[dict] = None
    riskPrediction: Optional[dict] = None
    guardrailWarnings: list[str] = []


class ApprovalAction(BaseModel):
    """Approve or reject a pending response card."""
    action: str  # "approve" or "reject"
    reviewer: str
    comment: Optional[str] = None


class Incident(BaseModel):
    """Full incident record for storage."""
    incidentId: str
    input: IncidentInput
    analysis: Optional[AnalysisResult] = None
    responseCard: Optional[ResponseCard] = None
    approval: Optional[ApprovalAction] = None
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)
