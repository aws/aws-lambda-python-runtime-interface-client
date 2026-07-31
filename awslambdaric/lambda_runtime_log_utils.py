"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
"""

import json
import logging
import os
import traceback
from datetime import datetime, timezone
from enum import IntEnum

# TODO(v5.0): Remove this env var check and make milliseconds the default.
# Once removed, _format_timestamp simplifies to just the millis branch.
_TIMESTAMP_PRECISION_MILLIS = (
    os.environ.get("AWS_LAMBDA_LOG_TIMESTAMP_PRECISION", "").lower() == "milliseconds"
)


def _format_timestamp(epoch_secs):
    """Format a UTC timestamp in ISO 8601 format.

    Returns second precision by default (e.g. 2024-06-19T23:13:05Z), to avoid breaking changes.
    When AWS_LAMBDA_LOG_TIMESTAMP_PRECISION=milliseconds, includes
    milliseconds (e.g. 2024-06-19T23:13:05.068Z).
    """
    dt = datetime.fromtimestamp(epoch_secs, tz=timezone.utc)

    if _TIMESTAMP_PRECISION_MILLIS:
        millis = dt.microsecond // 1000
        return f"{dt:%Y-%m-%dT%H:%M:%S}.{millis:03d}Z"

    return f"{dt:%Y-%m-%dT%H:%M:%S}Z"


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
    "tenant_id",
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
        super().__init__()

    def formatTime(self, record, datefmt=None):
        return _format_timestamp(record.created)

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
        if hasattr(record, "tenant_id") and record.tenant_id is not None:
            result["tenantId"] = record.tenant_id

        result.update(
            (key, value)
            for key, value in record.__dict__.items()
            if key not in _RESERVED_FIELDS and key not in result
        )

        result = {k: v for k, v in result.items() if v is not None}

        return _encode_json(result) + "\n"
