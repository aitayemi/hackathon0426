# Architecture — Supply Chain Disruption Response Agent

## Design Decisions

### Separation of concerns
- **Claude (Bedrock)**: inference only — severity classification, impact analysis, mitigation drafting
- **FastAPI (EKS)**: business logic — enrichment, response scoring, escalation rules, persistence
- **Why**: Business rules for escalation stay outside the model so the app is deterministic and auditable

### Response scoring is deterministic
The `do_nothing / monitor / mitigate / escalate` score is computed in Python, not by Claude:
- Same severity always → same score
- Ops team can tune thresholds without touching prompts
- Judges can trace exactly why an escalation fired

### Single prompt (not chained)
The SOP suggests splitting into classification + mitigation prompts. For the MVP, one structured prompt covers both because:
- The task is well-bounded
- Splitting adds latency without proportional accuracy gain at hackathon scope
- Production would split them with separate validation layers

### Internet-facing services
Both backend and frontend K8s Services use:
```yaml
annotations:
  service.beta.kubernetes.io/aws-load-balancer-type: external
  service.beta.kubernetes.io/aws-load-balancer-scheme: internet-facing
  service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
```
This provisions internet-facing NLBs with public IPs. Requires:
- AWS Load Balancer Controller installed on the EKS cluster
- Public subnets tagged with `kubernetes.io/role/elb = 1`

### Security
- IRSA (IAM Roles for Service Accounts) — no hardcoded credentials
- Bedrock access scoped to `bedrock:InvokeModel` on Claude models only
- DynamoDB scoped to single table
- SNS scoped to escalation topic
- Frontend has no direct AWS access

## Data Flow

1. Disruption event → POST /incidents/analyze
2. Enrichment service adds supplier/lane/SKU context
3. Claude returns structured JSON (severity, impact, 3 actions, confidence)
4. Python applies response score rules
5. Incident persisted to DynamoDB
6. If severity ≥ threshold → SNS/Slack escalation
7. Response card rendered in web UI
