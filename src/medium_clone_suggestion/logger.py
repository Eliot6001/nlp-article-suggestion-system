# logger.py
import logging
import os
from logging.handlers import RotatingFileHandler

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] %(name)s.%(funcName)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Stream handler for console
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        # File handler only for errors
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, f"{name}.errors.log"),
            maxBytes=1024*1024, backupCount=3
        )
        file_handler.setLevel(logging.ERROR)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
