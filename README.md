# Supply Chain Disruption Response Agent

A "control tower copilot" that transforms noisy supply chain disruption alerts into ranked response playbooks. Built on Amazon EKS with Amazon Bedrock (Claude) for inference.

## Architecture

```
Supplier/Logistics Alerts ──► Ingestion API (EKS) ──► Event Normalizer
   (CSV, API, webhook)              │                       │
                                    │                       ▼
                              Incident Store ◄── Risk Enrichment Service
                              (DynamoDB)         (SKU, lane, supplier)
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
4. Generates a response card with top 3 recommended actions + response score
5. Escalates high-severity incidents via SNS/Slack/Email

## Quick Start (Local)

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Deploy to EKS

```bash
# Build and push images to ECR
docker build -t <ecr-url>/sc-agent-backend:latest ./backend
docker push <ecr-url>/sc-agent-backend:latest

docker build -t <ecr-url>/sc-agent-frontend:latest ./frontend
docker push <ecr-url>/sc-agent-frontend:latest

# Deploy
kubectl apply -f k8s/
```

Both services use internet-facing NLBs — they'll get public IPs automatically.

Ensure your public subnets are tagged: `kubernetes.io/role/elb = 1`

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/incidents/analyze` | Submit + analyze with Claude |
| POST | `/incidents` | Submit without analysis |
| GET | `/incidents` | List all incidents |
| GET | `/incidents/{id}` | Get incident + response card |
| GET | `/health` | Health check |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_REGION` | AWS region | `us-east-1` |
| `BEDROCK_MODEL_ID` | Claude model ID | `anthropic.claude-3-sonnet-20240229-v1:0` |
| `DYNAMODB_TABLE` | DynamoDB table name | `supply-chain-incidents` |
| `USE_DYNAMODB` | Use DynamoDB (false = in-memory) | `false` |
| `SNS_TOPIC_ARN` | SNS topic for escalations | — |
| `SLACK_WEBHOOK_URL` | Slack webhook for alerts | — |
| `ESCALATION_THRESHOLD` | Min severity to escalate | `high` |

## Demo Scenario

Port of Long Beach congestion causing 3-day delay on Shanghai → Phoenix lane, impacting critical SKUs for a priority customer. The agent receives the alert, enriches it, Claude scores severity as "high" with 0.87 confidence, generates a response card recommending reroute/expedite/notify, and triggers escalation.

**Value prop**: Reduce time-to-triage from hours to minutes.
