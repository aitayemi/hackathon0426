"""Data models for the Supply Chain Disruption Response Agent."""

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
    MONITORING = "monitoring"
    MITIGATING = "mitigating"
    ESCALATED = "escalated"
    RESOLVED = "resolved"


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
    """Claude's structured analysis output."""
    incidentId: str
    severity: Severity
    summary: str
    impactedAreas: list[str]
    likelyCause: str
    recommendedActions: list[RecommendedAction]
    confidence: float = Field(ge=0, le=1)
    escalate: bool
    escalationReason: Optional[str] = None


class ResponseScore(str, Enum):
    DO_NOTHING = "do_nothing"
    MONITOR = "monitor"
    MITIGATE = "mitigate"
    ESCALATE = "escalate"


class ResponseCard(BaseModel):
    """The final response card shown to operations users."""
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


class Incident(BaseModel):
    """Full incident record stored in the database."""
    incidentId: str
    input: IncidentInput
    analysis: Optional[AnalysisResult] = None
    responseCard: Optional[ResponseCard] = None
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)
