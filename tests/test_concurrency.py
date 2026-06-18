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
        manager = multiprocessing.Manager()
        success_counter = manager.Value("i", 0)
        fail_counter = manager.Value("i", 0)
        process_index = manager.Value("i", 0)
        lock = manager.Lock()

        def fake_bootstrap_run(handler, lambda_runtime_client):
            with lock:
                idx = process_index.value
                process_index.value += 1
            if idx % 2 == 0:
                for _ in range(3):
                    with lock:
                        success_counter.value += 1
            else:
                with lock:
                    fail_counter.value += 1
                raise RuntimeError("Simulated failure")

        with patch(
            "awslambdaric.lambda_multi_concurrent_utils.MultiConcurrentRunner._redirect_output"
        ), patch(
            "awslambdaric.lambda_multi_concurrent_utils.bootstrap.run",
            side_effect=fake_bootstrap_run,
        ):
            MultiConcurrentRunner.run_concurrent(
                self.handler, self.addr, self.use_thread, self.socket, max_concurrency=4
            )

        self.assertEqual(success_counter.value, 6)
        self.assertEqual(fail_counter.value, 2)
        manager.shutdown()


if __name__ == "__main__":
    unittest.main()
