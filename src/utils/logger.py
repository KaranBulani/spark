from __future__ import annotations

import logging


def get_logger(name: str = "spark-redaction-poc", level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.propagate = False

    # Optional GCP Cloud Logging integration for later:
    # from google.cloud import logging as cloud_logging
    # cloud_logging_client = cloud_logging.Client()
    # cloud_logging_client.setup_logging(log_level=getattr(logging, level.upper(), logging.INFO))

    return logger
