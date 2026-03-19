from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

#spark-submit src/spark_jobs/redact_job.py --config configs/local.yaml
#spark-submit redact_job.py --config configs/local.yaml
# Purpose to run both ways
if __package__ in (None, ""):
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from src.dlp.dlp_client import DlpClient
from src.readers.data_reader import extract_field_values, read_sample_records
from src.utils.logger import get_logger
from src.utils.spark_session import get_spark, stop_spark


def load_config(config_path: str | Path) -> dict[str, Any]:
    """
    Load configuration strictly from a given YAML file.
    """
    resolved_path = Path(config_path)

    if not resolved_path.exists():
        raise FileNotFoundError(f"Config file not found: {resolved_path}")

    with resolved_path.open("r", encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)

    if not config:
        raise ValueError("Config file is empty or invalid")

    return config

def run_redact_job(
    config_path: str | Path | None = None,
    env: str = "local",
) -> dict[str, Any]:

    job_config = load_config(config_path=config_path, env=env)
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

    spark = get_spark(job_config)

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

    stop_spark(spark)

    return summary


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
    return parser.parse_args() # Namespace(config='configs/local.yaml', env='local')


def main() -> None:
    args = parse_args()
    summary = run_redact_job(config_path=args.config, env=args.env) # run_redact_job(config_path='configs/local.yaml', env='local')
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
