"""
Copyright 2025 Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import unittest
from unittest.mock import patch, MagicMock

from awslambdaric import lambda_concurrency_hooks as hooks
from awslambdaric.lambda_concurrency_hooks import register_pre_fork
from awslambdaric.lambda_multi_concurrent_utils import MultiConcurrentRunner
from awslambdaric.lambda_runtime_exception import FaultException


class PreForkRegistryTest(unittest.TestCase):
    def setUp(self):
        hooks._pre_fork_registry.clear()

    def tearDown(self):
        hooks._pre_fork_registry.clear()

    def test_register_returns_the_function_unchanged(self):
        def my_hook():
            pass

        # The decorator must hand the function back, or it disappears from the
        # customer's module.
        self.assertIs(register_pre_fork(my_hook), my_hook)

    def test_register_stores_func_with_empty_args_and_kwargs(self):
        def my_hook():
            pass

        register_pre_fork(my_hook)
        # The runner unpacks this 3-tuple shape.
        self.assertEqual(hooks.get_pre_fork(), [(my_hook, (), {})])


class RunPreForkHooksTest(unittest.TestCase):
    def setUp(self):
        hooks._pre_fork_registry.clear()
        self.log_sink = MagicMock()

    def tearDown(self):
        hooks._pre_fork_registry.clear()

    @patch.object(MultiConcurrentRunner, "_init_handler")
    @patch(
        "awslambdaric.lambda_multi_concurrent_utils.LambdaMultiConcurrentRuntimeClient"
    )
    def test_hooks_run_once_in_registration_order(
        self, mock_client_cls, mock_init_handler
    ):
        order = []

        @register_pre_fork
        def first():
            order.append(1)

        @register_pre_fork
        def second():
            order.append(2)

        MultiConcurrentRunner._run_pre_fork_hooks("app.handler", "addr", self.log_sink)

        self.assertEqual(order, [1, 2])

    @patch.object(MultiConcurrentRunner, "_init_handler")
    @patch(
        "awslambdaric.lambda_multi_concurrent_utils.LambdaMultiConcurrentRuntimeClient"
    )
    def test_handler_is_imported_before_hooks_run(
        self, mock_client_cls, mock_init_handler
    ):
        order = []
        mock_init_handler.side_effect = lambda *a, **k: order.append("import")

        @register_pre_fork
        def hook():
            order.append("hook")

        MultiConcurrentRunner._run_pre_fork_hooks("app.handler", "addr", self.log_sink)

        # Importing the handler is what registers the hooks, so it must come first.
        self.assertEqual(order, ["import", "hook"])

    @patch.object(MultiConcurrentRunner, "_init_handler")
    @patch(
        "awslambdaric.lambda_multi_concurrent_utils.LambdaMultiConcurrentRuntimeClient"
    )
    @patch("awslambdaric.lambda_multi_concurrent_utils.bootstrap")
    def test_failing_hook_is_reported_as_init_error_and_exits(
        self, mock_bootstrap, mock_client_cls, mock_init_handler
    ):
        mock_bootstrap.FaultException = FaultException
        mock_bootstrap.build_fault_result.return_value = {"errorType": "RuntimeError"}

        @register_pre_fork
        def bad_hook():
            raise RuntimeError("boom")

        with self.assertRaises(SystemExit) as raised:
            MultiConcurrentRunner._run_pre_fork_hooks(
                "app.handler", "addr", self.log_sink
            )

        self.assertEqual(raised.exception.code, 1)
        # Reported like a failed handler import, so the customer sees a real
        # INIT error carrying the hook's traceback rather than a bare crash.
        mock_bootstrap.log_error.assert_called_once_with(
            {"errorType": "RuntimeError"}, self.log_sink
        )
        # The hook phase is named explicitly: the bare Python exception type
        # would be normalized to Runtime.Unknown by the platform.
        mock_client_cls.return_value.post_init_error.assert_called_once_with(
            {"errorType": "RuntimeError"}, "Runtime.PreForkError"
        )

    def test_pre_fork_error_type_survives_platform_normalization(self):
        # Lambda normalizes anything outside <Category.Reason> to
        # Runtime.Unknown, which would misreport a well-formed hook failure.
        self.assertRegex(
            FaultException.PRE_FORK_ERROR, r"^(Runtime|Function)\.[A-Z][a-zA-Z]+$"
        )

    @patch.object(MultiConcurrentRunner, "_init_handler")
    @patch(
        "awslambdaric.lambda_multi_concurrent_utils.LambdaMultiConcurrentRuntimeClient"
    )
    @patch("awslambdaric.lambda_multi_concurrent_utils.bootstrap")
    def test_later_hooks_do_not_run_after_one_fails(
        self, mock_bootstrap, mock_client_cls, mock_init_handler
    ):
        mock_bootstrap.FaultException = FaultException
        ran = []

        @register_pre_fork
        def bad_hook():
            raise RuntimeError("boom")

        @register_pre_fork
        def later_hook():
            ran.append("later")

        with self.assertRaises(SystemExit):
            MultiConcurrentRunner._run_pre_fork_hooks(
                "app.handler", "addr", self.log_sink
            )

        self.assertEqual(ran, [])


class BeforeForkTest(unittest.TestCase):
    """_before_fork owns the parent's log sink for the pre-fork work."""

    @patch.object(MultiConcurrentRunner, "_emit_worker_pool_event")
    @patch.object(MultiConcurrentRunner, "_run_pre_fork_hooks")
    @patch("awslambdaric.lambda_multi_concurrent_utils.logging")
    @patch("awslambdaric.lambda_multi_concurrent_utils.bootstrap")
    def test_sets_up_sink_once_and_releases_it_before_returning(
        self, mock_bootstrap, mock_logging, mock_run_hooks, mock_emit
    ):
        log_sink = mock_bootstrap.init_logging.return_value

        MultiConcurrentRunner._before_fork("app.handler", "addr", 3)

        mock_bootstrap.init_logging.assert_called_once_with()
        # Both steps log through that one sink.
        mock_run_hooks.assert_called_once_with("app.handler", "addr", log_sink)
        mock_emit.assert_called_once_with(3)
        # Released before returning, so no forked worker inherits the handler.
        mock_logging.getLogger.return_value.handlers.clear.assert_called_once_with()
        log_sink.__exit__.assert_called_once_with(None, None, None)

    @patch("awslambdaric.lambda_multi_concurrent_utils.logging")
    @patch("awslambdaric.lambda_multi_concurrent_utils.bootstrap")
    def test_hooks_run_before_the_pool_event(self, mock_bootstrap, mock_logging):
        order_tracker = MagicMock()

        with patch.object(
            MultiConcurrentRunner, "_run_pre_fork_hooks"
        ) as mock_run_hooks, patch.object(
            MultiConcurrentRunner, "_emit_worker_pool_event"
        ) as mock_emit:
            order_tracker.attach_mock(mock_run_hooks, "run_hooks")
            order_tracker.attach_mock(mock_emit, "emit")
            MultiConcurrentRunner._before_fork("app.handler", "addr", 2)

        # The event is emitted after the hooks, so it is never emitted for a
        # pool that then fails to start.
        self.assertEqual(
            [c[0] for c in order_tracker.mock_calls[:2]], ["run_hooks", "emit"]
        )


