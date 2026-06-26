"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
"""

import importlib
import logging
import json
import os
import time
import unittest
from unittest.mock import patch


class TestJsonFormatterTimestampDefaultPrecision(unittest.TestCase):
    def setUp(self):
        env = os.environ.copy()
        env.pop("AWS_LAMBDA_LOG_TIMESTAMP_PRECISION", None)
        with patch.dict(os.environ, env, clear=True):
            import awslambdaric.lambda_runtime_log_utils as mod

            importlib.reload(mod)
            self.formatter = mod.JsonFormatter()

    def test_timestamp_format_is_second_precision_with_z(self):
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="hello",
            args=None,
            exc_info=None,
        )
        output = self.formatter.format(record)
        log_entry = json.loads(output)
        timestamp = log_entry["timestamp"]

        pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
        self.assertRegex(
            timestamp,
            pattern,
            f"Timestamp '{timestamp}' does not match expected format YYYY-MM-DDTHH:MM:SSZ",
        )

    def test_timestamp_value_is_accurate(self):
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="hello",
            args=None,
            exc_info=None,
        )
        record.created = 1718838785.068
        output = self.formatter.format(record)
        log_entry = json.loads(output)

        expected = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created))
        self.assertEqual(log_entry["timestamp"], expected)

    def test_timestamp_does_not_include_milliseconds(self):
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="hello",
            args=None,
            exc_info=None,
        )
        record.created = 1718838785.999
        output = self.formatter.format(record)
        log_entry = json.loads(output)

        self.assertNotIn(".", log_entry["timestamp"])
        self.assertTrue(log_entry["timestamp"].endswith("Z"))

    def test_timestamps_same_within_same_second(self):
        record1 = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="first",
            args=None,
            exc_info=None,
        )
        record1.created = 1718838785.100

        record2 = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="second",
            args=None,
            exc_info=None,
        )
        record2.created = 1718838785.900

        output1 = json.loads(self.formatter.format(record1))
        output2 = json.loads(self.formatter.format(record2))

        self.assertEqual(output1["timestamp"], output2["timestamp"])


class TestJsonFormatterTimestampMillisecondPrecision(unittest.TestCase):
    def setUp(self):
        env = os.environ.copy()
        env["AWS_LAMBDA_LOG_TIMESTAMP_PRECISION"] = "milliseconds"
        with patch.dict(os.environ, env, clear=True):
            import awslambdaric.lambda_runtime_log_utils as mod

            importlib.reload(mod)
            self.formatter = mod.JsonFormatter()

    def test_timestamp_includes_milliseconds(self):
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="hello",
            args=None,
            exc_info=None,
        )
        output = self.formatter.format(record)
        log_entry = json.loads(output)
        timestamp = log_entry["timestamp"]

        pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$"
        self.assertRegex(
            timestamp,
            pattern,
            f"Timestamp '{timestamp}' does not match expected format YYYY-MM-DDTHH:MM:SS.mmmZ",
        )

    def test_timestamp_milliseconds_are_accurate(self):
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="hello",
            args=None,
            exc_info=None,
        )
        record.created = 1718838785.068
        output = self.formatter.format(record)
        log_entry = json.loads(output)

        self.assertEqual(log_entry["timestamp"], "2024-06-19T23:13:05.068Z")

    def test_timestamp_zero_milliseconds(self):
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="hello",
            args=None,
            exc_info=None,
        )
        record.created = 1718838785.0
        output = self.formatter.format(record)
        log_entry = json.loads(output)

        self.assertEqual(log_entry["timestamp"], "2024-06-19T23:13:05.000Z")

    def test_timestamps_differ_within_same_second(self):
        record1 = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="first",
            args=None,
            exc_info=None,
        )
        record1.created = 1718838785.100

        record2 = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="second",
            args=None,
            exc_info=None,
        )
        record2.created = 1718838785.200

        output1 = json.loads(self.formatter.format(record1))
        output2 = json.loads(self.formatter.format(record2))

        self.assertNotEqual(output1["timestamp"], output2["timestamp"])
        self.assertEqual(output1["timestamp"], "2024-06-19T23:13:05.100Z")
        self.assertEqual(output2["timestamp"], "2024-06-19T23:13:05.200Z")


class TestTimestampPrecisionVersionGate(unittest.TestCase):
    """Fails if we bump to v5+ without removing the seconds-precision path."""

    def test_v5_must_remove_timestamp_precision_env_var(self):
        from awslambdaric import __version__

        major = int(__version__.split(".")[0])
        if major >= 5:
            import awslambdaric.lambda_runtime_log_utils as mod

            self.assertFalse(
                hasattr(mod, "_TIMESTAMP_PRECISION_MILLIS"),
                "v5+: remove _TIMESTAMP_PRECISION_MILLIS and make milliseconds "
                "the default. See TODO(v5.0) in lambda_runtime_log_utils.py",
            )
