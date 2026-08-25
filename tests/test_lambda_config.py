"""
Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import os
import sys
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

    def test_concurrency_and_is_multi_concurrent(self):
        env = {"AWS_LAMBDA_RUNTIME_API": "a", "AWS_LAMBDA_MAX_CONCURRENCY": "4"}
        cfg = LambdaConfigProvider(["p", "h.fn"], environ=env)
        self.assertEqual(cfg.max_concurrency, "4")
        self.assertTrue(cfg.is_multi_concurrent)
        env2 = {"AWS_LAMBDA_RUNTIME_API": "a"}
        cfg2 = LambdaConfigProvider(["p", "h.fn"], environ=env2)
        self.assertIsNone(cfg2.max_concurrency)
        self.assertFalse(cfg2.is_multi_concurrent)

    def test_use_thread_polling_disabled_for_unsupported_managed_envs(self):
        # Managed runtimes on the denylist never use thread polling,
        # regardless of the Python version the code happens to run on.
        for exec_env in LambdaConfigProvider.UNSUPPORTED_THREADPOLLING_ENVS:
            env = {
                "AWS_LAMBDA_RUNTIME_API": "a",
                "AWS_EXECUTION_ENV": exec_env,
            }
            cfg = LambdaConfigProvider(["p", "h.fn"], environ=env)
            self.assertFalse(
                cfg.use_thread_polling,
                msg=f"expected thread polling disabled for {exec_env}",
            )

    def test_use_thread_polling_enabled_for_custom_oci_image(self):
        # Custom OCI images (AWS_Lambda_Image) are not on the denylist and
        # fall back to the minimum-supported Python version check.
        env = {
            "AWS_LAMBDA_RUNTIME_API": "a",
            "AWS_EXECUTION_ENV": "AWS_Lambda_Image",
        }
        cfg = LambdaConfigProvider(["p", "h.fn"], environ=env)
        self.assertEqual(cfg.use_thread_polling, sys.version_info >= (3, 4))

    def test_use_thread_polling_enabled_for_supported_managed_env(self):
        # Managed runtimes not on the denylist (e.g. newer versions) fall
        # back to the Python version check.
        env = {
            "AWS_LAMBDA_RUNTIME_API": "a",
            "AWS_EXECUTION_ENV": "AWS_Lambda_python3.12",
        }
        cfg = LambdaConfigProvider(["p", "h.fn"], environ=env)
        self.assertEqual(cfg.use_thread_polling, sys.version_info >= (3, 4))

    def test_use_thread_polling_without_execution_env(self):
        # With no AWS_EXECUTION_ENV set, fall back to the version check.
        env = {"AWS_LAMBDA_RUNTIME_API": "a"}
        cfg = LambdaConfigProvider(["p", "h.fn"], environ=env)
        self.assertEqual(cfg.use_thread_polling, sys.version_info >= (3, 4))

    def test_lmi_socket_path_property(self):
        env = {
            "AWS_LAMBDA_RUNTIME_API": "a",
            "_LAMBDA_TELEMETRY_LOG_FD_PROVIDER_SOCKET": "/sock",
        }
        cfg = LambdaConfigProvider(["p", "h.fn"], environ=env)
        self.assertEqual(cfg.lmi_socket_path, "/sock")

        # Test case where socket path env var is not set
        env2 = {"AWS_LAMBDA_RUNTIME_API": "a"}
        cfg2 = LambdaConfigProvider(["p", "h.fn"], environ=env2)
        self.assertIsNone(cfg2.lmi_socket_path)


if __name__ == "__main__":
    unittest.main()
