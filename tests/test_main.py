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
        # Non-elevator mode
        cfg = MagicMock()
        cfg.handler = "my.handler"
        cfg.api_address = "http://addr"
        cfg.use_thread_polling = False
        cfg.is_elevator = False
        mock_config_provider.return_value = cfg

        package_entry.main(["prog", "my.handler"])

        mock_client_cls.assert_called_once_with("http://addr", False)
        mock_bootstrap.run.assert_called_once_with(
            "my.handler", mock_client_cls.return_value
        )

    @patch("awslambdaric.__main__.ElevatorRunner")
    @patch("awslambdaric.__main__.LambdaConfigProvider")
    def test_elevator_path_dispatches_to_elevator_runner(
        self, mock_config_provider, mock_runner
    ):
        # Elevator mode
        cfg = MagicMock()
        cfg.handler = "my.handler"
        cfg.api_address = "http://addr"
        cfg.use_thread_polling = True
        cfg.is_elevator = True
        cfg.max_concurrency = "2"
        cfg.elevator_socket_path = "/tmp/elev.sock"
        mock_config_provider.return_value = cfg

        package_entry.main(["prog", "my.handler"])

        mock_runner.run_concurrent.assert_called_once_with(
            "my.handler", "http://addr", True, "/tmp/elev.sock", 2
        )


if __name__ == "__main__":
    unittest.main()
