"""
Copyright 2025 Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import os
import sys
import socket
import multiprocessing

from . import bootstrap
from .lambda_runtime_client import LambdaElevatorRuntimeClient


class ElevatorRunner:
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
        client = LambdaElevatorRuntimeClient(api_addr, use_thread)
        bootstrap.run(handler, client)

    @classmethod
    def run_concurrent(
        cls,
        handler: str,
        api_addr: str,
        use_thread: bool,
        socket_path: str,
        max_concurrency: int,
    ):
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
