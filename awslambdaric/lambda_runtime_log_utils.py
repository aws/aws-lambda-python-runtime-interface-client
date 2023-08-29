"""
Copyright 2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import json
import logging
import traceback
from enum import IntEnum

_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
_RESERVED_FIELDS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "aws_request_id",
    "_frame_type",
}


class LogFormat(IntEnum):
    JSON = 0b0
    TEXT = 0b1

    @classmethod
    def from_str(cls, value: str):
        if value and value.upper() == "JSON":
            return cls.JSON.value
        return cls.TEXT.value


def _get_log_level_from_env_var(log_level):
    return {None: "", "TRACE": "DEBUG"}.get(log_level, log_level).upper()


_JSON_FRAME_TYPES = {
    logging.NOTSET: 0xA55A0002.to_bytes(4, "big"),
    logging.DEBUG: 0xA55A000A.to_bytes(4, "big"),
    logging.INFO: 0xA55A000E.to_bytes(4, "big"),
    logging.WARNING: 0xA55A0012.to_bytes(4, "big"),
    logging.ERROR: 0xA55A0016.to_bytes(4, "big"),
    logging.CRITICAL: 0xA55A001A.to_bytes(4, "big"),
}
_TEXT_FRAME_TYPES = {
    logging.NOTSET: 0xA55A0003.to_bytes(4, "big"),
    logging.DEBUG: 0xA55A000B.to_bytes(4, "big"),
    logging.INFO: 0xA55A000F.to_bytes(4, "big"),
    logging.WARNING: 0xA55A0013.to_bytes(4, "big"),
    logging.ERROR: 0xA55A0017.to_bytes(4, "big"),
    logging.CRITICAL: 0xA55A001B.to_bytes(4, "big"),
}
_DEFAULT_FRAME_TYPE = _TEXT_FRAME_TYPES[logging.NOTSET]

_json_encoder = json.JSONEncoder(ensure_ascii=False)
_encode_json = _json_encoder.encode


def _format_log_level(record: logging.LogRecord) -> int:
    return min(50, max(0, record.levelno)) // 10 * 10


class JsonFormatter(logging.Formatter):
    def __init__(self):
        super().__init__(datefmt=_DATETIME_FORMAT)

    @staticmethod
    def __format_stacktrace(exc_info):
        if not exc_info:
            return None
        return traceback.format_tb(exc_info[2])

    @staticmethod
    def __format_exception_name(exc_info):
        if not exc_info:
            return None

        return exc_info[0].__name__

    @staticmethod
    def __format_exception(exc_info):
        if not exc_info:
            return None

        return str(exc_info[1])

    @staticmethod
    def __format_location(record: logging.LogRecord):
        if not record.exc_info:
            return None

        return f"{record.pathname}:{record.funcName}:{record.lineno}"

    def format(self, record: logging.LogRecord) -> str:
        record.levelno = _format_log_level(record)
        record.levelname = logging.getLevelName(record.levelno)
        record._frame_type = _JSON_FRAME_TYPES.get(
            record.levelno, _JSON_FRAME_TYPES[logging.NOTSET]
        )

        result = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "stackTrace": self.__format_stacktrace(record.exc_info),
            "errorType": self.__format_exception_name(record.exc_info),
            "errorMessage": self.__format_exception(record.exc_info),
            "requestId": getattr(record, "aws_request_id", None),
            "location": self.__format_location(record),
        }
        result.update(
            (key, value)
            for key, value in record.__dict__.items()
            if key not in _RESERVED_FIELDS and key not in result
        )

        result = {k: v for k, v in result.items() if v is not None}

        return _encode_json(result) + "\n"
