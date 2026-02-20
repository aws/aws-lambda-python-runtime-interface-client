"""
Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import os


class LambdaConfigProvider:
    SUPPORTED_THREADPOLLING_ENVS = {
        "AWS_Lambda_python3.12",
        "AWS_Lambda_python3.13",
        "AWS_Lambda_python3.14",
    }
    SOCKET_PATH_ENV = "_LAMBDA_TELEMETRY_LOG_FD_PROVIDER_SOCKET"
    AWS_LAMBDA_RUNTIME_API = "AWS_LAMBDA_RUNTIME_API"
    AWS_LAMBDA_MAX_CONCURRENCY = "AWS_LAMBDA_MAX_CONCURRENCY"
    AWS_EXECUTION_ENV = "AWS_EXECUTION_ENV"

    def __init__(self, args, environ=None):
        self._environ = environ if environ is not None else os.environ
        self._handler = self._parse_handler(args)
        self._api_address = self._parse_api_address()
        self._max_concurrency = self._parse_concurrency()
        self._use_thread_polling = self._parse_thread_polling()
        self._lmi_socket_path = self._parse_lmi_socket_path()

    def _parse_handler(self, args):
        try:
            return args[1]
        except IndexError:
            raise ValueError("Handler not set")

    def _parse_api_address(self):
        return self._environ[self.AWS_LAMBDA_RUNTIME_API]

    def _parse_concurrency(self):
        return self._environ.get(self.AWS_LAMBDA_MAX_CONCURRENCY)

    def _parse_thread_polling(self):
        return (
            self._environ.get(self.AWS_EXECUTION_ENV)
            in self.SUPPORTED_THREADPOLLING_ENVS
        )

    def _parse_lmi_socket_path(self):
        return self._environ.get(self.SOCKET_PATH_ENV)

    @property
    def handler(self):
        return self._handler

    @property
    def api_address(self):
        return self._api_address

    @property
    def max_concurrency(self):
        return self._max_concurrency

    @property
    def use_thread_polling(self):
        return self._use_thread_polling

    @property
    def is_multi_concurrent(self):
        return self._max_concurrency is not None

    @property
    def lmi_socket_path(self):
        return self._lmi_socket_path
