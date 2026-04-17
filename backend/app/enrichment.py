"""Risk enrichment — adds business context before Claude sees the incident.

In production this queries internal systems. For hackathon, mock data."""

SUPPLIERS = {
    "Supplier A": {
        "criticality": "high", "leadTimeDays": 14,
        "alternates": ["Supplier B", "Supplier C"], "region": "APAC",
    },
    "Supplier B": {
        "criticality": "medium", "leadTimeDays": 21,
        "alternates": ["Supplier A"], "region": "EMEA",
    },
}

LANES = {
    "Shanghai -> Phoenix": {
        "transitDays": 18, "carrier": "COSCO",
        "alternates": ["Busan -> Phoenix", "Shanghai -> Los Angeles"],
        "volumePerWeek": 450,
    },
    "Busan -> Phoenix": {
        "transitDays": 16, "carrier": "Evergreen",
        "alternates": ["Shanghai -> Phoenix"], "volumePerWeek": 200,
    },
}

SKUS = {
    "SKU-101": {"revenue": "high", "safetyStockDays": 7, "customers": ["Customer-X"]},
    "SKU-204": {"revenue": "medium", "safetyStockDays": 14, "customers": ["Customer-X", "Customer-Y"]},
    "SKU-305": {"revenue": "high", "safetyStockDays": 5, "customers": ["Customer-Y"]},
    "SKU-410": {"revenue": "low", "safetyStockDays": 30, "customers": []},
    "SKU-550": {"revenue": "medium", "safetyStockDays": 10, "customers": ["Customer-Z"]},
}


def enrich_incident(data: dict) -> dict:
    """Add supplier, lane, SKU context for Claude's analysis."""
    ctx = {}

    supplier = data.get("supplier")
    if supplier and supplier in SUPPLIERS:
        ctx["supplierProfile"] = SUPPLIERS[supplier]

    lane = data.get("affectedLane")
    if lane and lane in LANES:
        ctx["laneMetadata"] = LANES[lane]

    products = data.get("affectedProducts", [])
    sku_ctx = {s: SKUS[s] for s in products if s in SKUS}
    if sku_ctx:
        ctx["productCriticality"] = sku_ctx

    customers = data.get("priorityCustomers", [])
    if customers:
        ctx["priorityCustomers"] = customers
        ctx["customerImpactRisk"] = (
            "high" if any(v.get("revenue") == "high" for v in sku_ctx.values())
            else "medium"
        )

    return ctx
