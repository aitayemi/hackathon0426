"""Guardrails — input validation + output validation wrapping Bedrock calls.

Prevents malformed inputs from reaching Claude and catches hallucinated or
out-of-spec outputs before they reach the user. In production, swap for
Bedrock Guardrails API. For hackathon, deterministic Python checks."""

import logging
from datetime import datetime, timedelta
from .models import IncidentInput, AnalysisResult, Severity

log = logging.getLogger(__name__)

# --- Input guardrails ---

_VALID_REGIONS = {
    "US-West", "US-East", "US-Southeast", "US-Central",
    "EMEA", "APAC", "LATAM", "Global",
}

_MAX_EVENT_LENGTH = 2000
_MAX_PRODUCTS = 50
_MAX_CUSTOMERS = 20


class GuardrailViolation(Exception):
    """Raised when input or output fails guardrail checks."""
    def __init__(self, field: str, reason: str):
        self.field = field
        self.reason = reason
        super().__init__(f"Guardrail violation [{field}]: {reason}")


def validate_input(inp: IncidentInput) -> list[str]:
    """Validate incident input before sending to Claude. Returns list of warnings."""
    warnings = []

    # Event text length
    if len(inp.event) > _MAX_EVENT_LENGTH:
        raise GuardrailViolation("event", f"Event text exceeds {_MAX_EVENT_LENGTH} chars")
    if len(inp.event.strip()) < 10:
        raise GuardrailViolation("event", "Event description too short to analyze")

    # Region validation (warn, don't block)
    if inp.region not in _VALID_REGIONS:
        warnings.append(f"Unrecognized region '{inp.region}' — analysis may be less accurate")

    # Product/customer list bounds
    if len(inp.affectedProducts) > _MAX_PRODUCTS:
        raise GuardrailViolation("affectedProducts", f"Too many products ({len(inp.affectedProducts)} > {_MAX_PRODUCTS})")
    if len(inp.priorityCustomers) > _MAX_CUSTOMERS:
        raise GuardrailViolation("priorityCustomers", f"Too many customers ({len(inp.priorityCustomers)} > {_MAX_CUSTOMERS})")

    # Timestamp sanity — not too far in the future
    if inp.timestamp > datetime.utcnow() + timedelta(hours=24):
        warnings.append("Timestamp is more than 24h in the future")

    return warnings


# --- Output guardrails ---

def validate_output(result: AnalysisResult) -> list[str]:
    """Validate Claude's output for consistency and safety. Returns warnings."""
    warnings = []

    # Confidence sanity
    if result.confidence < 0 or result.confidence > 1:
        raise GuardrailViolation("confidence", f"Confidence {result.confidence} outside [0,1]")

    # Must have exactly 3 actions (per SOP)
    if len(result.recommendedActions) != 3:
        warnings.append(f"Expected 3 actions, got {len(result.recommendedActions)}")

    # Priorities should be 1, 2, 3
    priorities = sorted(a.priority for a in result.recommendedActions)
    if priorities != list(range(1, len(result.recommendedActions) + 1)):
        warnings.append(f"Action priorities not sequential: {priorities}")

    # Escalation consistency
    if result.escalate and not result.escalationReason:
        warnings.append("Escalation flagged but no reason provided")
    if not result.escalate and result.severity in (Severity.HIGH, Severity.CRITICAL):
        warnings.append(f"Severity is {result.severity.value} but escalate=false — may need review")

    # Summary length check
    if result.summary and len(result.summary) > 500:
        warnings.append("Summary exceeds 500 chars — may be too verbose")

    return warnings
