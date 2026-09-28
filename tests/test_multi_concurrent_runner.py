"""
Copyright 2025 Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import sys
import unittest
from unittest.mock import patch, MagicMock, call

from awslambdaric.lambda_multi_concurrent_utils import MultiConcurrentRunner


class TestMultiConcurrentRunnerRedirect(unittest.TestCase):
    @patch("socket.socket")
    @patch("os.dup2")
    def test_redirect_output_opens_two_sockets_and_dup2s(
        self, mock_dup2, mock_socket_cls
    ):
        sock1 = MagicMock()
        sock1.fileno.return_value = 10
        sock1.__enter__.return_value = sock1  # <-- key line
        sock1.__exit__.return_value = None

        sock2 = MagicMock()
        sock2.fileno.return_value = 11
        sock2.__enter__.return_value = sock2  # <-- key line
        sock2.__exit__.return_value = None

        mock_socket_cls.side_effect = [sock1, sock2]

        MultiConcurrentRunner._redirect_output("/fake/path")

        self.assertEqual(mock_socket_cls.call_count, 2)
        sock1.connect.assert_called_once_with("/fake/path")
        sock2.connect.assert_called_once_with("/fake/path")
        mock_dup2.assert_any_call(10, sys.stdout.fileno())
        mock_dup2.assert_any_call(11, sys.stderr.fileno())

        # With a context manager, prefer asserting __exit__ was called:
        self.assertEqual(sock1.__enter__.call_count, 1)
        self.assertEqual(sock1.__exit__.call_count, 1)
        self.assertEqual(sock2.__enter__.call_count, 1)
        self.assertEqual(sock2.__exit__.call_count, 1)

    @patch(
        "awslambdaric.lambda_multi_concurrent_utils.LambdaMultiConcurrentRuntimeClient"
    )
    @patch("awslambdaric.lambda_multi_concurrent_utils.bootstrap")
    def test_run_single_creates_client_and_calls_bootstrap(
        self, mock_bootstrap, mock_client_cls
    ):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        # stub out redirect
        with patch.object(MultiConcurrentRunner, "_redirect_output"):
            MultiConcurrentRunner.run_single("h.fn", "addr", True, "/socket")

        mock_client_cls.assert_called_once_with("addr", True)
        mock_bootstrap.run.assert_called_once_with("h.fn", mock_client)

    @patch.object(MultiConcurrentRunner, "_before_fork")
    @patch("multiprocessing.Process")
    def test_run_concurrent_spawns_and_joins(self, mock_process, mock_before_fork):
        fake_proc = MagicMock()
        mock_process.return_value = fake_proc

        MultiConcurrentRunner.run_concurrent(
            "h", "a", False, "/sock", max_concurrency=3
        )

        self.assertEqual(mock_process.call_count, 3)
        self.assertEqual(fake_proc.start.call_count, 3)
        self.assertEqual(fake_proc.join.call_count, 3)

        for call_args in mock_process.call_args_list:
            target = call_args.kwargs.get("target") or call_args[1].get("target")
            args = call_args.kwargs.get("args") or call_args[1].get("args")
            self.assertEqual(target, MultiConcurrentRunner.run_single)
            self.assertEqual(args, ("h", "a", False, "/sock"))

    @patch("awslambdaric.lambda_multi_concurrent_utils.logging")
    @patch("awslambdaric.lambda_multi_concurrent_utils.bootstrap")
    @patch("multiprocessing.Process")
    def test_run_concurrent_emits_worker_pool_event_once_before_spawning(
        self, mock_process, mock_bootstrap, mock_logging
    ):
        mock_process.return_value = MagicMock()
        order_tracker = MagicMock()
        order_tracker.attach_mock(mock_process, "process")

        with patch.object(
            MultiConcurrentRunner, "_emit_worker_pool_event"
        ) as mock_emit:
            with patch.object(MultiConcurrentRunner, "_run_pre_fork_hooks"):
                order_tracker.attach_mock(mock_emit, "emit")
                MultiConcurrentRunner.run_concurrent(
                    "h", "a", False, "/sock", max_concurrency=3
                )

        mock_emit.assert_called_once_with(3)
        self.assertEqual(order_tracker.mock_calls[0], call.emit(3))

    @patch("awslambdaric.lambda_multi_concurrent_utils.logging")
    def test_emit_worker_pool_event_emits_pool_size(self, mock_logging):
        with patch.object(MultiConcurrentRunner, "_redirect_output") as mock_redirect:
            MultiConcurrentRunner._emit_worker_pool_event(16)

        # Parent never redirects: RAPID wires its stdout at spawn.
        mock_redirect.assert_not_called()
        mock_logging.getLogger.return_value.debug.assert_called_once()
        event = mock_logging.getLogger.return_value.debug.call_args[0][0]
        self.assertEqual(event["workerCount"], 16)
        self.assertEqual(event["executionEnvironmentMaxConcurrency"], 16)
        # Setting up and releasing the sink is _before_fork's job now.
        mock_logging.getLogger.return_value.handlers.clear.assert_not_called()

    @patch(
        "awslambdaric.lambda_multi_concurrent_utils.LambdaMultiConcurrentRuntimeClient"
    )
    @patch("awslambdaric.lambda_multi_concurrent_utils.bootstrap")
    def test_run_single_skips_redirect_when_socket_path_is_none(
        self, mock_bootstrap, mock_client_cls
    ):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        with patch.object(MultiConcurrentRunner, "_redirect_output") as mock_redirect:
            MultiConcurrentRunner.run_single("h.fn", "addr", True, None)

        # Verify _redirect_output was not called
        mock_redirect.assert_not_called()

        # Verify client and bootstrap are still called normally
        mock_client_cls.assert_called_once_with("addr", True)
        mock_bootstrap.run.assert_called_once_with("h.fn", mock_client)

    @patch(
        "awslambdaric.lambda_multi_concurrent_utils.LambdaMultiConcurrentRuntimeClient"
    )
    @patch("awslambdaric.lambda_multi_concurrent_utils.bootstrap")
    def test_run_single_calls_redirect_when_socket_path_is_provided(
        self, mock_bootstrap, mock_client_cls
    ):
        """Test that _redirect_output is called when socket_path is provided"""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        with patch.object(MultiConcurrentRunner, "_redirect_output") as mock_redirect:
            MultiConcurrentRunner.run_single("h.fn", "addr", True, "/valid/socket/path")

        # Verify _redirect_output was called with the socket path
        mock_redirect.assert_called_once_with("/valid/socket/path")

        # Verify client and bootstrap are still called normally
        mock_client_cls.assert_called_once_with("addr", True)
        mock_bootstrap.run.assert_called_once_with("h.fn", mock_client)


if __name__ == "__main__":
    unittest.main()
