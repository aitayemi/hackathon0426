"""Predictive risk scoring — rules-based model for hackathon, swap for ML later.

Scores disruption risk based on source type, region, supplier criticality,
lane volume, and product revenue exposure. Returns a 0-1 probability and
a risk tier (low/medium/high/critical).

In production, this would be a trained model (XGBoost, etc.) served on EKS.
The API contract stays the same — just swap the scoring function."""

from datetime import datetime
from .enrichment import SUPPLIERS, LANES, SKUS

# Weights for each risk factor (tunable without touching prompts)
_WEIGHTS = {
    "source_type": {"weather": 0.3, "logistics": 0.2, "supplier": 0.25, "news": 0.1},
    "supplier_criticality": {"high": 0.3, "medium": 0.15, "low": 0.05},
    "lane_volume_threshold": 300,  # weekly units — above this = higher risk
    "high_revenue_sku_boost": 0.15,
    "priority_customer_boost": 0.1,
    "multi_product_boost": 0.05,  # per additional product beyond 1
}


def predict_risk(incident_data: dict) -> dict:
    """Score disruption risk. Returns probability, tier, and factor breakdown."""
    score = 0.0
    factors = []

    # 1. Source type risk
    src = incident_data.get("sourceType", "news")
    src_score = _WEIGHTS["source_type"].get(src, 0.1)
    score += src_score
    factors.append({"factor": "sourceType", "value": src, "contribution": src_score})

    # 2. Supplier criticality
    supplier = incident_data.get("supplier")
    if supplier and supplier in SUPPLIERS:
        crit = SUPPLIERS[supplier]["criticality"]
        crit_score = _WEIGHTS["supplier_criticality"].get(crit, 0.05)
        score += crit_score
        factors.append({"factor": "supplierCriticality", "value": crit, "contribution": crit_score})

    # 3. Lane volume exposure
    lane = incident_data.get("affectedLane")
    if lane and lane in LANES:
        vol = LANES[lane]["volumePerWeek"]
        if vol >= _WEIGHTS["lane_volume_threshold"]:
            lane_score = 0.2
        else:
            lane_score = 0.08
        score += lane_score
        factors.append({"factor": "laneVolume", "value": vol, "contribution": lane_score})

    # 4. Product revenue exposure
    products = incident_data.get("affectedProducts", [])
    high_rev = any(
        SKUS.get(p, {}).get("revenue") == "high" for p in products
    )
    if high_rev:
        score += _WEIGHTS["high_revenue_sku_boost"]
        factors.append({"factor": "highRevenueSKU", "value": True, "contribution": _WEIGHTS["high_revenue_sku_boost"]})

    # Multi-product penalty
    if len(products) > 1:
        multi = _WEIGHTS["multi_product_boost"] * (len(products) - 1)
        score += multi
        factors.append({"factor": "multipleProducts", "value": len(products), "contribution": multi})

    # 5. Priority customer exposure
    customers = incident_data.get("priorityCustomers", [])
    if customers:
        score += _WEIGHTS["priority_customer_boost"]
        factors.append({"factor": "priorityCustomers", "value": len(customers), "contribution": _WEIGHTS["priority_customer_boost"]})

    # Clamp to [0, 1]
    probability = min(max(score, 0.0), 1.0)

    # Map to tier
    if probability >= 0.75:
        tier = "critical"
    elif probability >= 0.5:
        tier = "high"
    elif probability >= 0.25:
        tier = "medium"
    else:
        tier = "low"

    return {
        "riskProbability": round(probability, 3),
        "riskTier": tier,
        "factors": factors,
        "modelVersion": "rules-v1",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
