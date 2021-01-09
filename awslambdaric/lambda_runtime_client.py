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


def user_agent():
    py_version = (
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
    try:
        pkg_version = metadata.version("awslambdaric")
    except:
        pkg_version = "unknown"
    return f"aws-lambda-python/{py_version}-{pkg_version}"


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
        runtime_connection.request(
            "POST",
            endpoint,
            body=error_response_data,
            headers={"User-Agent": user_agent()},
        )
        response = runtime_connection.getresponse()
        response_body = response.read()

        if response.code != http.HTTPStatus.ACCEPTED:
            raise LambdaRuntimeClientError(endpoint, response.code, response_body)

    def wait_next_invocation(self):
        runtime_connection = http.client.HTTPConnection(self.lambda_runtime_address)
        runtime_connection.connect()
        endpoint = "/2018-06-01/runtime/invocation/next"
        runtime_connection.request(
            "GET", endpoint, headers={"User-Agent": user_agent()}
        )
        response = runtime_connection.getresponse()
        response_body = response.read()

        if response.code != http.HTTPStatus.OK:
            raise LambdaRuntimeClientError(endpoint, response.code, response_body)

        return InvocationRequest(
            invoke_id=response.getheader("Lambda-Runtime-Aws-Request-Id"),
            x_amzn_trace_id=response.getheader("Lambda-Runtime-Trace-Id"),
            invoked_function_arn=response.getheader(
                "Lambda-Runtime-Invoked-Function-Arn"
            ),
            deadline_time_in_ms=response.getheader("Lambda-Runtime-Deadline-Ms"),
            client_context=response.getheader("Lambda-Runtime-Client-Context"),
            cognito_identity=response.getheader("Lambda-Runtime-Cognito-Identity"),
            content_type=response.getheader("Content-Type"),
            event_body=response_body,
        )

    def post_invocation_result(
        self, invoke_id, result_data, content_type="application/json"
    ):
        runtime_connection = http.client.HTTPConnection(self.lambda_runtime_address)
        runtime_connection.connect()
        endpoint = "/2018-06-01/runtime/invocation/#{invoke_id}/response"
        headers = {"Content-Type": content_type, "User-Agent": user_agent()}
        runtime_connection.request(
            "POST",
            endpoint,
            result_data
            if isinstance(result_data, bytes)
            else result_data.encode("utf-8"),
            headers,
        )
        response = runtime_connection.getresponse()
        response_body = response.read()

        if response.code != http.HTTPStatus.OK:
            raise LambdaRuntimeClientError(endpoint, response.code, response_body)

    def post_invocation_error(self, invoke_id, error_response_data, xray_fault):
        max_header_size = 1024 * 1024  # 1MiB
        xray_fault = xray_fault if len(xray_fault.encode()) < max_header_size else ""

        runtime_connection = http.client.HTTPConnection(self.lambda_runtime_address)
        runtime_connection.connect()
        endpoint = "/2018-06-01/runtime/invocation/#{invoke_id}/error"
        headers = {
            "User-Agent": user_agent(),
            "Content-Type": "application/json",
            "Lambda-Runtime-Function-XRay-Error-Cause": xray_fault,
        }
        runtime_connection.request("POST", endpoint, error_response_data, headers)
        response = runtime_connection.getresponse()
        response_body = response.read()

        if response.code != http.HTTPStatus.OK:
            raise LambdaRuntimeClientError(endpoint, response.code, response_body)
