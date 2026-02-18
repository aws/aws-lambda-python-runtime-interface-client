"""
Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import os
import unittest
from awslambdaric.lambda_config import LambdaConfigProvider


class TestLambdaConfigProvider(unittest.TestCase):
    def setUp(self):
        self.orig = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.orig)

    def test_handler_property_and_missing(self):
        cfg = LambdaConfigProvider(
            ["prog", "h.fn"], environ={"AWS_LAMBDA_RUNTIME_API": "a"}
        )
        self.assertEqual(cfg.handler, "h.fn")
        with self.assertRaises(ValueError):
            LambdaConfigProvider(["prog"], environ={"AWS_LAMBDA_RUNTIME_API": "a"})

    def test_api_address_property_and_missing(self):
        cfg = LambdaConfigProvider(
            ["prog", "h.fn"], environ={"AWS_LAMBDA_RUNTIME_API": "endpoint"}
        )
        self.assertEqual(cfg.api_address, "endpoint")
        with self.assertRaises(KeyError):
            LambdaConfigProvider(["prog", "h.fn"], environ={})

    def test_concurrency_and_is_elevator(self):
        env = {"AWS_LAMBDA_RUNTIME_API": "a", "AWS_LAMBDA_MAX_CONCURRENCY": "4"}
        cfg = LambdaConfigProvider(["p", "h.fn"], environ=env)
        self.assertEqual(cfg.max_concurrency, "4")
        self.assertTrue(cfg.is_elevator)
        env2 = {"AWS_LAMBDA_RUNTIME_API": "a"}
        cfg2 = LambdaConfigProvider(["p", "h.fn"], environ=env2)
        self.assertIsNone(cfg2.max_concurrency)
        self.assertFalse(cfg2.is_elevator)

    def test_use_thread_polling_flag(self):
        env = {
            "AWS_LAMBDA_RUNTIME_API": "a",
            "AWS_EXECUTION_ENV": "AWS_Lambda_python3.12",
        }
        cfg = LambdaConfigProvider(["p", "h.fn"], environ=env)
        self.assertTrue(cfg.use_thread_polling)
        env2 = {"AWS_LAMBDA_RUNTIME_API": "a", "AWS_EXECUTION_ENV": "OTHER"}
        cfg2 = LambdaConfigProvider(["p", "h.fn"], environ=env2)
        self.assertFalse(cfg2.use_thread_polling)

    def test_elevator_socket_path_property(self):
        env = {
            "AWS_LAMBDA_RUNTIME_API": "a",
            "_LAMBDA_TELEMETRY_LOG_FD_PROVIDER_SOCKET": "/sock",
        }
        cfg = LambdaConfigProvider(["p", "h.fn"], environ=env)
        self.assertEqual(cfg.elevator_socket_path, "/sock")

        # Test case where socket path env var is not set
        env2 = {"AWS_LAMBDA_RUNTIME_API": "a"}
        cfg2 = LambdaConfigProvider(["p", "h.fn"], environ=env2)
        self.assertIsNone(cfg2.elevator_socket_path)


if __name__ == "__main__":
    unittest.main()
