"""
Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import http
import http.client
import sys

try:
    from importlib import metadata
except ImportError:
    # Running on pre-3.8 Python; use importlib-metadata package
    import importlib_metadata as metadata


def _user_agent():
    py_version = (
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
    try:
        pkg_version = metadata.version("awslambdaric")
    except:
        pkg_version = "unknown"
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


class LambdaRuntimeClient(object):
    marshaller = LambdaMarshaller()
    """marshaller is a class attribute that determines the unmarshalling and marshalling logic of a function's event
    and response. It allows for function authors to override the the default implementation, LambdaMarshaller which
    unmarshals and marshals JSON, to an instance of a class that implements the same interface."""

    def __init__(self, lambda_runtime_address):
        self.lambda_runtime_address = lambda_runtime_address

    def post_init_error(self, error_response_data):
        runtime_connection = http.client.HTTPConnection(self.lambda_runtime_address)
        runtime_connection.connect()
        endpoint = "/2018-06-01/runtime/init/error"
        runtime_connection.request("POST", endpoint, error_response_data)
        response = runtime_connection.getresponse()
        response_body = response.read()

        if response.code != http.HTTPStatus.ACCEPTED:
            raise LambdaRuntimeClientError(endpoint, response.code, response_body)

    def wait_next_invocation(self):
        response_body, headers = runtime_client.next()
        return InvocationRequest(
            invoke_id=headers.get("Lambda-Runtime-Aws-Request-Id"),
            x_amzn_trace_id=headers.get("Lambda-Runtime-Trace-Id"),
            invoked_function_arn=headers.get("Lambda-Runtime-Invoked-Function-Arn"),
            deadline_time_in_ms=headers.get("Lambda-Runtime-Deadline-Ms"),
            client_context=headers.get("Lambda-Runtime-Client-Context"),
            cognito_identity=headers.get("Lambda-Runtime-Cognito-Identity"),
            content_type=headers.get("Content-Type"),
            event_body=response_body,
        )

    def post_invocation_result(
        self, invoke_id, result_data, content_type="application/json"
    ):
        runtime_client.post_invocation_result(
            invoke_id,
            result_data
            if isinstance(result_data, bytes)
            else result_data.encode("utf-8"),
            content_type,
        )

    def post_invocation_error(self, invoke_id, error_response_data, xray_fault):
        max_header_size = 1024 * 1024  # 1MiB
        xray_fault = xray_fault if len(xray_fault.encode()) < max_header_size else ""
        runtime_client.post_error(invoke_id, error_response_data, xray_fault)
