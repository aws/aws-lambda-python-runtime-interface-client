"""
Copyright 2025 Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import logging
import os
import sys
import socket
import multiprocessing

from . import bootstrap
from .lambda_runtime_client import LambdaMultiConcurrentRuntimeClient
from .lambda_concurrency_hooks import get_pre_fork

WORKER_POOL_INITIALIZING_EVENT = "runtime_worker_pool_initializing"


class MultiConcurrentRunner:
    @staticmethod
    def _redirect_stream_to_fd(stream_fd: int, socket_path: str):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.connect(socket_path)
            os.dup2(s.fileno(), stream_fd)

    @classmethod
    def _redirect_output(cls, socket_path: str):
        for std_fd in (sys.stdout.fileno(), sys.stderr.fileno()):
            cls._redirect_stream_to_fd(std_fd, socket_path)

    @classmethod
    def run_single(
        cls, handler: str, api_addr: str, use_thread: bool, socket_path: str
    ):
        if socket_path:
            cls._redirect_output(socket_path)
        client = LambdaMultiConcurrentRuntimeClient(api_addr, use_thread)
        bootstrap.run(handler, client)

    @classmethod
    def _emit_worker_pool_event(cls, max_concurrency: int):
        """Emit the worker pool DEBUG event. The sink is owned by _before_fork."""
        logging.getLogger().debug(
            {
                "event": WORKER_POOL_INITIALIZING_EVENT,
                "workerCount": max_concurrency,
                "executionEnvironmentMaxConcurrency": max_concurrency,
            }
        )

    @classmethod
    def _init_handler(cls, handler: str, client, log_sink):
        """Import the handler, mirroring the guard in bootstrap.run: report an
        init error to RAPID and exit if it fails."""
        try:
            return bootstrap.get_handler(handler)
        except bootstrap.FaultException as e:
            error_result = bootstrap.make_error(e.msg, e.exception_type, e.trace)
        except Exception:
            error_result = bootstrap.build_fault_result(sys.exc_info(), None)

        bootstrap.log_error(error_result, log_sink)
        client.post_init_error(error_result)
        sys.exit(1)

    @classmethod
    def _run_pre_fork_hooks(cls, handler: str, api_addr: str, log_sink):
        """Run @register_pre_fork hooks once in the parent, in registration order.

        Importing the handler here is what runs its module-level
        @register_pre_fork decorators. Workers re-import it in their own
        process, so hooks are for external side effects (a subprocess, a warmed
        service, a file in /tmp) and share no in-memory state with workers.

        A failing hook is reported as an INIT error and exits: no worker should
        run against a precondition the hook failed to establish.
        """
        client = LambdaMultiConcurrentRuntimeClient(api_addr, False)
        cls._init_handler(handler, client, log_sink)

        try:
            for func, args, kwargs in get_pre_fork():
                func(*args, **kwargs)
        except Exception:
            error_result = bootstrap.build_fault_result(sys.exc_info(), None)
            bootstrap.log_error(error_result, log_sink)
            client.post_init_error(
                error_result, bootstrap.FaultException.PRE_FORK_ERROR
            )
            sys.exit(1)

    @classmethod
    def _before_fork(cls, handler: str, api_addr: str, max_concurrency: int):
        """Run the parent's work that must happen before forking workers.

        One sink covers both steps, released before returning: forked workers
        inherit the parent's handler (fork is the POSIX default before 3.14)
        and would log every line twice. Not released on the failure path, where
        the process is exiting anyway.

        No redirection here: RAPID wires the parent's stdout/stderr to the log
        egress at spawn; the FD provider socket is for workers (run_single).
        """
        log_sink = bootstrap.init_logging()

        cls._run_pre_fork_hooks(handler, api_addr, log_sink)

        # After the hooks, so it is never emitted for a pool that fails to start.
        cls._emit_worker_pool_event(max_concurrency)

        logging.getLogger().handlers.clear()
        log_sink.__exit__(None, None, None)

    @classmethod
    def run_concurrent(
        cls,
        handler: str,
        api_addr: str,
        use_thread: bool,
        socket_path: str,
        max_concurrency: int,
    ):
        cls._before_fork(handler, api_addr, max_concurrency)

        processes = []
        for _ in range(max_concurrency):
            p = multiprocessing.Process(
                target=cls.run_single,
                args=(handler, api_addr, use_thread, socket_path),
            )
            p.start()
            processes.append(p)
        for p in processes:
            p.join()
