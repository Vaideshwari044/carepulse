import logging
import re
import sys

import structlog


class TokenSanitizerFilter(logging.Filter):
    """Filter that redacts raw JWT tokens from log records."""
    TOKEN_REGEX = re.compile(r"token=[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+")

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.TOKEN_REGEX.sub("token=[REDACTED]", record.msg)
        if record.args:
            if isinstance(record.args, tuple):
                record.args = tuple(
                    self.TOKEN_REGEX.sub("token=[REDACTED]", arg) if isinstance(arg, str) else arg
                    for arg in record.args
                )
        return True


def configure_logging() -> None:
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            timestamper,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    token_filter = TokenSanitizerFilter()
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(token_filter)
    handler.setFormatter(logging.Formatter("%(message)s"))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.addFilter(token_filter)

