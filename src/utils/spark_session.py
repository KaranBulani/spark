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
