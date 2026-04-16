"""Escalation service — sends alerts for high-severity incidents."""

import os
import json
import logging
import boto3
import httpx

logger = logging.getLogger(__name__)

SNS_TOPIC_ARN = os.getenv("SNS_TOPIC_ARN")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
ESCALATION_THRESHOLD = os.getenv("ESCALATION_THRESHOLD", "high")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def should_escalate(severity: str, explicit_escalate: bool = False) -> bool:
    """Check if severity meets the escalation threshold."""
    if explicit_escalate:
        return True
    threshold = SEVERITY_RANK.get(ESCALATION_THRESHOLD, 2)
    current = SEVERITY_RANK.get(severity, 0)
    return current >= threshold


async def send_escalation(incident_id: str, severity: str, summary: str, reason: str) -> dict:
    """Send escalation notifications via configured channels."""
    results = {"sns": None, "slack": None}
    message = (
        f"🚨 Supply Chain Escalation — {severity.upper()}\n"
        f"Incident: {incident_id}\n"
        f"Summary: {summary}\n"
        f"Reason: {reason}"
    )

    if SNS_TOPIC_ARN:
        try:
            sns = boto3.client("sns", region_name=AWS_REGION)
            sns.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject=f"[{severity.upper()}] Supply Chain Alert: {incident_id}",
                Message=message,
            )
            results["sns"] = "sent"
        except Exception as e:
            logger.error(f"SNS escalation failed: {e}")
            results["sns"] = f"error: {e}"

    if SLACK_WEBHOOK_URL:
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    SLACK_WEBHOOK_URL,
                    json={"text": message},
                    timeout=10,
                )
            results["slack"] = "sent"
        except Exception as e:
            logger.error(f"Slack escalation failed: {e}")
            results["slack"] = f"error: {e}"

    if not SNS_TOPIC_ARN and not SLACK_WEBHOOK_URL:
        logger.warning(f"No escalation channels configured. Logging only: {message}")
        results["logged"] = True

    return results
