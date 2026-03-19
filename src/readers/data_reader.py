from __future__ import annotations

from copy import deepcopy
from typing import Any


DEFAULT_SAMPLE_RECORDS = [
    {"record_id": "001", "customer_ref": "CUST001234", "region": "APAC"},
    {"record_id": "002", "customer_ref": "ACCT998877", "region": "EMEA"},
    {"record_id": "003", "customer_ref": "USER554433", "region": "AMER"},
]


def read_sample_records(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Return local records that make the redaction flow easy to validate."""

    job_config = config.get("job", {})
    configured_records = job_config.get("sample_records")
    if configured_records:
        return deepcopy(configured_records)

    redact_field = job_config.get("redact_field", "customer_ref")
    sample_values = job_config.get("sample_values", [record["customer_ref"] for record in DEFAULT_SAMPLE_RECORDS])
    return [
        {"record_id": f"{index + 1:03d}", redact_field: str(value), "region": "LOCAL"}
        for index, value in enumerate(sample_values)
    ]


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
