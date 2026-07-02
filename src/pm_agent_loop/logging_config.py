import logging
import re

_API_KEY_PATTERN = re.compile(r"sk-ant-[A-Za-z0-9_-]{10,}")
_LOGGER_NAME = "pm_agent_loop"


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        formatted = super().format(record)
        return _API_KEY_PATTERN.sub("[REDACTED]", formatted)


def configure_logging(level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(RedactingFormatter("%(levelname)s %(name)s: %(message)s"))
        logger.addHandler(handler)
    return logger