class RunConcurrentHookTest(unittest.TestCase):
    """Drive the public entry point with a really registered hook."""

    def setUp(self):
        hooks._pre_fork_registry.clear()

    def tearDown(self):
        hooks._pre_fork_registry.clear()

    @patch.object(MultiConcurrentRunner, "_init_handler")
    @patch(
        "awslambdaric.lambda_multi_concurrent_utils.LambdaMultiConcurrentRuntimeClient"
    )
    @patch.object(MultiConcurrentRunner, "_emit_worker_pool_event")
    @patch("awslambdaric.lambda_multi_concurrent_utils.logging")
    @patch("awslambdaric.lambda_multi_concurrent_utils.bootstrap")
    @patch("multiprocessing.Process")
    def test_registered_hook_runs_exactly_once_through_run_concurrent(
        self,
        mock_process,
        mock_bootstrap,
        mock_logging,
        mock_emit,
        mock_client_cls,
        mock_init_handler,
    ):
        mock_process.return_value = MagicMock()
        hook_fn = MagicMock()
        register_pre_fork(hook_fn)

        MultiConcurrentRunner.run_concurrent(
            "app.handler", "addr", False, "/sock", max_concurrency=4
        )

        # One call in the parent, not one per worker.
        hook_fn.assert_called_once_with()
        self.assertEqual(mock_process.call_count, 4)

    @patch.object(MultiConcurrentRunner, "_init_handler")
    @patch(
        "awslambdaric.lambda_multi_concurrent_utils.LambdaMultiConcurrentRuntimeClient"
    )
    @patch("awslambdaric.lambda_multi_concurrent_utils.logging")
    @patch("awslambdaric.lambda_multi_concurrent_utils.bootstrap")
    @patch("multiprocessing.Process")
    def test_failing_hook_starts_no_workers(
        self,
        mock_process,
        mock_bootstrap,
        mock_logging,
        mock_client_cls,
        mock_init_handler,
    ):
        @register_pre_fork
        def bad_hook():
            raise RuntimeError("s3 download failed")

        with self.assertRaises(SystemExit):
            MultiConcurrentRunner.run_concurrent(
                "app.handler", "addr", False, "/sock", max_concurrency=4
            )

        # Workers must never run against a precondition the hook failed to
        # establish - one clear init failure beats N per-invocation failures.
        mock_process.assert_not_called()


