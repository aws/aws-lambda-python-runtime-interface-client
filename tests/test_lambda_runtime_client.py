"""
Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import http
import http.client
import unittest.mock
from unittest.mock import MagicMock, patch

from awslambdaric import __version__
from awslambdaric.lambda_runtime_client import (
    InvocationRequest,
    LambdaRuntimeClient,
    LambdaRuntimeClientError,
    _user_agent,
)


class TestInvocationRequest(unittest.TestCase):
    def test_constructor(self):
        invocation_request = InvocationRequest(
            invoke_id="Lambda-Runtime-Aws-Request-Id",
            x_amzn_trace_id="Lambda-Runtime-Trace-Id",
            invoked_function_arn="Lambda-Runtime-Invoked-Function-Arn",
            deadline_time_in_ms="Lambda-Runtime-Deadline-Ms",
            client_context="Lambda-Runtime-Client-Context",
            cognito_identity="Lambda-Runtime-Cognito-Identity",
            content_type="Content-Type",
            event_body="response_body",
        )

        equal_invocation_request = InvocationRequest(
            invoke_id="Lambda-Runtime-Aws-Request-Id",
            x_amzn_trace_id="Lambda-Runtime-Trace-Id",
            invoked_function_arn="Lambda-Runtime-Invoked-Function-Arn",
            deadline_time_in_ms="Lambda-Runtime-Deadline-Ms",
            client_context="Lambda-Runtime-Client-Context",
            cognito_identity="Lambda-Runtime-Cognito-Identity",
            content_type="Content-Type",
            event_body="response_body",
        )

        different_invocation_request = InvocationRequest(
            invoke_id="Lambda-Runtime-Aws-Request-Id",
            x_amzn_trace_id="Lambda-Runtime-Trace-Id",
            invoked_function_arn="Lambda-Runtime-Invoked-Function-Arn",
            deadline_time_in_ms="Lambda-Runtime-Deadline-Ms",
            client_context="Lambda-Runtime-Client-Context",
            cognito_identity="Lambda-Runtime-Cognito-Identity",
            content_type="Content-Type",
            event_body="another_response_body",
        )

        self.assertTrue(invocation_request == invocation_request)
        self.assertTrue(invocation_request == equal_invocation_request)
        self.assertFalse(invocation_request == different_invocation_request)


class TestLambdaRuntime(unittest.TestCase):
    @patch("awslambdaric.lambda_runtime_client.runtime_client")
    def test_wait_next_invocation(self, mock_runtime_client):
        response_body = b"{}"
        headears = {
            "Lambda-Runtime-Aws-Request-Id": "RID1234",
            "Lambda-Runtime-Trace-Id": "TID1234",
            "Lambda-Runtime-Invoked-Function-Arn": "FARN1234",
            "Lambda-Runtime-Deadline-Ms": 12,
            "Lambda-Runtime-Client-Context": "client_context",
            "Lambda-Runtime-Cognito-Identity": "cognito_identity",
            "Content-Type": "application/json",
        }
        mock_runtime_client.next.return_value = response_body, headears
        runtime_client = LambdaRuntimeClient("localhost:1234")

        use_thread_for_polling_next = True
        event_request = runtime_client.wait_next_invocation(use_thread_for_polling_next)

        self.assertIsNotNone(event_request)
        self.assertEqual(event_request.invoke_id, "RID1234")
        self.assertEqual(event_request.x_amzn_trace_id, "TID1234")
        self.assertEqual(event_request.invoked_function_arn, "FARN1234")
        self.assertEqual(event_request.deadline_time_in_ms, 12)
        self.assertEqual(event_request.client_context, "client_context")
        self.assertEqual(event_request.cognito_identity, "cognito_identity")
        self.assertEqual(event_request.content_type, "application/json")
        self.assertEqual(event_request.event_body, response_body)

        # Using ThreadPoolExecutor to polling next()
        use_thread_for_polling_next = False
        event_request = runtime_client.wait_next_invocation(use_thread_for_polling_next)

        self.assertIsNotNone(event_request)
        self.assertEqual(event_request.invoke_id, "RID1234")
        self.assertEqual(event_request.x_amzn_trace_id, "TID1234")
        self.assertEqual(event_request.invoked_function_arn, "FARN1234")
        self.assertEqual(event_request.deadline_time_in_ms, 12)
        self.assertEqual(event_request.client_context, "client_context")
        self.assertEqual(event_request.cognito_identity, "cognito_identity")
        self.assertEqual(event_request.content_type, "application/json")
        self.assertEqual(event_request.event_body, response_body)

    @patch("http.client.HTTPConnection", autospec=http.client.HTTPConnection)
    def test_post_init_error(self, MockHTTPConnection):
        mock_conn = MockHTTPConnection.return_value
        mock_response = MagicMock(autospec=http.client.HTTPResponse)
        mock_conn.getresponse.return_value = mock_response
        mock_response.read.return_value = b""
        mock_response.code = http.HTTPStatus.ACCEPTED

        runtime_client = LambdaRuntimeClient("localhost:1234")
        runtime_client.post_init_error("error_data")

        MockHTTPConnection.assert_called_with("localhost:1234")
        mock_conn.request.assert_called_once_with(
            "POST", "/2018-06-01/runtime/init/error", "error_data"
        )
        mock_response.read.assert_called_once()

    @patch("http.client.HTTPConnection", autospec=http.client.HTTPConnection)
    def test_post_init_error_non_accepted_status_code(self, MockHTTPConnection):
        mock_conn = MockHTTPConnection.return_value
        mock_response = MagicMock(autospec=http.client.HTTPResponse)
        mock_conn.getresponse.return_value = mock_response
        mock_response.read.return_value = b""
        mock_response.code = http.HTTPStatus.IM_USED

        runtime_client = LambdaRuntimeClient("localhost:1234")

        with self.assertRaises(LambdaRuntimeClientError) as cm:
            runtime_client.post_init_error("error_data")
        returned_exception = cm.exception

        self.assertEqual(returned_exception.endpoint, "/2018-06-01/runtime/init/error")
        self.assertEqual(returned_exception.response_code, http.HTTPStatus.IM_USED)

    @patch("awslambdaric.lambda_runtime_client.runtime_client")
    def test_post_invocation_result(self, mock_runtime_client):
        runtime_client = LambdaRuntimeClient("localhost:1234")
        response_data = "data"
        invoke_id = "1234"

        runtime_client.post_invocation_result(invoke_id, response_data)

        mock_runtime_client.post_invocation_result.assert_called_once_with(
            invoke_id, response_data.encode("utf-8"), "application/json"
        )

    @patch("awslambdaric.lambda_runtime_client.runtime_client")
    def test_post_invocation_result_binary_data(self, mock_runtime_client):
        runtime_client = LambdaRuntimeClient("localhost:1234")
        response_data = b"binary_data"
        invoke_id = "1234"
        content_type = "application/octet-stream"

        runtime_client.post_invocation_result(invoke_id, response_data, content_type)

        mock_runtime_client.post_invocation_result.assert_called_once_with(
            invoke_id, response_data, content_type
        )

    @patch("awslambdaric.lambda_runtime_client.runtime_client")
    def test_post_invocation_result_failure(self, mock_runtime_client):
        runtime_client = LambdaRuntimeClient("localhost:1234")
        response_data = "data"
        invoke_id = "1234"

        mock_runtime_client.post_invocation_result.side_effect = RuntimeError(
            "Failed to post invocation response"
        )

        with self.assertRaisesRegex(RuntimeError, "Failed to post invocation response"):
            runtime_client.post_invocation_result(invoke_id, response_data)

    @patch("awslambdaric.lambda_runtime_client.runtime_client")
    def test_post_invocation_error(self, mock_runtime_client):
        runtime_client = LambdaRuntimeClient("localhost:1234")
        error_data = "data"
        invoke_id = "1234"
        xray_fault = "xray_fault"

        runtime_client.post_invocation_error(invoke_id, error_data, xray_fault)

        mock_runtime_client.post_error.assert_called_once_with(
            invoke_id, error_data, xray_fault
        )

    @patch("awslambdaric.lambda_runtime_client.runtime_client")
    def test_post_invocation_error_with_large_xray_cause(self, mock_runtime_client):
        runtime_client = LambdaRuntimeClient("localhost:1234")
        error_data = "data"
        invoke_id = "1234"
        large_xray_fault = ("a" * int(1024 * 1024))[:-1]

        runtime_client.post_invocation_error(invoke_id, error_data, large_xray_fault)

        mock_runtime_client.post_error.assert_called_once_with(
            invoke_id, error_data, large_xray_fault
        )

    @patch("awslambdaric.lambda_runtime_client.runtime_client")
    def test_post_invocation_error_with_too_large_xray_cause(self, mock_runtime_client):
        runtime_client = LambdaRuntimeClient("localhost:1234")
        error_data = "data"
        invoke_id = "1234"
        too_large_xray_fault = "a" * int(1024 * 1024)

        runtime_client.post_invocation_error(
            invoke_id, error_data, too_large_xray_fault
        )

        mock_runtime_client.post_error.assert_called_once_with(
            invoke_id, error_data, ""
        )

    def test_connection_refused(self):
        with self.assertRaises(ConnectionRefusedError):
            runtime_client = LambdaRuntimeClient("127.0.0.1:1")
            runtime_client.post_init_error("error")

    def test_invalid_addr(self):
        with self.assertRaises(OSError):
            runtime_client = LambdaRuntimeClient("::::")
            runtime_client.post_init_error("error")

    def test_lambdaric_version(self):
        self.assertTrue(_user_agent().endswith(__version__))


class TestLambdaRuntimeClientError(unittest.TestCase):
    def test_constructor(self):
        expected_endpoint = ""
        expected_response_code = ""
        expected_response_body = ""

        lambda_runtime_client_error = LambdaRuntimeClientError(
            expected_endpoint, expected_response_code, expected_response_body
        )

        self.assertIsInstance(lambda_runtime_client_error, Exception)
        self.assertEqual(lambda_runtime_client_error.endpoint, expected_endpoint)


if __name__ == "__main__":
    unittest.main()
