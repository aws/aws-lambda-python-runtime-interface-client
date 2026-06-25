"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
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

        expected = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", self.formatter.converter(record.created)
        )
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
