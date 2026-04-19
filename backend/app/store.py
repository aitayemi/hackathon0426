"""Incident store — DynamoDB with in-memory fallback for local dev."""

import os
import json
import boto3
from typing import Optional
from .models import Incident

USE_DYNAMO = os.getenv("USE_DYNAMODB", "false").lower() == "true"
TABLE_NAME = os.getenv("DYNAMODB_TABLE", "supply-chain-incidents")
REGION = os.getenv("AWS_REGION", "us-east-1")

_mem: dict[str, dict] = {}


def _table():
    return boto3.resource("dynamodb", region_name=REGION).Table(TABLE_NAME)


def save_incident(incident: Incident) -> None:
    data = json.loads(incident.model_dump_json())
    if USE_DYNAMO:
        _table().put_item(Item=data)
    else:
        _mem[incident.incidentId] = data


def get_incident(incident_id: str) -> Optional[dict]:
    if USE_DYNAMO:
        return _table().get_item(Key={"incidentId": incident_id}).get("Item")
    return _mem.get(incident_id)


def list_incidents() -> list[dict]:
    items = _table().scan().get("Items", []) if USE_DYNAMO else list(_mem.values())
    return sorted(items, key=lambda x: x.get("createdAt", ""), reverse=True)


def update_incident(incident_id: str, data: dict) -> None:
    """Update an existing incident record."""
    if USE_DYNAMO:
        _table().put_item(Item=data)
    else:
        _mem[incident_id] = data
