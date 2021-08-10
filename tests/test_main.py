"""
Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import os
import unittest
from unittest.mock import patch

import awslambdaric.__main__ as package_entry


class TestEnvVars(unittest.TestCase):
    def setUp(self):
        self.org_os_environ = os.environ

    def tearDown(self):
        os.environ = self.org_os_environ

    @patch("awslambdaric.__main__.bootstrap")
    def test_main(self, mock_bootstrap):
        expected_app_root = os.getcwd()
        expected_handler = "app.my_test_handler"
        expected_lambda_runtime_api_addr = "test_addr"

        args = ["dummy", expected_handler, "other_dummy"]

        os.environ["AWS_LAMBDA_RUNTIME_API"] = expected_lambda_runtime_api_addr

        package_entry.main(args)

        mock_bootstrap.run.assert_called_once_with(
            expected_app_root, expected_handler, expected_lambda_runtime_api_addr
        )
