"""Supply Chain Disruption Response Agent — FastAPI service on EKS."""

import uuid
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models import IncidentInput, Incident, ResponseCard, ResponseScore, Status
from .bedrock import analyze_incident
from .enrichment import enrich_incident
from .store import save_incident, get_incident, list_incidents
from .escalation import should_escalate, send_escalation

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = FastAPI(
    title="Supply Chain Disruption Response Agent",
    description="Control tower copilot — disruption alerts to ranked response playbooks",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


def _score(severity: str, confidence: float, escalate: bool) -> ResponseScore:
    """Deterministic business rule — kept outside the model."""
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


@app.post("/incidents")
async def create_incident(inp: IncidentInput):
    iid = inp.incidentId or f"SC-{uuid.uuid4().hex[:6].upper()}"
    inp.incidentId = iid
    save_incident(Incident(incidentId=iid, input=inp))
    return {"incidentId": iid, "status": "created"}


@app.post("/incidents/analyze", response_model=ResponseCard)
async def analyze_and_respond(inp: IncidentInput):
    """Full pipeline: enrich → Claude → response card → escalate."""
    iid = inp.incidentId or f"SC-{uuid.uuid4().hex[:6].upper()}"
    inp.incidentId = iid

    # 1. Enrich with business context
    ctx = enrich_incident(inp.model_dump())
    log.info(f"Enriched {iid}: {list(ctx.keys())}")

    # 2. Claude analysis via Bedrock
    try:
        analysis = await analyze_incident(inp, ctx)
    except Exception as e:
        log.error(f"Bedrock failed for {iid}: {e}")
        raise HTTPException(502, f"Analysis failed: {e}")

    # 3. Build response card (business rules outside model)
    card = ResponseCard(
        incidentId=iid,
        timestamp=inp.timestamp,
        sourceType=inp.sourceType,
        sourceName=inp.sourceName,
        region=inp.region,
        severity=analysis.severity,
        status=Status.ESCALATED if analysis.escalate else Status.OPEN,
        summary=analysis.summary,
        impactedAreas=analysis.impactedAreas,
        likelyCause=analysis.likelyCause,
        recommendedActions=analysis.recommendedActions,
        confidence=analysis.confidence,
        responseScore=_score(analysis.severity.value, analysis.confidence, analysis.escalate),
        escalate=analysis.escalate,
        escalationReason=analysis.escalationReason,
        enrichment=ctx,
    )

    # 4. Persist
    save_incident(Incident(incidentId=iid, input=inp, analysis=analysis, responseCard=card))

    # 5. Escalate if needed
    if should_escalate(analysis.severity.value, analysis.escalate):
        await send_escalation(iid, analysis.severity.value, analysis.summary,
                              analysis.escalationReason or "Severity threshold exceeded")
        log.info(f"Escalation triggered for {iid}")

    return card


@app.get("/incidents")
async def get_all():
    return list_incidents()


@app.get("/incidents/{incident_id}")
async def get_one(incident_id: str):
    inc = get_incident(incident_id)
    if not inc:
        raise HTTPException(404, "Incident not found")
    return inc
