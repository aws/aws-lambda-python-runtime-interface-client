"""
Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import unittest
from unittest.mock import MagicMock, patch

import awslambdaric.__main__ as package_entry


class TestMain(unittest.TestCase):
    @patch("awslambdaric.__main__.bootstrap")
    @patch("awslambdaric.__main__.LambdaRuntimeClient")
    @patch("awslambdaric.__main__.LambdaConfigProvider")
    def test_default_path_invokes_runtime_client_and_bootstrap(
        self, mock_config_provider, mock_client_cls, mock_bootstrap
    ):
        # Non-multi-concurrent mode
        cfg = MagicMock()
        cfg.handler = "my.handler"
        cfg.api_address = "http://addr"
        cfg.use_thread_polling = False
        cfg.is_multi_concurrent = False
        mock_config_provider.return_value = cfg

        package_entry.main(["prog", "my.handler"])

        mock_client_cls.assert_called_once_with("http://addr", False)
        mock_bootstrap.run.assert_called_once_with(
            "my.handler", mock_client_cls.return_value
        )

    @patch("awslambdaric.__main__.MultiConcurrentRunner")
    @patch("awslambdaric.__main__.LambdaConfigProvider")
    def test_multi_concurrent_path_dispatches_to_multi_concurrent_runner(
        self, mock_config_provider, mock_runner
    ):
        # Multi-concurrent mode
        cfg = MagicMock()
        cfg.handler = "my.handler"
        cfg.api_address = "http://addr"
        cfg.use_thread_polling = True
        cfg.is_multi_concurrent = True
        cfg.max_concurrency = "2"
        cfg.lmi_socket_path = "/tmp/lmi.sock"
        mock_config_provider.return_value = cfg

        package_entry.main(["prog", "my.handler"])

        mock_runner.run_concurrent.assert_called_once_with(
            "my.handler", "http://addr", True, "/tmp/lmi.sock", 2
        )


if __name__ == "__main__":
    unittest.main()
