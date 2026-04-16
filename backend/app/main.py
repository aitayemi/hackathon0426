"""Supply Chain Disruption Response Agent — API Service."""

import uuid
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models import (
    IncidentInput, Incident, ResponseCard, ResponseScore, Status,
)
from .bedrock import analyze_incident
from .enrichment import enrich_incident
from .store import save_incident, get_incident, list_incidents
from .escalation import should_escalate, send_escalation

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Supply Chain Disruption Response Agent",
    description="Control tower copilot — turns disruption alerts into ranked response playbooks",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _determine_response_score(severity: str, confidence: float, escalate: bool) -> ResponseScore:
    """Deterministic business rule for response scoring."""
    if escalate or severity == "critical":
        return ResponseScore.ESCALATE
    if severity == "high":
        return ResponseScore.MITIGATE
    if severity == "medium":
        return ResponseScore.MONITOR
    return ResponseScore.DO_NOTHING


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "supply-chain-agent"}


@app.post("/incidents", response_model=dict)
async def create_incident(incident_input: IncidentInput):
    """Submit a disruption event without analysis."""
    incident_id = incident_input.incidentId or f"SC-{uuid.uuid4().hex[:6].upper()}"
    incident_input.incidentId = incident_id

    incident = Incident(
        incidentId=incident_id,
        input=incident_input,
    )
    save_incident(incident)
    return {"incidentId": incident_id, "status": "created"}


@app.post("/incidents/analyze", response_model=ResponseCard)
async def analyze_and_respond(incident_input: IncidentInput):
    """Submit a disruption event, analyze with Claude, and generate response card."""
    incident_id = incident_input.incidentId or f"SC-{uuid.uuid4().hex[:6].upper()}"
    incident_input.incidentId = incident_id

    # Step 1: Enrich with business context
    business_context = enrich_incident(incident_input.model_dump())
    logger.info(f"Enriched incident {incident_id} with context keys: {list(business_context.keys())}")

    # Step 2: Analyze with Claude via Bedrock
    try:
        analysis = await analyze_incident(incident_input, business_context)
    except Exception as e:
        logger.error(f"Bedrock analysis failed for {incident_id}: {e}")
        raise HTTPException(status_code=502, detail=f"Analysis failed: {e}")

    # Step 3: Build response card (business rules stay outside the model)
    response_score = _determine_response_score(
        analysis.severity.value, analysis.confidence, analysis.escalate
    )

    status = Status.ESCALATED if analysis.escalate else Status.OPEN
    card = ResponseCard(
        incidentId=incident_id,
        timestamp=incident_input.timestamp,
        sourceType=incident_input.sourceType,
        sourceName=incident_input.sourceName,
        region=incident_input.region,
        severity=analysis.severity,
        status=status,
        summary=analysis.summary,
        impactedAreas=analysis.impactedAreas,
        likelyCause=analysis.likelyCause,
        recommendedActions=analysis.recommendedActions,
        confidence=analysis.confidence,
        responseScore=response_score,
        escalate=analysis.escalate,
        escalationReason=analysis.escalationReason,
        enrichment=business_context,
    )

    # Step 4: Persist
    incident = Incident(
        incidentId=incident_id,
        input=incident_input,
        analysis=analysis,
        responseCard=card,
    )
    save_incident(incident)

    # Step 5: Escalate if needed
    if should_escalate(analysis.severity.value, analysis.escalate):
        await send_escalation(
            incident_id, analysis.severity.value,
            analysis.summary, analysis.escalationReason or "Severity threshold exceeded",
        )
        logger.info(f"Escalation triggered for {incident_id}")

    return card


@app.get("/incidents")
async def get_all_incidents():
    """List all incidents."""
    return list_incidents()


@app.get("/incidents/{incident_id}")
async def get_one_incident(incident_id: str):
    """Get a single incident with its response card."""
    incident = get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident
