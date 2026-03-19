from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

# Allow running with either `python .../redact_job.py` or `spark-submit`.
if __package__ in (None, ""):
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from src.dlp.dlp_client import DlpClient
from src.readers.data_reader import DEMO_CONTEXT, DEMO_REDACT_FIELD, extract_field_values, read_sample_records
from src.utils.logger import get_logger
from src.utils.spark_session import get_spark, stop_spark


def load_config(config_path: str | Path | None = None, env: str = "local") -> dict[str, Any]:
    """
    Load configuration from a YAML file.
    """
    if config_path is None:
        resolved_path = Path(__file__).resolve().parents[2] / "configs" / f"{env}.yaml"
    else:
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

    redact_field = job_config.get("job", {}).get("redact_field", DEMO_REDACT_FIELD)
    logger.info("Starting the simple redaction demo.")
    logger.info("Reading hardcoded demo records from data_reader.py.")

    records = read_sample_records()
    original_values = extract_field_values(records, redact_field)

    dlp_client = DlpClient(
        dlp_config=job_config.get("dlp", {}),
        gcp_config=job_config.get("gcp", {}),
        logger=logger,
    )
    encrypted_values = dlp_client.encrypt_values(original_values)
    decrypted_values = dlp_client.decrypt_values(encrypted_values)

    result_records: list[dict[str, Any]] = []
    for record, encrypted_value, decrypted_value in zip(records, encrypted_values, decrypted_values):
        result_record = dict(record)
        result_record[f"encrypted_{redact_field}"] = encrypted_value
        result_record[f"decrypted_{redact_field}"] = decrypted_value
        result_records.append(result_record)

    repeated_value_groups: dict[str, list[str | None]] = {}
    for original_value, encrypted_value in zip(original_values, encrypted_values):
        repeated_value_groups.setdefault(str(original_value), []).append(encrypted_value)

    same_input_same_output_examples = []
    for original_value, encrypted_group in repeated_value_groups.items():
        if len(encrypted_group) > 1:
            same_input_same_output_examples.append(
                {
                    "original_value": original_value,
                    "encrypted_values": encrypted_group,
                    "all_encrypted_values_match": len(set(encrypted_group)) == 1,
                }
            )

    spark = get_spark(job_config)
    logger.info("Spark session created. app_name=%s version=%s", spark.sparkContext.appName, spark.version)

    input_df = spark.createDataFrame(records)
    result_df = spark.createDataFrame(result_records)
    input_preview = [row.asDict() for row in input_df.collect()]
    result_preview = [row.asDict() for row in result_df.collect()]

    logger.info("Original values: %s", original_values)
    logger.info("Encrypted values: %s", encrypted_values)
    logger.info("Decrypted values: %s", decrypted_values)
    logger.info("Same input gives same output check: %s", same_input_same_output_examples)
    logger.info("Input dataframe preview: %s", input_preview)
    logger.info("Result dataframe preview: %s", result_preview)

    summary = {
        "environment": job_config.get("environment", env),
        "backend": job_config.get("dlp", {}).get("backend", "local"),
        "demo_context": deepcopy(DEMO_CONTEXT),
        "redact_field": redact_field,
        "original_values": original_values,
        "encrypted_values": encrypted_values,
        "decrypted_values": decrypted_values,
        "same_input_same_output_examples": same_input_same_output_examples,
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
