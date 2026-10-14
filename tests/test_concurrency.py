"""
Copyright 2025 Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import multiprocessing
import os
import sys
import threading
import types
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
        multiprocessing.set_start_method("fork", force=True)
        success_counter = multiprocessing.Value("i", 0)
        fail_counter = multiprocessing.Value("i", 0)
        process_index = multiprocessing.Value("i", 0)

        def fake_bootstrap_run(handler, lambda_runtime_client):
            with process_index.get_lock():
                idx = process_index.value
                process_index.value += 1
            if idx % 2 == 0:
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
            "awslambdaric.lambda_multi_concurrent_utils.MultiConcurrentRunner._emit_worker_pool_event"
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

    def test_workers_are_forked_children_regardless_of_default_start_method(self):
        """The runner must not inherit the interpreter default start method.

        Force the default to "forkserver" (what 3.14+ picks) and check that
        workers are still direct children of this process, that the parent
        forked while single-threaded, and that a module imported in the parent
        before the fork is already present in each worker (fork semantics, not
        a fresh interpreter).
        """
        previous = multiprocessing.get_start_method(allow_none=True)
        multiprocessing.set_start_method("forkserver", force=True)
        try:
            parent_pid = os.getpid()
            parent_threads_at_fork = threading.active_count()
            marker = "_fork_pin_marker_module"
            sys.modules[marker] = types.ModuleType(marker)
            n = 3
            ppids = multiprocessing.Array("i", n)
            inherited = multiprocessing.Array("i", n)
            slot = multiprocessing.Value("i", 0)

            def fake_bootstrap_run(handler, lambda_runtime_client):
                with slot.get_lock():
                    i = slot.value
                    slot.value += 1
                ppids[i] = os.getppid()
                inherited[i] = int(marker in sys.modules)

            with patch(
                "awslambdaric.lambda_multi_concurrent_utils.MultiConcurrentRunner._redirect_output"
            ), patch(
                "awslambdaric.lambda_multi_concurrent_utils.MultiConcurrentRunner._emit_worker_pool_event"
            ), patch(
                "awslambdaric.lambda_multi_concurrent_utils.bootstrap.run",
                side_effect=fake_bootstrap_run,
            ):
                MultiConcurrentRunner.run_concurrent(
                    self.handler,
                    self.addr,
                    self.use_thread,
                    self.socket,
                    max_concurrency=n,
                )

            self.assertEqual(multiprocessing.get_start_method(), "forkserver")
            self.assertEqual(parent_threads_at_fork, 1)
            self.assertEqual(list(ppids), [parent_pid] * n)
            self.assertEqual(list(inherited), [1] * n)
        finally:
            sys.modules.pop(marker, None)
            multiprocessing.set_start_method(previous, force=True)


if __name__ == "__main__":
    unittest.main()
