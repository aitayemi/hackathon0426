"""Amazon Bedrock Claude integration — structured output, inference only."""

import json
import os
import boto3
from .models import IncidentInput, AnalysisResult

MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")
REGION = os.getenv("AWS_REGION", "us-east-1")

client = boto3.client("bedrock-runtime", region_name=REGION)

# System prompt from claude-sop.md — explicit, format-locked, no hallucination
SYSTEM_PROMPT = (
    "You are a supply chain disruption response analyst.\n\n"
    "Task:\nAnalyze the incident and return a structured JSON object only.\n\n"
    "Instructions:\n"
    "- Use only the incident data and supplied business context.\n"
    "- Do not invent facts.\n"
    "- Classify severity as one of: low, medium, high, critical.\n"
    "- Identify likely impacted areas.\n"
    "- Recommend exactly 3 mitigation actions.\n"
    "- Give a confidence score from 0 to 1.\n"
    "- Keep each field concise.\n"
    "- Return valid JSON only. No markdown. No extra text."
)

OUTPUT_FORMAT = """{
  "incidentId": "string",
  "severity": "low|medium|high|critical",
  "summary": "string",
  "impactedAreas": ["string"],
  "likelyCause": "string",
  "recommendedActions": [
    {"action": "string", "reason": "string", "priority": 1}
  ],
  "confidence": 0.0,
  "escalate": true,
  "escalationReason": "string"
}"""


async def analyze_incident(
    incident: IncidentInput, business_context: dict | None = None
) -> AnalysisResult:
    """Call Claude via Bedrock. Returns validated structured output."""

    user_msg = (
        f"Incident:\n{json.dumps(incident.model_dump(), default=str)}\n\n"
        f"Business context:\n{json.dumps(business_context or {}, default=str)}\n\n"
        f"Output format:\n{OUTPUT_FORMAT}"
    )

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_msg}],
    })

    resp = client.invoke_model(
        modelId=MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=body,
    )

    result = json.loads(resp["body"].read())
    text = result["content"][0]["text"]

    # Validate structured output before returning
    parsed = json.loads(text)
    return AnalysisResult(**parsed)
