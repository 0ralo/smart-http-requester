from __future__ import annotations

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Optional


DEFAULT_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logger(
    name: str = "smart_http_requester",
    log_dir: Optional[Path | str] = None,
    log_file: Optional[Path | str] = None,
    level: int = logging.INFO,
    rotate_days: int = 7,
) -> logging.Logger:
    log_dir_path = Path(log_dir or "logs")
    log_file_path = Path(log_file or log_dir_path / f"{name}.log")

    log_dir_path.mkdir(parents=True, exist_ok=True)
    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    if logger.handlers:
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()

    formatter = logging.Formatter(DEFAULT_LOG_FORMAT, datefmt=DEFAULT_DATE_FORMAT)
    file_handler = TimedRotatingFileHandler(
        filename=str(log_file_path),
        when="D",
        interval=1,
        backupCount=rotate_days,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    logger.addHandler(file_handler)

    return logger


logger = setup_logger()
