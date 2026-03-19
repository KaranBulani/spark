from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

if __package__ in (None, ""):
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from src.dlp.dlp_client import DlpClient
from src.readers.data_reader import extract_field_values, read_sample_records
from src.utils.logger import get_logger
from src.utils.spark_session import get_spark, stop_spark


DEFAULT_CONFIG: dict[str, Any] = {
    "environment": "local",
    "spark": {
        "app_name": "dlp-redaction-poc-local",
        "master": "local[*]",
        "log_level": "WARN",
        "configs": {
            "spark.sql.shuffle.partitions": "2",
            "spark.ui.enabled": "false",
        },
    },
    "gcp": {
        "project_id": "local-demo-project",
        "location": "global",
        "bigquery": {
            "input_table": "local_project.raw.sample_customer_table",
            "output_table": "local_project.redacted.sample_customer_table",
        },
    },
    "dlp": {
        "backend": "local",
        "field_name": "customer_ref",
        "common_alphabet": "ALPHA_NUMERIC",
        "local_key": "spark-local-demo-key",
        "kms_key_name": "",
        "wrapped_key_base64": "",
        "unwrapped_key_base64": "",
    },
    "job": {
        "redact_field": "customer_ref",
        "sample_records": [
            {"record_id": "001", "customer_ref": "CUST001234", "region": "APAC"},
            {"record_id": "002", "customer_ref": "ACCT998877", "region": "EMEA"},
            {"record_id": "003", "customer_ref": "USER554433", "region": "AMER"},
        ],
    },
}


def load_config(config_path: str | Path | None = None, env: str = "local") -> dict[str, Any]:
    resolved_path = Path(config_path) if config_path else Path(__file__).resolve().parents[2] / "configs" / f"{env}.yaml"
    merged_config = deepcopy(DEFAULT_CONFIG)

    if resolved_path.exists():
        with resolved_path.open("r", encoding="utf-8") as config_file:
            loaded_config = yaml.safe_load(config_file) or {}
        return _deep_merge(merged_config, loaded_config)

    merged_config["environment"] = env
    return merged_config


def run_redact_job(
    config: dict[str, Any] | None = None,
    config_path: str | Path | None = None,
    env: str = "local",
    spark=None,
) -> dict[str, Any]:
    job_config = deepcopy(config) if config else load_config(config_path=config_path, env=env)
    logger = get_logger(name="src.spark_jobs.redact_job", level=job_config.get("spark", {}).get("log_level", "INFO"))
    redact_field = job_config.get("job", {}).get("redact_field", "customer_ref")

    records = read_sample_records(job_config)
    original_values = extract_field_values(records, redact_field)

    dlp_client = DlpClient(
        dlp_config=job_config.get("dlp", {}),
        gcp_config=job_config.get("gcp", {}),
        logger=logger,
    )
    encrypted_values = dlp_client.encrypt_values(original_values)
    decrypted_values = dlp_client.decrypt_values(encrypted_values)
    result_records = _build_result_records(records, redact_field, encrypted_values, decrypted_values)

    should_stop_spark = spark is None
    spark = spark or get_spark(job_config)

    logger.info("Spark session created. app_name=%s version=%s", spark.sparkContext.appName, spark.version)
    logger.info("Loaded %s sample records from data_reader.", len(records))
    logger.info("Original values: %s", original_values)
    logger.info("Encrypted values: %s", encrypted_values)
    logger.info("Decrypted values: %s", decrypted_values)

    input_df = spark.createDataFrame(records)
    result_df = spark.createDataFrame(result_records)
    input_preview = [row.asDict() for row in input_df.collect()]
    result_preview = [row.asDict() for row in result_df.collect()]

    logger.info("Input dataframe preview: %s", input_preview)
    logger.info("Result dataframe preview: %s", result_preview)

    summary = {
        "environment": job_config.get("environment", env),
        "backend": job_config.get("dlp", {}).get("backend", "local"),
        "redact_field": redact_field,
        "original_values": original_values,
        "encrypted_values": encrypted_values,
        "decrypted_values": decrypted_values,
        "input_records": input_preview,
        "result_records": result_preview,
        "spark": {
            "app_name": spark.sparkContext.appName,
            "master": spark.sparkContext.master,
            "version": spark.version,
        },
    }

    if should_stop_spark:
        stop_spark(spark)

    return summary


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _build_result_records(
    records: list[dict[str, Any]],
    redact_field: str,
    encrypted_values: list[str | None],
    decrypted_values: list[str | None],
) -> list[dict[str, Any]]:
    result_records: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        result_record = dict(record)
        result_record[f"encrypted_{redact_field}"] = encrypted_values[index]
        result_record[f"decrypted_{redact_field}"] = decrypted_values[index]
        result_records.append(result_record)
    return result_records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Spark redaction POC job.")
    parser.add_argument("--config", default=None, help="Optional path to a YAML config file.")
    parser.add_argument("--env", default="local", choices=["local", "dev", "prod"], help="Environment config to load.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run_redact_job(config_path=args.config, env=args.env)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
