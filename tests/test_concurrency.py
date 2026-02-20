"""
Copyright 2025 Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import multiprocessing
import unittest
from unittest.mock import patch, MagicMock

from awslambdaric.lambda_multi_concurrent_utils import MultiConcurrentRunner


class LambdaRuntimeConcurrencyTest(unittest.TestCase):
    def setUp(self):
        # common args
        self.handler = "h.fn"
        self.addr = "addr"
        self.use_thread = False
        self.socket = "/tmp/sock"

    def test_success_and_failure_isolation(self):
        success_counter = multiprocessing.Value("i", 0)
        fail_counter = multiprocessing.Value("i", 0)

        def fake_bootstrap_run(handler, lambda_runtime_client):
            pid = multiprocessing.current_process().pid
            if pid % 2 == 0:
                for _ in range(3):
                    with success_counter.get_lock():
                        success_counter.value += 1
            else:
                with fail_counter.get_lock():
                    fail_counter.value += 1
                raise RuntimeError("Simulated failure")

        with patch(
            "awslambdaric.lambda_multi_concurrent_utils.MultiConcurrentRunner._redirect_output"
        ), patch(
            "awslambdaric.lambda_multi_concurrent_utils.bootstrap.run",
            side_effect=fake_bootstrap_run,
        ):
            # spawn 4 multi-concurrent processes
            MultiConcurrentRunner.run_concurrent(
                self.handler, self.addr, self.use_thread, self.socket, max_concurrency=4
            )

        self.assertEqual(success_counter.value, 6)
        self.assertEqual(fail_counter.value, 2)


if __name__ == "__main__":
    unittest.main()
