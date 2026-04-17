"""Amazon Bedrock Claude integration for incident analysis."""

import json
import os
import boto3
from .models import IncidentInput, AnalysisResult

BEDROCK_MODEL_ID = os.getenv(
    "BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0"
)
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

bedrock_client = boto3.client("bedrock-runtime", region_name=AWS_REGION)

SYSTEM_PROMPT = """You are a supply chain disruption response analyst.

Task: Analyze the incident and return a structured JSON object only.

Instructions:
- Use only the incident data and supplied business context.
- Do not invent facts.
- Classify severity as one of: low, medium, high, critical.
- Identify likely impacted areas.
- Recommend exactly 3 mitigation actions.
- Give a confidence score from 0 to 1.
- Keep each field concise.
- Return valid JSON only. No markdown. No extra text."""

OUTPUT_SCHEMA = """{
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
###    incident: IncidentInput, business_context: dict | None = None
    incident: IncidentInput, business_context: Union[dict, None] = None
) -> AnalysisResult:
    """Call Claude via Bedrock to analyze a supply chain disruption."""

    user_message = f"""Incident:
{json.dumps(incident.model_dump(), default=str)}

Business context:
{json.dumps(business_context or {}, default=str)}

Output format:
{OUTPUT_SCHEMA}"""

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_message}],
    })

    response = bedrock_client.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=body,
    )

    result = json.loads(response["body"].read())
    text = result["content"][0]["text"]

    # Parse and validate the structured output
    parsed = json.loads(text)
    return AnalysisResult(**parsed)
