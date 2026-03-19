from __future__ import annotations

from copy import deepcopy
from typing import Any

DEMO_REDACT_FIELD = "customer_ref"
DEMO_BATCH_ID = 101
DEMO_SHARED_CUSTOMER_REF = "CUST000111"
DEMO_SHARED_VIP_REF = "VIP777888"
DEMO_NOTE = "Same original value should get the same encrypted value."

DEMO_CONTEXT = {
    "demo_name": "Simple FPE walkthrough",
    "batch_id": DEMO_BATCH_ID,
    "note": DEMO_NOTE,
}

DEMO_RECORDS = [
    {
        "record_id": "001",
        DEMO_REDACT_FIELD: DEMO_SHARED_CUSTOMER_REF,
        "region": "APAC",
        "batch_id": DEMO_BATCH_ID,
        "owner": "Alice",
    },
    {
        "record_id": "002",
        DEMO_REDACT_FIELD: DEMO_SHARED_CUSTOMER_REF,
        "region": "EMEA",
        "batch_id": DEMO_BATCH_ID,
        "owner": "Bob",
    },
    {
        "record_id": "003",
        DEMO_REDACT_FIELD: DEMO_SHARED_VIP_REF,
        "region": "AMER",
        "batch_id": DEMO_BATCH_ID,
        "owner": "Carla",
    },
    {
        "record_id": "004",
        DEMO_REDACT_FIELD: DEMO_SHARED_VIP_REF,
        "region": "APAC",
        "batch_id": DEMO_BATCH_ID,
        "owner": "Deepak",
    },
    {
        "record_id": "005",
        DEMO_REDACT_FIELD: "USER123456",
        "region": "LATAM",
        "batch_id": DEMO_BATCH_ID,
        "owner": "Elena",
    },
]

def read_sample_records() -> list[dict[str, Any]]:
    """Return the hardcoded demo records used by the Spark redaction walkthrough."""
    return deepcopy(DEMO_RECORDS)

def extract_field_values(records: list[dict[str, Any]], field_name: str) -> list[str]:
    """Extract a target field from the sample record set."""
    return [str(record.get(field_name, "")) for record in records]

def read_bigquery_table(*_, **__):
    """Placeholder for the later BigQuery read path."""

    # Future Spark BigQuery read path:
    # return (
    #     spark.read.format("bigquery")
    #     .option("table", "project.dataset.input_table")
    #     .load()
    # )
    raise NotImplementedError("BigQuery reading is intentionally stubbed for the local POC.")
