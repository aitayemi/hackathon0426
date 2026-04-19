"""Supply Chain Disruption Response Agent — FastAPI service on EKS."""

import uuid
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models import IncidentInput, Incident, ResponseCard, ResponseScore, Status, ApprovalAction
from .bedrock import analyze_incident
from .enrichment import enrich_incident
from .predict import predict_risk
from .guardrails import validate_input, validate_output, GuardrailViolation
from .store import save_incident, get_incident, list_incidents, update_incident
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
    """Full pipeline: guardrails → enrich → predict → Claude → guardrails → response card → escalate."""
    iid = inp.incidentId or f"SC-{uuid.uuid4().hex[:6].upper()}"
    inp.incidentId = iid

    # 0. Input guardrails
    try:
        input_warnings = validate_input(inp)
    except GuardrailViolation as e:
        raise HTTPException(422, f"Input rejected: {e}")

    # 1. Enrich with business context
    ctx = enrich_incident(inp.model_dump())
    log.info(f"Enriched {iid}: {list(ctx.keys())}")

    # 2. Predictive risk score
    risk = predict_risk(inp.model_dump())
    ctx["riskPrediction"] = risk
    log.info(f"Risk prediction for {iid}: {risk['riskTier']} ({risk['riskProbability']})")

    # 3. Claude analysis via Bedrock
    try:
        analysis = await analyze_incident(inp, ctx)
    except Exception as e:
        log.error(f"Bedrock failed for {iid}: {e}")
        raise HTTPException(502, f"Analysis failed: {e}")

    # 4. Output guardrails
    output_warnings = validate_output(analysis)
    all_warnings = input_warnings + output_warnings
    if all_warnings:
        log.warning(f"Guardrail warnings for {iid}: {all_warnings}")

    # 5. Build response card (business rules outside model)
    # High-severity incidents require approval before escalation
    needs_approval = analysis.severity.value in ("high", "critical") and analysis.escalate
    status = Status.PENDING_APPROVAL if needs_approval else (
        Status.ESCALATED if analysis.escalate else Status.OPEN
    )

    card = ResponseCard(
        incidentId=iid,
        timestamp=inp.timestamp,
        sourceType=inp.sourceType,
        sourceName=inp.sourceName,
        region=inp.region,
        severity=analysis.severity,
        status=status,
        summary=analysis.summary,
        impactedAreas=analysis.impactedAreas,
        likelyCause=analysis.likelyCause,
        recommendedActions=analysis.recommendedActions,
        confidence=analysis.confidence,
        responseScore=_score(analysis.severity.value, analysis.confidence, analysis.escalate),
        escalate=analysis.escalate,
        escalationReason=analysis.escalationReason,
        enrichment=ctx,
        riskPrediction=risk,
        guardrailWarnings=all_warnings,
    )

    # 6. Persist
    save_incident(Incident(incidentId=iid, input=inp, analysis=analysis, responseCard=card))

    # 7. Auto-escalate only if NOT pending approval
    if not needs_approval and should_escalate(analysis.severity.value, analysis.escalate):
        await send_escalation(iid, analysis.severity.value, analysis.summary,
                              analysis.escalationReason or "Severity threshold exceeded")
        log.info(f"Escalation triggered for {iid}")

    return card


@app.post("/predict")
async def predict_only(inp: IncidentInput):
    """Risk prediction without Claude analysis — fast, no LLM cost."""
    return predict_risk(inp.model_dump())


@app.post("/incidents/{incident_id}/approve")
async def approve_incident(incident_id: str, action: ApprovalAction):
    """Approve or reject a pending response card. Triggers escalation on approve."""
    inc = get_incident(incident_id)
    if not inc:
        raise HTTPException(404, "Incident not found")

    card = inc.get("responseCard")
    if not card:
        raise HTTPException(400, "No response card to approve")
    if card.get("status") != "pending_approval":
        raise HTTPException(400, f"Incident is '{card.get('status')}', not pending_approval")

    if action.action == "approve":
        card["status"] = "escalated"
        inc["approval"] = action.model_dump()
        inc["responseCard"] = card
        update_incident(incident_id, inc)

        # Now trigger the escalation
        await send_escalation(
            incident_id, card.get("severity", "high"),
            card.get("summary", ""), card.get("escalationReason", "Approved by reviewer"),
        )
        log.info(f"Approved and escalated {incident_id} by {action.reviewer}")
        return {"incidentId": incident_id, "status": "escalated", "reviewer": action.reviewer}

    elif action.action == "reject":
        card["status"] = "rejected"
        inc["approval"] = action.model_dump()
        inc["responseCard"] = card
        update_incident(incident_id, inc)
        log.info(f"Rejected {incident_id} by {action.reviewer}: {action.comment}")
        return {"incidentId": incident_id, "status": "rejected", "reviewer": action.reviewer}

    else:
        raise HTTPException(400, "Action must be 'approve' or 'reject'")


@app.get("/incidents")
async def get_all():
    return list_incidents()


@app.get("/incidents/{incident_id}")
async def get_one(incident_id: str):
    inc = get_incident(incident_id)
    if not inc:
        raise HTTPException(404, "Incident not found")
    return inc
