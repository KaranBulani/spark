from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    from pyspark.sql import SparkSession
except ImportError:  # pragma: no cover
    spark_home = os.environ.get("SPARK_HOME")
    if spark_home:
        spark_python_path = Path(spark_home) / "python"
        py4j_archives = sorted((spark_python_path / "lib").glob("py4j-*.zip"))
        sys.path.insert(0, str(spark_python_path))
        if py4j_archives:
            sys.path.insert(0, str(py4j_archives[0]))

    from pyspark.sql import SparkSession


def get_spark(config: dict | None = None) -> SparkSession:
    spark_config = (config or {}).get("spark", {})
    builder = SparkSession.builder.appName(spark_config.get("app_name", "dlp-redaction-poc")).master(
        spark_config.get("master", "local[*]")
    )

    for key, value in spark_config.get("configs", {}).items():
        builder = builder.config(key, value)

    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel(spark_config.get("log_level", "WARN").upper())
    return spark


def stop_spark(spark: SparkSession | None) -> None:
    if spark is not None:
        spark.stop()
