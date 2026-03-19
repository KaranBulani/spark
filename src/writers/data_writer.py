from __future__ import annotations

from typing import Any


def write_preview(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return the records so tests and local runs can inspect the final payload."""

    return records


def write_bigquery_table(*_, **__):
    """Placeholder for the future BigQuery write path."""

    # Future Spark BigQuery write path:
    # (
    #     dataframe.write.format("bigquery")
    #     .option("table", "project.dataset.output_table")
    #     .mode("overwrite")
    #     .save()
    # )
    raise NotImplementedError("BigQuery writing is intentionally stubbed for the local POC.")
