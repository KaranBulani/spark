from __future__ import annotations

from pathlib import Path

from src.spark_jobs.redact_job import load_config, run_redact_job


def test_load_config_reads_local_yaml() -> None:
    config = load_config(Path(__file__).resolve().parents[2] / "configs" / "local.yaml")

    assert config["environment"] == "local"
    assert config["dlp"]["backend"] == "local"
    assert config["job"]["redact_field"] == "customer_ref"


def test_run_redact_job_returns_round_trip_results(spark) -> None:
    config = {
        "environment": "test",
        "spark": {
            "app_name": "pytest-dlp-redaction-poc",
            "master": "local[2]",
            "log_level": "ERROR",
            "configs": {
                "spark.ui.enabled": "false",
            },
        },
        "gcp": {"project_id": "test-project", "location": "global"},
        "dlp": {
            "backend": "local",
            "field_name": "customer_ref",
            "common_alphabet": "ALPHA_NUMERIC",
            "local_key": "unit-test-key",
        },
        "job": {
            "redact_field": "customer_ref",
            "sample_records": [
                {"record_id": "001", "customer_ref": "CUST001234", "region": "APAC"},
                {"record_id": "002", "customer_ref": "ACCT998877", "region": "EMEA"},
            ],
        },
    }

    result = run_redact_job(config=config, spark=spark)

    assert result["encrypted_values"] != result["original_values"]
    assert result["decrypted_values"] == result["original_values"]
    assert result["spark"]["app_name"] == "pytest-dlp-redaction-poc"
    assert result["result_records"][0]["decrypted_customer_ref"] == "CUST001234"
