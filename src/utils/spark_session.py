from pyspark.sql import SparkSession


def get_spark():
    spark = (
        SparkSession.builder
        .appName("dlp-redaction-poc")
        .master("local[*]")
        .getOrCreate()
    )
    return spark