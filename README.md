# Supply Chain Disruption Response Agent

A "control tower copilot" that transforms noisy supply chain disruption alerts into ranked response playbooks. Built on Amazon EKS with Amazon Bedrock (Claude) for inference.

## Architecture

```
Supplier/Logistics Alerts ──► Ingestion API (EKS) ──► Event Normalizer
   (CSV, API, webhook)              │                       │
                                    │                       ▼
                              Incident Store ◄── Risk Enrichment Service
                           (DynamoDB/Postgres)    (SKU, lane, supplier)
                                    │                       │
                                    ▼                       ▼
                              Web UI/Dashboard    Claude on Bedrock
                                    ▲              (inference only)
                                    │                       │
                              Response Card ◄───────────────┘
                              Generator
                                    │
                                    ▼
                            Escalation Service
                            (SNS / Slack / Email)
```

## What It Does

1. Ingests disruption events (supplier delays, port congestion, weather alerts)
2. Normalizes and enriches with business context (lane, SKU, supplier criticality)
3. Claude classifies severity, identifies impact, and drafts mitigation actions
4. Generates a response card with top 3 recommended actions
5. Escalates high-severity incidents via SNS/Slack/Email

## Project Structure

```
├── backend/              # FastAPI service
│   ├── app/
│   │   ├── main.py       # API entry point
│   │   ├── models.py     # Pydantic data models
│   │   ├── bedrock.py    # Bedrock Claude integration
│   │   ├── enrichment.py # Risk enrichment logic
│   │   ├── store.py      # DynamoDB incident store
│   │   └── escalation.py # SNS/Slack notifications
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/             # React dashboard
│   ├── src/
│   ├── package.json
│   └── Dockerfile
├── k8s/                  # EKS deployment manifests
│   ├── namespace.yaml
│   ├── backend.yaml
│   ├── frontend.yaml
│   └── ingress.yaml
├── terraform/            # Infrastructure as code
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
├── mock-data/            # Sample disruption events
│   └── incidents.json
└── docs/
    └── ARCHITECTURE.md
```

## Quick Start (Local Dev)

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

## Deploy to EKS

```bash
# Build and push images
docker build -t supply-chain-agent-backend ./backend
docker build -t supply-chain-agent-frontend ./frontend

# Apply K8s manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/incidents` | Submit a new disruption event |
| POST | `/incidents/analyze` | Submit and analyze with Claude |
| GET | `/incidents` | List all incidents |
| GET | `/incidents/{id}` | Get incident details + response card |
| GET | `/health` | Health check |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_REGION` | AWS region | `us-east-1` |
| `BEDROCK_MODEL_ID` | Claude model ID | `anthropic.claude-3-sonnet-20240229-v1:0` |
| `DYNAMODB_TABLE` | DynamoDB table name | `supply-chain-incidents` |
| `SNS_TOPIC_ARN` | SNS topic for escalations | — |
| `SLACK_WEBHOOK_URL` | Slack webhook for alerts | — |
| `ESCALATION_THRESHOLD` | Severity threshold | `high` |

## Demo Scenario

Port of Long Beach congestion causing 3-day delay on Shanghai → Phoenix lane, impacting critical SKUs for a priority customer. The agent:
1. Receives the alert
2. Enriches with supplier/SKU context
3. Claude scores severity as "high" with 0.87 confidence
4. Generates response card: reroute, expedite, notify customer ops
5. Triggers escalation to supply chain leadership

**Value prop**: Reduce time-to-triage from hours to minutes.
