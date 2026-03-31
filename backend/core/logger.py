import logging
import pathlib
import time


class CustomFormatter(logging.Formatter):
    """
    Lớp định dạng log tùy chỉnh
    """

    SHORT_LEVELS = {
        "DEBUG": "DBG",
        "INFO": "INF",
        "WARNING": "WRN",
        "ERROR": "ERR",
        "CRITICAL": "CRT",
    }

    def __init__(self):
        super().__init__()

    def format(self, record: logging.LogRecord) -> str:
        record.levelname = self.SHORT_LEVELS.get(record.levelname, record.levelname)

        log_format = "[%(levelname)s] [%(asctime)s] - %(message)s"

        formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


class LoggerPrefixFilter(logging.Filter):

    def __init__(self, prefixes: tuple[str, ...], include: bool = True):
        super().__init__()
        self.prefixes = prefixes
        self.include = include

    def filter(self, record: logging.LogRecord) -> bool:
        matched = record.name.startswith(self.prefixes)
        return matched if self.include else not matched


def setup_logger(debug: bool = False, log_dir: str = "logs"):
    """
    Thiết lập và cấu hình logger
    """
    today = time.strftime("%Y-%m-%d")
    request_log_file = f"{log_dir}/request_{today}.log"
    prediction_log_file = f"{log_dir}/prediction_{today}.log"

    pathlib.Path(log_dir).mkdir(parents=True, exist_ok=True)

    log_level = logging.DEBUG if debug else logging.INFO

    formatter = CustomFormatter()

    request_handler = logging.FileHandler(request_log_file, mode="a", encoding="utf-8")
    request_handler.setFormatter(formatter)
    request_handler.addFilter(LoggerPrefixFilter(("request",), include=True))

    prediction_handler = logging.FileHandler(
        prediction_log_file,
        mode="a",
        encoding="utf-8",
    )
    prediction_handler.setFormatter(formatter)
    prediction_handler.addFilter(LoggerPrefixFilter(("prediction",), include=True))

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.addFilter(LoggerPrefixFilter(("console",), include=True))

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        handler.close()

    root_logger.addHandler(request_handler)
    root_logger.addHandler(prediction_handler)
    root_logger.addHandler(console_handler)
    return logging.getLogger(__name__)
