from __future__ import annotations

import pytest

from src.utils.spark_session import get_spark, stop_spark


@pytest.fixture(scope="session")
def spark():
    spark_session = get_spark(
        {
            "spark": {
                "app_name": "pytest-dlp-redaction-poc",
                "master": "local[2]",
                "log_level": "ERROR",
                "configs": {
                    "spark.ui.enabled": "false",
                    "spark.sql.shuffle.partitions": "2",
                },
            }
        }
    )
    yield spark_session
    stop_spark(spark_session)
