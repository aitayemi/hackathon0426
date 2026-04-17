"""Escalation service — SNS/Slack alerts when severity crosses threshold."""

import os
import logging
import boto3
import httpx

log = logging.getLogger(__name__)

SNS_TOPIC = os.getenv("SNS_TOPIC_ARN")
SLACK_URL = os.getenv("SLACK_WEBHOOK_URL")
THRESHOLD = os.getenv("ESCALATION_THRESHOLD", "high")
REGION = os.getenv("AWS_REGION", "us-east-1")

_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def should_escalate(severity: str, explicit: bool = False) -> bool:
    if explicit:
        return True
    return _RANK.get(severity, 0) >= _RANK.get(THRESHOLD, 2)


async def send_escalation(incident_id: str, severity: str, summary: str, reason: str) -> dict:
    results = {}
    msg = (
        f"🚨 Supply Chain Escalation — {severity.upper()}\n"
        f"Incident: {incident_id}\n"
        f"Summary: {summary}\n"
        f"Reason: {reason}"
    )

    if SNS_TOPIC:
        try:
            boto3.client("sns", region_name=REGION).publish(
                TopicArn=SNS_TOPIC,
                Subject=f"[{severity.upper()}] SC Alert: {incident_id}",
                Message=msg,
            )
            results["sns"] = "sent"
        except Exception as e:
            log.error(f"SNS failed: {e}")
            results["sns"] = f"error: {e}"

    if SLACK_URL:
        try:
            async with httpx.AsyncClient() as c:
                await c.post(SLACK_URL, json={"text": msg}, timeout=10)
            results["slack"] = "sent"
        except Exception as e:
            log.error(f"Slack failed: {e}")
            results["slack"] = f"error: {e}"

    if not SNS_TOPIC and not SLACK_URL:
        log.warning(f"No escalation channels configured. {msg}")
        results["logged"] = True

    return results
