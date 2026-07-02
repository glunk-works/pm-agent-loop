import io
import logging

from pm_agent_loop.logging_config import RedactingFormatter

_SYNTHETIC_KEY = "sk-ant-abcdefghij1234567890"


def test_log_emission_redacts_api_key_shaped_string():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(RedactingFormatter("%(message)s"))
    logger = logging.getLogger("test_redaction_logger")
    logger.setLevel(logging.INFO)
    logger.handlers = [handler]
    logger.propagate = False

    logger.info("Using key %s for auth", _SYNTHETIC_KEY)

    output = stream.getvalue()
    assert "[REDACTED]" in output
    assert _SYNTHETIC_KEY not in output
