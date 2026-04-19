# Architecture — Supply Chain Disruption Response Agent

## Design Decisions

### Separation of concerns
- **Claude (Bedrock)**: inference only — severity classification, impact analysis, mitigation drafting
- **FastAPI (EKS)**: business logic — enrichment, prediction, guardrails, response scoring, approval, escalation
- **Why**: Business rules stay outside the model so the app is deterministic and auditable

### Predictive risk scoring (new)
A rules-based risk model runs BEFORE Claude, scoring disruption probability from 0-1 based on:
- Source type weight (weather > supplier > logistics > news)
- Supplier criticality (high/medium/low)
- Lane volume exposure (above/below threshold)
- High-revenue SKU presence
- Priority customer exposure

The risk score is passed to Claude as additional context AND displayed independently on the response card. This means you can get a fast risk assessment without any LLM cost via `POST /predict`.

In production, swap the rules engine for a trained model (XGBoost, etc.) — the API contract stays identical.

### Guardrails (new)
Input and output validation wraps every Bedrock call:

**Input guardrails** (before Claude):
- Event text length bounds (10-2000 chars)
- Product/customer list size limits
- Region validation (warn on unknown)
- Timestamp sanity check

**Output guardrails** (after Claude):
- Confidence range [0,1]
- Exactly 3 recommended actions (per SOP)
- Sequential priority numbering
- Escalation consistency (severity vs escalate flag)
- Summary length check

Violations block the request. Warnings are attached to the response card for transparency.
In production, swap for Bedrock Guardrails API.

### Approval workflow (new)
High-severity incidents (high/critical with escalate=true) enter `pending_approval` status instead of auto-escalating. A human reviewer must:
- `POST /incidents/{id}/approve` with `{"action": "approve", "reviewer": "name"}`
- Or reject with `{"action": "reject", "reviewer": "name", "comment": "reason"}`

Only after approval does the escalation (SNS/Slack) fire. This prevents the system from autonomously triggering business-critical notifications without human oversight.

### Response scoring is deterministic
The `do_nothing / monitor / mitigate / escalate` score is computed in Python, not by Claude:
- Same severity always → same score
- Ops team can tune thresholds without touching prompts
- Judges can trace exactly why an escalation fired

### Why single-agent, not multi-agent?
The multi-agent SOP proposes separate prediction and decision agents orchestrated by Bedrock Agents. We chose single-agent because:
- Multi-agent adds setup complexity without proportional demo value in a hackathon
- The prediction model and decision logic can coexist in one FastAPI service
- The API contract is designed so prediction can be split out later (same `/predict` endpoint)
- Production roadmap: split prediction into a separate EKS service, add Bedrock Agents orchestration

### Internet-facing services
Both backend and frontend K8s Services use:
```yaml
annotations:
  service.beta.kubernetes.io/aws-load-balancer-type: external
  service.beta.kubernetes.io/aws-load-balancer-scheme: internet-facing
  service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
```

### Security
- IRSA (IAM Roles for Service Accounts) — no hardcoded credentials
- Bedrock access scoped to `bedrock:InvokeModel` on Claude models only
- DynamoDB scoped to single table
- SNS scoped to escalation topic
- Input guardrails prevent prompt injection via oversized inputs
- Output guardrails catch hallucinated or out-of-spec model responses
- Approval gate prevents autonomous escalation for high-severity incidents

## Data Flow

1. Disruption event → POST /incidents/analyze
2. **Input guardrails** validate the request
3. Enrichment service adds supplier/lane/SKU context
4. **Predictive risk model** scores disruption probability
5. Risk score + enrichment passed to Claude as context
6. Claude returns structured JSON (severity, impact, 3 actions, confidence)
7. **Output guardrails** validate Claude's response
8. Python applies response score rules
9. If high-severity + escalate → status = `pending_approval`
10. Incident persisted to DynamoDB
11. Human approves → escalation fires via SNS/Slack
12. Response card rendered in web UI with risk prediction + guardrail warnings
