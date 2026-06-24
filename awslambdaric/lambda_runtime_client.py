"""
Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import sys
from awslambdaric import __version__
from .lambda_runtime_exception import FaultException
from .lambda_runtime_marshaller import to_json
import logging
import time

ERROR_TYPE_HEADER = "Lambda-Runtime-Function-Error-Type"
# Retry config constants
DEFAULT_RETRY_MAX_ATTEMPTS = 5
DEFAULT_RETRY_INITIAL_DELAY = 0.1  # seconds
DEFAULT_RETRY_BACKOFF_FACTOR = 2.0


def _user_agent():
    py_version = (
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
    pkg_version = __version__
    return f"aws-lambda-python/{py_version}-{pkg_version}"


try:
    import runtime_client

    runtime_client.initialize_client(_user_agent())
except ImportError:
    runtime_client = None

from .lambda_runtime_marshaller import LambdaMarshaller


class InvocationRequest(object):
    def __init__(self, **kwds):
        self.__dict__.update(kwds)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__


class LambdaRuntimeClientError(Exception):
    def __init__(self, endpoint, response_code, response_body):
        self.endpoint = endpoint
        self.response_code = response_code
        self.response_body = response_body
        super().__init__(
            f"Request to Lambda Runtime '{endpoint}' endpoint failed. Reason: '{response_code}'. Response body: '{response_body}'"
        )


class BaseLambdaRuntimeClient(object):
    marshaller = LambdaMarshaller()
    """marshaller is a class attribute that determines the unmarshalling and marshalling logic of a function's event
    and response. It allows for function authors to override the the default implementation, LambdaMarshaller which
    unmarshals and marshals JSON, to an instance of a class that implements the same interface."""

    def __init__(
        self,
        lambda_runtime_address,
        use_thread_for_polling_next=False,
    ):
        self.lambda_runtime_address = lambda_runtime_address
        self.use_thread_for_polling_next = use_thread_for_polling_next
        if self.use_thread_for_polling_next:
            # Conditionally import only for the case when TPE is used in this class.
            from concurrent.futures import ThreadPoolExecutor

            # Not defining symbol as global to avoid relying on TPE being imported unconditionally.
            self.ThreadPoolExecutor = ThreadPoolExecutor

    def call_rapid(
        self, http_method, endpoint, expected_http_code, payload=None, headers=None
    ):
        # These imports are heavy-weight. They implicitly trigger `import ssl, hashlib`.
        # Importing them lazily to speed up critical path of a common case.
        import http.client

        runtime_connection = http.client.HTTPConnection(self.lambda_runtime_address)
        runtime_connection.connect()
        if http_method == "GET":
            runtime_connection.request(http_method, endpoint)
        else:
            runtime_connection.request(
                http_method, endpoint, to_json(payload), headers=headers
            )

        response = runtime_connection.getresponse()
        response_body = response.read()
        if response.code != expected_http_code:
            raise LambdaRuntimeClientError(endpoint, response.code, response_body)

    def post_init_error(self, error_response_data, error_type_override=None):
        import http

        endpoint = "/2018-06-01/runtime/init/error"
        headers = {
            ERROR_TYPE_HEADER: (
                error_type_override
                if error_type_override
                else error_response_data["errorType"]
            )
        }
        try:
            self.call_rapid(
                "POST", endpoint, http.HTTPStatus.ACCEPTED, error_response_data, headers
            )
        except Exception as e:
            self.handle_init_error(e)

    def handle_init_error(self, exc):
        """Override in subclasses to customize init error handling."""
        raise NotImplementedError

    def restore_next(self):
        import http

        endpoint = "/2018-06-01/runtime/restore/next"
        self.call_rapid("GET", endpoint, http.HTTPStatus.OK)

    def report_restore_error(self, restore_error_data):
        import http

        endpoint = "/2018-06-01/runtime/restore/error"
        headers = {ERROR_TYPE_HEADER: FaultException.AFTER_RESTORE_ERROR}
        self.call_rapid(
            "POST", endpoint, http.HTTPStatus.ACCEPTED, restore_error_data, headers
        )

    def handle_exception(self, exc, func_to_retry=None, use_backoff=False):
        """Override in subclasses to customize error handling."""
        raise NotImplementedError

    def _get_next(self):
        try:
            return runtime_client.next()
        except Exception as e:
            return self.handle_exception(e, runtime_client.next, True)

    def wait_next_invocation(self):
        # Calling runtime_client.next() from a separate thread unblocks the main thread,
        # which can then process signals.
        if self.use_thread_for_polling_next:
            try:
                # TPE class is supposed to be registered at construction time and be ready to use.
                with self.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(self._get_next)
                response_body, headers = future.result()
            except Exception as e:
                raise FaultException(
                    FaultException.LAMBDA_RUNTIME_CLIENT_ERROR,
                    "LAMBDA_RUNTIME Failed to get next invocation: {}".format(str(e)),
                    None,
                )
        else:
            response_body, headers = runtime_client.next()
        return InvocationRequest(
            invoke_id=headers.get("Lambda-Runtime-Aws-Request-Id"),
            x_amzn_trace_id=headers.get("Lambda-Runtime-Trace-Id"),
            invoked_function_arn=headers.get("Lambda-Runtime-Invoked-Function-Arn"),
            deadline_time_in_ms=headers.get("Lambda-Runtime-Deadline-Ms"),
            client_context=headers.get("Lambda-Runtime-Client-Context"),
            cognito_identity=headers.get("Lambda-Runtime-Cognito-Identity"),
            tenant_id=headers.get("Lambda-Runtime-Aws-Tenant-Id"),
            content_type=headers.get("Content-Type"),
            event_body=response_body,
        )

    def post_invocation_result(
        self, invoke_id, result_data, content_type="application/json"
    ):
        try:
            runtime_client.post_invocation_result(
                invoke_id,
                (
                    result_data
                    if isinstance(result_data, bytes)
                    else result_data.encode("utf-8")
                ),
                content_type,
            )
        except Exception as e:
            self.handle_exception(e)

    def post_invocation_error(self, invoke_id, error_response_data, xray_fault):
        try:
            max_header_size = 1024 * 1024
            xray_fault = (
                xray_fault if len(xray_fault.encode()) < max_header_size else ""
            )
            runtime_client.post_error(invoke_id, error_response_data, xray_fault)
        except Exception as e:
            self.handle_exception(e)


class LambdaRuntimeClient(BaseLambdaRuntimeClient):
    def handle_exception(self, exc, func_to_retry=None, use_backoff=False):
        raise exc

    def handle_init_error(self, exc):
        raise exc


class LambdaMultiConcurrentRuntimeClient(BaseLambdaRuntimeClient):
    def _get_next_with_backoff(self, e, func_to_retry):
        logging.warning(f"Initial runtime_client.next() failed: {e}")
        delay = DEFAULT_RETRY_INITIAL_DELAY
        latest_exception = None
        for attempt in range(1, DEFAULT_RETRY_MAX_ATTEMPTS):
            try:
                logging.info(
                    f"Retrying runtime_client.next() [attempt {attempt + 1}]..."
                )
                time.sleep(delay)
                return func_to_retry()
            except Exception as e:
                logging.warning(f"Attempt {attempt + 1} failed: {e}")
                delay *= DEFAULT_RETRY_BACKOFF_FACTOR
                latest_exception = e

        raise latest_exception

    # In multi-concurrent mode we don't want to raise unhandled exception and crash the worker on non-2xx responses from RAPID
    def handle_exception(self, exc, func_to_retry=None, use_backoff=False):
        if use_backoff:
            return self._get_next_with_backoff(exc, func_to_retry)
        # We retry if getting next invoke failed, but if posting response to RAPID failed we just log it and continue
        logging.warning(f"{exc}: This won't kill the Runtime loop")

    def handle_init_error(self, exc):
        if isinstance(exc, LambdaRuntimeClientError) and exc.response_code == 403:
            # Suppress 403 errors from RAPID during init - indicates another runtime worker has already posted init error
            return
        raise exc
