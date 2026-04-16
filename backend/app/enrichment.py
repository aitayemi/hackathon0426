"""Risk enrichment service — adds business context to raw incidents."""

# Mock enrichment data for hackathon demo.
# In production, this would query internal systems for supplier profiles,
# lane metadata, SKU criticality, and SLA information.

SUPPLIER_PROFILES = {
    "Supplier A": {
        "criticality": "high",
        "leadTimeDays": 14,
        "alternateSuppliers": ["Supplier B", "Supplier C"],
        "region": "APAC",
    },
    "Supplier B": {
        "criticality": "medium",
        "leadTimeDays": 21,
        "alternateSuppliers": ["Supplier A"],
        "region": "EMEA",
    },
}

LANE_METADATA = {
    "Shanghai -> Phoenix": {
        "transitDays": 18,
        "carrier": "COSCO",
        "alternateLanes": ["Busan -> Phoenix", "Shanghai -> Los Angeles"],
        "volumePerWeek": 450,
    },
    "Busan -> Phoenix": {
        "transitDays": 16,
        "carrier": "Evergreen",
        "alternateLanes": ["Shanghai -> Phoenix"],
        "volumePerWeek": 200,
    },
}

SKU_CRITICALITY = {
    "SKU-101": {"revenue": "high", "safetyStockDays": 7, "customers": ["Customer-X"]},
    "SKU-204": {"revenue": "medium", "safetyStockDays": 14, "customers": ["Customer-X", "Customer-Y"]},
}


def enrich_incident(incident_data: dict) -> dict:
    """Add business context to an incident for Claude's analysis."""
    context = {}

    supplier = incident_data.get("supplier")
    if supplier and supplier in SUPPLIER_PROFILES:
        context["supplierProfile"] = SUPPLIER_PROFILES[supplier]

    lane = incident_data.get("affectedLane")
    if lane and lane in LANE_METADATA:
        context["laneMetadata"] = LANE_METADATA[lane]

    products = incident_data.get("affectedProducts", [])
    product_context = {}
    for sku in products:
        if sku in SKU_CRITICALITY:
            product_context[sku] = SKU_CRITICALITY[sku]
    if product_context:
        context["productCriticality"] = product_context

    customers = incident_data.get("priorityCustomers", [])
    if customers:
        context["priorityCustomers"] = customers
        context["customerImpactRisk"] = "high" if any(
            sku_data.get("revenue") == "high"
            for sku_data in product_context.values()
        ) else "medium"

    return context
