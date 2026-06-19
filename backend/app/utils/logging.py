import json
import logging
from contextvars import ContextVar

_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id():
    return _request_id_ctx.get()


def set_request_id(value: str):
    _request_id_ctx.set(value)


class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = _request_id_ctx.get()
        return True


class StructFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", ""),
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }, ensure_ascii=False)


def setup_logging(log_format: str, log_level: str) -> logging.Logger:
    if log_format == "json":
        _fmt = StructFormatter(datefmt="%Y-%m-%dT%H:%M:%S")
    else:
        _fmt = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | [%(request_id)s] | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    _handler = logging.StreamHandler()
    _handler.setFormatter(_fmt)
    _handler.addFilter(RequestIdFilter())

    logging.basicConfig(level=getattr(logging, log_level, logging.INFO), handlers=[_handler])
    return logging.getLogger("quizapp")
