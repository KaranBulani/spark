from __future__ import annotations

from src.spark_jobs.redact_job import load_config, run_redact_job


def test_load_config_reads_local_yaml() -> None:
    config = load_config(env="local")

    assert config["environment"] == "local"
    assert config["dlp"]["backend"] == "local"
    assert config["job"]["redact_field"] == "customer_ref"


def test_run_redact_job_returns_round_trip_results() -> None:
    result = run_redact_job(env="local")
    decrypted_result_values = [row["decrypted_customer_ref"] for row in result["result_records"]]

    assert result["encrypted_values"] != result["original_values"]
    assert result["decrypted_values"] == result["original_values"]
    assert decrypted_result_values == result["original_values"]
    assert result["spark"]["app_name"] == "simple-fpe-demo-local"
    assert result["same_input_same_output_examples"]
    assert result["same_input_same_output_examples"][0]["all_encrypted_values_match"] is True
