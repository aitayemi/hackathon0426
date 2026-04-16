# Architecture — Supply Chain Disruption Response Agent

## Design Reasoning

### Why this architecture?

The system is intentionally split into modular services that each do one thing well. This keeps Claude focused on inference (what it's good at) while EKS handles business logic and workflow orchestration (what deterministic code is good at).

**Key principle**: Business rules for escalation and response scoring stay *outside* the model so the app remains deterministic and auditable.

### Component Breakdown

```
┌─────────────────────────────────────────────────────────────────┐
│                        Amazon EKS Cluster                       │
│                                                                 │
│  ┌──────────────┐    ┌──────────────────┐    ┌──────────────┐  │
│  │  Frontend     │    │  Backend API     │    │  Escalation  │  │
│  │  (React/Nginx)│◄──►│  (FastAPI)       │───►│  Service     │  │
│  │  Port 80      │    │  Port 8000       │    │  (SNS/Slack) │  │
│  └──────────────┘    └────────┬─────────┘    └──────────────┘  │
│                               │                                 │
│                    ┌──────────┼──────────┐                      │
│                    ▼          ▼          ▼                      │
│             ┌──────────┐ ┌────────┐ ┌────────────┐             │
│             │Enrichment│ │ Store  │ │ Bedrock    │             │
│             │Service   │ │DynamoDB│ │ Claude     │             │
│             └──────────┘ └────────┘ └────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Ingestion**: Disruption event arrives via REST API (POST /incidents/analyze)
2. **Enrichment**: System adds business context — supplier profile, lane metadata, SKU criticality, customer priority
3. **Analysis**: Claude receives the enriched incident and returns structured JSON with severity, impact, actions, confidence
4. **Scoring**: Deterministic business rules map severity + confidence → response score (do nothing / monitor / mitigate / escalate)
5. **Persistence**: Full incident record saved to DynamoDB with audit trail
6. **Escalation**: If severity ≥ threshold, notifications fire via SNS/Slack
7. **Display**: Response card rendered in the web UI

### Why Claude via Bedrock (not fine-tuned model)?

- **Structured output**: Claude follows JSON schemas reliably, which is critical for automation
- **Zero training data needed**: Works out of the box with good prompting
- **Swap-friendly**: If a better model ships tomorrow, swap the model ID in one env var
- **Cost-effective for hackathon**: Pay-per-invocation, no GPU provisioning

### Why business rules outside the model?

The response scoring logic (`do_nothing` / `monitor` / `mitigate` / `escalate`) is handled in Python, not by Claude. This is intentional:

- **Deterministic**: Same severity always produces the same score
- **Auditable**: You can trace exactly why an escalation fired
- **Tunable**: Ops team can change thresholds without touching prompts
- **Trustworthy**: Judges can see the system doesn't hallucinate escalation decisions

### Why two-phase prompt design?

The SOP suggests splitting complex workflows into separate prompts. For the MVP we use a single prompt because:
- The incident analysis task is well-bounded
- One structured output covers classification + mitigation
- Splitting adds latency without proportional accuracy gain at this scope

For production, you'd split into: (1) severity classification, (2) mitigation drafting — each with its own validation layer.

### EKS Service Layout

| Service | Role | Why separate? |
|---------|------|---------------|
| `backend` (FastAPI) | API + orchestration | Central coordination, easy to scale |
| `frontend` (React/Nginx) | UI rendering | Static assets, CDN-friendly |
| `enrichment` (in-process) | Business context injection | Hackathon: runs in backend. Production: separate service |
| `escalation` (in-process) | Alert dispatch | Hackathon: runs in backend. Production: async worker |

### Security Model

- EKS pods use IRSA (IAM Roles for Service Accounts) — no hardcoded credentials
- Bedrock access is scoped to `bedrock:InvokeModel` on Claude models only
- DynamoDB access is scoped to the single incidents table
- SNS publish is scoped to the escalation topic
- Frontend has no direct AWS access — everything goes through the backend API

### What's not in the MVP (production roadmap)

- Real supplier/logistics data feeds (webhooks, S3 event triggers)
- Historical incident similarity search (vector store)
- Multi-tenant isolation
- Prompt chaining for complex multi-step analysis
- Cost optimization (response caching, batched inference)
- Observability (X-Ray tracing, CloudWatch dashboards)
