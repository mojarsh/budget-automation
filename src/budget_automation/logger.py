import json
import logging.config
from logging import Logger
from pathlib import Path


def configure_logging(logging_config_file: Path) -> Logger:
    """Set up logger based on logging config from JSON file."""

    with open(logging_config_file, encoding="utf8") as f:
        logging_config = json.load(f)

    logging.config.dictConfig(logging_config)
    return logging.getLogger(__name__)