class InitHandlerTest(unittest.TestCase):
    @patch("awslambdaric.lambda_multi_concurrent_utils.bootstrap")
    def test_returns_handler_on_success(self, mock_bootstrap):
        sentinel = object()
        mock_bootstrap.get_handler.return_value = sentinel
        client = MagicMock()

        result = MultiConcurrentRunner._init_handler("app.handler", client, MagicMock())

        self.assertIs(result, sentinel)
        client.post_init_error.assert_not_called()

    @patch("awslambdaric.lambda_multi_concurrent_utils.bootstrap")
    def test_reports_fault_exception_and_exits(self, mock_bootstrap):
        from awslambdaric.lambda_runtime_exception import FaultException

        mock_bootstrap.FaultException = FaultException
        mock_bootstrap.get_handler.side_effect = FaultException(
            FaultException.IMPORT_MODULE_ERROR, "no module", None
        )
        mock_bootstrap.make_error.return_value = {"errorType": "x"}
        client = MagicMock()
        log_sink = MagicMock()

        with self.assertRaises(SystemExit):
            MultiConcurrentRunner._init_handler("app.handler", client, log_sink)

        mock_bootstrap.log_error.assert_called_once_with({"errorType": "x"}, log_sink)
        client.post_init_error.assert_called_once_with({"errorType": "x"})

    @patch("awslambdaric.lambda_multi_concurrent_utils.bootstrap")
    def test_reports_unexpected_exception_and_exits(self, mock_bootstrap):
        from awslambdaric.lambda_runtime_exception import FaultException

        mock_bootstrap.FaultException = FaultException
        mock_bootstrap.get_handler.side_effect = ValueError("unexpected")
        mock_bootstrap.build_fault_result.return_value = {"errorType": "ValueError"}
        client = MagicMock()

        with self.assertRaises(SystemExit):
            MultiConcurrentRunner._init_handler("app.handler", client, MagicMock())

        mock_bootstrap.build_fault_result.assert_called_once()
        client.post_init_error.assert_called_once()


if __name__ == "__main__":
    unittest.main()
