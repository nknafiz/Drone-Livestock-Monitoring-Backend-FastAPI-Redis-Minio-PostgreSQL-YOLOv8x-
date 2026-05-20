"""
Structured logging setup for production.
Supports both JSON and text formats with rotation.
"""
import logging
import logging.handlers
import json
import sys
from pathlib import Path
from datetime import datetime

from config.settings import settings

# pythonjsonlogger সম্পূর্ণ বাদ — নিজের formatter লিখছি


class JSONFormatter(logging.Formatter):
    """
    Pure custom JSON formatter — no third-party dependency.
    pythonjsonlogger এর 'message' overwrite bug এড়াতে এটা ব্যবহার করা হচ্ছে।
    """

    # LogRecord এর built-in attributes — এগুলো extra হিসেবে আসলে skip করবো
    _SKIP_ATTRS = {
        "msg", "args", "levelname", "levelno", "pathname", "filename",
        "module", "exc_info", "exc_text", "stack_info", "lineno",
        "funcName", "created", "msecs", "relativeCreated", "thread",
        "threadName", "processName", "process", "name", "message",
    }

    def format(self, record: logging.LogRecord) -> str:
        # exc info format করো আগে (side effect: record.exc_text set হয়)
        if record.exc_info:
            self.formatException(record.exc_info)

        log_data = {
            "message": record.getMessage(),  # ✅ সরাসরি getMessage()
            "taskName": getattr(record, "taskName", None),
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
        }

        # extra fields যোগ করো — reserved keys বাদ দিয়ে
        for key, value in record.__dict__.items():
            if key not in self._SKIP_ATTRS and not key.startswith("_"):
                log_data[key] = value

        # taskName None হলে বাদ দাও
        if log_data.get("taskName") is None:
            log_data.pop("taskName", None)

        # Exception info যোগ করো
        if record.exc_text:
            log_data["exception"] = record.exc_text

        return json.dumps(log_data, ensure_ascii=False, default=str)


class TextFormatter(logging.Formatter):
    """Custom text formatter with colors for console output."""

    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
    }
    RESET = "\033[0m"

    def format(self, record):
        if sys.stdout.isatty():
            color = self.COLORS.get(record.levelname, self.RESET)
            record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging() -> logging.Logger:
    """Configure structured logging for the application."""

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    if settings.LOG_FORMAT == "json":
        formatter = JSONFormatter()  # ✅ pythonjsonlogger নেই

        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "app.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=10,
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    else:
        fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "app.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=10,
        )
        file_handler.setFormatter(logging.Formatter(fmt))
        root_logger.addHandler(file_handler)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(TextFormatter(fmt))
        root_logger.addHandler(console_handler)

    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)