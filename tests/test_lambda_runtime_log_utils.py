"""
Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import logging
import json
import re
import time
import unittest

from awslambdaric.lambda_runtime_log_utils import JsonFormatter


class TestJsonFormatterTimestamp(unittest.TestCase):
    def setUp(self):
        self.formatter = JsonFormatter()
        self.logger = logging.getLogger("test")
        self.logger.setLevel(logging.INFO)

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
