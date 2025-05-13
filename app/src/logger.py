import logging
from datetime import datetime
from typing import Optional, Dict, Any
import traceback
import sys
import os
from logging.handlers import RotatingFileHandler


class AppLogger:
    def __init__(self, name: str = "finance_app", log_level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)

        # Prevent adding handles multiple times
        if not self.logger.handlers:
            self._setup_handlers()


    def _setup_handlers(self):
        """Configuring logging handlers"""
        # Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(self._get_formatter())
        self.logger.addHandler(console_handler)

        # File handler with rotation
        os.makedirs("logs", exist_ok=True)
        
        # Info handler
        info_handler = RotatingFileHandler(
            "logs/info.log",
            maxBytes=100*1024*1024,
            backupCount=3
        )
        info_handler.setLevel(logging.INFO)
        info_handler.setFormatter(self._get_formatter())
        info_handler.addFilter(lambda record: record.levelno == logging.INFO)
        self.logger.addHandler(info_handler)

        # Warning handler
        warning_handler = RotatingFileHandler(
            "logs/warning.log",
            maxBytes=100*1024*1024,
            backupCount=3
        )
        warning_handler.setLevel(logging.WARNING)
        warning_handler.setFormatter(self._get_formatter())
        warning_handler.addFilter(lambda record: record.levelno == logging.WARNING)
        self.logger.addHandler(warning_handler)

        # Error handler (fixed this section)
        error_handler = RotatingFileHandler(
            "logs/error.log", 
            maxBytes=100*1024*1024,
            backupCount=3
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(self._get_formatter())
        error_handler.addFilter(lambda record: record.levelno == logging.ERROR)
        self.logger.addHandler(error_handler)

        # Critical handler
        critical_handler = RotatingFileHandler(
            "logs/critical.log",
            maxBytes=100*1024*1024,
            backupCount=3
        )
        critical_handler.setLevel(logging.CRITICAL)
        critical_handler.setFormatter(self._get_formatter())
        critical_handler.addFilter(lambda record: record.levelno == logging.CRITICAL)
        self.logger.addHandler(critical_handler)


    def _get_formatter(self):
        return logging.Formatter(
            '%(asctime)s - %(name)s - %(message)s'
        )


    def log(self, level: str, message: str, extra: Optional[Dict[str, Any]] = None):
        """Main Logging Method"""
        # getattr is a built-in Python function that in this case gets the attributes of this class (e.g. for example getting the logger.info() function, and executes that particular function)
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(message, extra=extra)


    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None):
        self.log("DEBUG", message, extra)

    def info(self, message: str, extra: Optional[Dict[str, Any]] = None):
        self.log("INFO", message, extra)

    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None):
        self.log("WARNING", message, extra)

    def error(self, message: str, extra: Optional[Dict[str, Any]] = None):
        self.log("ERROR", message, extra)
        exc_info = sys.exc_info()
        if exc_info[0] is not None:
            self.logger.error(traceback.format_exc())

    def critical(self, message: str, extra: Optional[Dict[str, Any]] = None):
        self.log("CRITICAL", message, extra)

    def exception(self, message: str, extra: Optional[Dict[str, Any]] = None):
        self.logger.exception(message, extra=extra)



# Initialising the default logger instance
logger = AppLogger()