"""Incident store — DynamoDB backend with in-memory fallback for local dev."""

import os
import json
import boto3
from datetime import datetime
from typing import Optional
from .models import Incident

USE_DYNAMODB = os.getenv("USE_DYNAMODB", "false").lower() == "true"
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "supply-chain-incidents")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# In-memory store for local dev / hackathon demo
_memory_store: dict[str, dict] = {}


def _get_table():
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    return dynamodb.Table(DYNAMODB_TABLE)


def save_incident(incident: Incident) -> None:
    """Persist an incident record."""
    data = json.loads(incident.model_dump_json())

    if USE_DYNAMODB:
        table = _get_table()
        table.put_item(Item=data)
    else:
        _memory_store[incident.incidentId] = data


def get_incident(incident_id: str) -> Optional[dict]:
    """Retrieve an incident by ID."""
    if USE_DYNAMODB:
        table = _get_table()
        resp = table.get_item(Key={"incidentId": incident_id})
        return resp.get("Item")
    return _memory_store.get(incident_id)


def list_incidents() -> list[dict]:
    """List all incidents (most recent first)."""
    if USE_DYNAMODB:
        table = _get_table()
        resp = table.scan()
        items = resp.get("Items", [])
    else:
        items = list(_memory_store.values())

    return sorted(items, key=lambda x: x.get("createdAt", ""), reverse=True)
