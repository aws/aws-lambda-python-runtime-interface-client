"""
Copyright 2025 Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import threading
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
        success_counter = 0
        fail_counter = 0
        process_index = 0
        lock = threading.Lock()

        def fake_bootstrap_run(handler, lambda_runtime_client):
            nonlocal success_counter, fail_counter, process_index
            with lock:
                idx = process_index
                process_index += 1
            if idx % 2 == 0:
                for _ in range(3):
                    with lock:
                        success_counter += 1
            else:
                with lock:
                    fail_counter += 1
                raise RuntimeError("Simulated failure")

        with patch(
            "awslambdaric.lambda_multi_concurrent_utils.MultiConcurrentRunner._redirect_output"
        ), patch(
            "awslambdaric.lambda_multi_concurrent_utils.bootstrap.run",
            side_effect=fake_bootstrap_run,
        ), patch(
            "awslambdaric.lambda_multi_concurrent_utils.multiprocessing.Process",
            threading.Thread,
        ):
            # spawn 4 multi-concurrent processes
            MultiConcurrentRunner.run_concurrent(
                self.handler, self.addr, self.use_thread, self.socket, max_concurrency=4
            )

        self.assertEqual(success_counter, 6)
        self.assertEqual(fail_counter, 2)


if __name__ == "__main__":
    unittest.main()
