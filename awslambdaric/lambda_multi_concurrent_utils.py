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
    def _emit_worker_pool_event(cls, socket_path: str, max_concurrency: int):
        """Emit worker pool DEBUG event once from the parent before forking."""
        if socket_path:
            cls._redirect_output(socket_path)
        log_sink = bootstrap.init_logging()
        logging.getLogger().debug(
            {
                "event": WORKER_POOL_INITIALIZING_EVENT,
                "workerCount": max_concurrency,
                "executionEnvironmentMaxConcurrency": max_concurrency,
            }
        )
        logging.getLogger().handlers.clear()
        # Close the sink deterministically now that its handler is gone
        # (no-op for StandardLogSink; releases the fd for framed sinks).
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
        cls._emit_worker_pool_event(socket_path, max_concurrency)

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
