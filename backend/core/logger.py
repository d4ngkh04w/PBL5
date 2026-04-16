import logging
import os
import time

from colorama import Fore, Style, init

from core.config import DEBUG_MODE, LOG_DIR, LOG_FORMAT, DATE_FORMAT

init(autoreset=True)


class CustomFormatter(logging.Formatter):
    """Lớp định dạng log tùy chỉnh có hỗ trợ màu sắc"""

    SHORT_LEVELS = {
        "DEBUG": "DBG",
        "INFO": "INF",
        "WARNING": "WRN",
        "ERROR": "ERR",
        "CRITICAL": "CRT",
    }
    COLORS = {
        "DBG": Fore.CYAN,
        "INF": Fore.GREEN,
        "WRN": Fore.YELLOW,
        "ERR": Fore.RED,
        "CRT": Fore.RED + Style.BRIGHT,
    }

    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
        use_color: bool = False,
    ):
        super().__init__(fmt=fmt, datefmt=datefmt)
        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        original_levelname = record.levelname
        short_level = self.SHORT_LEVELS.get(original_levelname, original_levelname)

        if self.use_color:
            color = self.COLORS.get(short_level, "")
            record.levelname = f"{color}{short_level}{Style.RESET_ALL}"
        else:
            record.levelname = short_level

        result = super().format(record)
        record.levelname = original_levelname
        return result


class LoggerPrefixFilter(logging.Filter):
    def __init__(self, prefixes: tuple[str, ...], include: bool = True):
        super().__init__()
        self.prefixes = tuple(prefixes)
        self.include = include

    def filter(self, record: logging.LogRecord) -> bool:
        matched = record.name.startswith(self.prefixes)
        return matched if self.include else not matched


def get_logger_config():
    os.makedirs(LOG_DIR, exist_ok=True)
    today = time.strftime("%Y-%m-%d")
    log_level = "DEBUG" if DEBUG_MODE else "INFO"

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "console_formatter": {
                "()": "core.logger.CustomFormatter",
                "fmt": LOG_FORMAT,
                "datefmt": DATE_FORMAT,
                "use_color": True,
            },
            "file_formatter": {
                "()": "core.logger.CustomFormatter",
                "fmt": LOG_FORMAT,
                "datefmt": DATE_FORMAT,
                "use_color": False,
            },
        },
        "filters": {
            "request_filter": {
                "()": "core.logger.LoggerPrefixFilter",
                "prefixes": ("request", "uvicorn.access"),
                "include": True,
            },
            "prediction_filter": {
                "()": "core.logger.LoggerPrefixFilter",
                "prefixes": ("prediction",),
                "include": True,
            },
            "console_filter": {
                "()": "core.logger.LoggerPrefixFilter",
                "prefixes": ("console", "uvicorn", "fastapi"),
                "include": True,
            },
        },
        "handlers": {
            "console_handler": {
                "class": "logging.StreamHandler",
                "formatter": "console_formatter",
                "filters": ["console_filter"],
                "stream": "ext://sys.stdout",
            },
            "request_file_handler": {
                "class": "logging.FileHandler",
                "formatter": "file_formatter",
                "filters": ["request_filter"],
                "filename": f"{LOG_DIR}/request_{today}.log",
                "mode": "a",
                "encoding": "utf-8",
            },
            "prediction_file_handler": {
                "class": "logging.FileHandler",
                "formatter": "file_formatter",
                "filters": ["prediction_filter"],
                "filename": f"{LOG_DIR}/prediction_{today}.log",
                "mode": "a",
                "encoding": "utf-8",
            },
        },
        "loggers": {
            "uvicorn": {
                "handlers": ["console_handler"],
                "level": log_level,
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["console_handler", "request_file_handler"],
                "level": log_level,
                "propagate": False,
            },
        },
        "root": {
            "handlers": [
                "console_handler",
                "request_file_handler",
                "prediction_file_handler",
            ],
            "level": log_level,
        },
    }
