"""
Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import decimal
import os
import unittest
from parameterized import parameterized
from awslambdaric.lambda_runtime_marshaller import to_json


class TestLambdaRuntimeMarshaller(unittest.TestCase):
    execution_envs = (
        "AWS_Lambda_python3.13",
        "AWS_Lambda_python3.12",
        "AWS_Lambda_python3.11",
        "AWS_Lambda_python3.10",
        "AWS_Lambda_python3.9",
    )

    envs_lambda_marshaller_ensure_ascii_false = {
        "AWS_Lambda_python3.12",
        "AWS_Lambda_python3.13",
    }

    execution_envs_lambda_marshaller_ensure_ascii_true = tuple(
        set(execution_envs).difference(envs_lambda_marshaller_ensure_ascii_false)
    )
    execution_envs_lambda_marshaller_ensure_ascii_false = tuple(
        envs_lambda_marshaller_ensure_ascii_false
    )

    def setUp(self):
        self.org_os_environ = os.environ

    def tearDown(self):
        os.environ = self.org_os_environ

    def test_to_json_decimal_encoding(self):
        response = to_json({"pi": decimal.Decimal("3.14159")})
        self.assertEqual('{"pi": 3.14159}', response)

    def test_to_json_decimal_encoding_nan(self):
        response = to_json({"pi": decimal.Decimal("nan")})
        self.assertEqual('{"pi": NaN}', response)

    def test_to_json_decimal_encoding_negative_nan(self):
        response = to_json({"pi": decimal.Decimal("-nan")})
        self.assertEqual('{"pi": NaN}', response)

    def test_json_serializer_is_not_default_json(self):
        from awslambdaric.lambda_runtime_marshaller import (
            json as internal_json,
        )
        import simplejson as simplejson
        import json as stock_json
        import json

        self.assertEqual(json, stock_json)
        self.assertNotEqual(stock_json, internal_json)
        self.assertNotEqual(stock_json, simplejson)

        internal_json.YOLO = "bello"
        self.assertTrue(hasattr(internal_json, "YOLO"))
        self.assertFalse(hasattr(stock_json, "YOLO"))
        self.assertTrue(hasattr(simplejson, "YOLO"))

    @parameterized.expand(execution_envs_lambda_marshaller_ensure_ascii_false)
    def test_to_json_unicode_not_escaped_encoding(self, execution_env):
        os.environ = {"AWS_EXECUTION_ENV": execution_env}
        response = to_json({"price": "£1.00"})
        self.assertEqual('{"price": "£1.00"}', response)
        self.assertNotEqual('{"price": "\\u00a31.00"}', response)
        self.assertEqual(
            19, len(response.encode("utf-8"))
        )  # would be 23 bytes if a unicode escape was returned

    @parameterized.expand(execution_envs_lambda_marshaller_ensure_ascii_true)
    def test_to_json_unicode_is_escaped_encoding(self, execution_env):
        os.environ = {"AWS_EXECUTION_ENV": execution_env}
        response = to_json({"price": "£1.00"})
        self.assertEqual('{"price": "\\u00a31.00"}', response)
        self.assertNotEqual('{"price": "£1.00"}', response)
        self.assertEqual(
            23, len(response.encode("utf-8"))
        )  # would be 19 bytes if a escaped was returned
