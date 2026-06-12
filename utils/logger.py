"""
Logger — console + file logging.
"""

import os
import logging
from datetime import datetime


class Logger:
    def __init__(self, log_dir: str = "output/logs"):
        os.makedirs(log_dir, exist_ok=True)
        self._log_dir = log_dir
        self._logger = logging.getLogger("CBandTest")
        self._logger.setLevel(logging.DEBUG)

        # Console
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S"))
        self._logger.addHandler(ch)

        # File
        filename = datetime.now().strftime("test_log_%Y%m%d_%H%M%S.log")
        fh = logging.FileHandler(os.path.join(log_dir, filename), encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        self._logger.addHandler(fh)

    def info(self, msg):
        self._logger.info(msg)

    def warning(self, msg):
        self._logger.warning(msg)

    def error(self, msg):
        self._logger.error(msg)

    def debug(self, msg):
        self._logger.debug(msg)
