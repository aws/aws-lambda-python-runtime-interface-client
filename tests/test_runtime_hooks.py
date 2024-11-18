# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import unittest
from unittest.mock import patch, call
from awslambdaric import lambda_runtime_hooks_runner
import snapshot_restore_py


def fun_test1():
    print("In function ONE")


def fun_test2():
    print("In function TWO")


def fun_with_args_kwargs(x, y, **kwargs):
    print("Here are the args:", x, y)
    print("Here are the keyword args:", kwargs)


class TestRuntimeHooks(unittest.TestCase):
    def tearDown(self):
        # We are accessing private filed for cleaning up
        snapshot_restore_py._before_snapshot_registry = []
        snapshot_restore_py._after_restore_registry = []

    @patch("builtins.print")
    def test_before_snapshot_execution_order(self, mock_print):
        snapshot_restore_py.register_before_snapshot(
            fun_with_args_kwargs, 5, 7, arg1="Lambda", arg2="SnapStart"
        )
        snapshot_restore_py.register_before_snapshot(fun_test2)
        snapshot_restore_py.register_before_snapshot(fun_test1)

        lambda_runtime_hooks_runner.run_before_snapshot()

        calls = []
        calls.append(call("In function ONE"))
        calls.append(call("In function TWO"))
        calls.append(call("Here are the args:", 5, 7))
        calls.append(
            call("Here are the keyword args:", {"arg1": "Lambda", "arg2": "SnapStart"})
        )
        self.assertEqual(calls, mock_print.mock_calls)

    @patch("builtins.print")
    def test_after_restore_execution_order(self, mock_print):
        snapshot_restore_py.register_after_restore(
            fun_with_args_kwargs, 11, 13, arg1="Lambda", arg2="SnapStart"
        )
        snapshot_restore_py.register_after_restore(fun_test2)
        snapshot_restore_py.register_after_restore(fun_test1)

        lambda_runtime_hooks_runner.run_after_restore()

        calls = []
        calls.append(call("Here are the args:", 11, 13))
        calls.append(
            call("Here are the keyword args:", {"arg1": "Lambda", "arg2": "SnapStart"})
        )
        calls.append(call("In function TWO"))
        calls.append(call("In function ONE"))
        self.assertEqual(calls, mock_print.mock_calls)
