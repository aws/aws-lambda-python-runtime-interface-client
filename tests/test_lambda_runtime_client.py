"""
Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import http
import http.client
import unittest.mock
import threading
from unittest.mock import MagicMock, patch

from awslambdaric import __version__
from awslambdaric.lambda_runtime_client import (
    InvocationRequest,
    LambdaRuntimeClient,
    LambdaMultiConcurrentRuntimeClient,
    LambdaRuntimeClientError,
    _user_agent,
)
from awslambdaric.lambda_runtime_marshaller import to_json


class TestInvocationRequest(unittest.TestCase):
    def test_constructor(self):
        invocation_request = InvocationRequest(
            invoke_id="Lambda-Runtime-Aws-Request-Id",
            x_amzn_trace_id="Lambda-Runtime-Trace-Id",
            invoked_function_arn="Lambda-Runtime-Invoked-Function-Arn",
            deadline_time_in_ms="Lambda-Runtime-Deadline-Ms",
            client_context="Lambda-Runtime-Client-Context",
            cognito_identity="Lambda-Runtime-Cognito-Identity",
            tenant_id="Lambda-Runtime-Aws-Tenant-Id",
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
            tenant_id="Lambda-Runtime-Aws-Tenant-Id",
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
            tenant_id="Lambda-Runtime-Aws-Tenant-Id",
            content_type="Content-Type",
            event_body="another_response_body",
        )

        self.assertTrue(invocation_request == invocation_request)
        self.assertTrue(invocation_request == equal_invocation_request)
        self.assertFalse(invocation_request == different_invocation_request)


class TestLambdaRuntime(unittest.TestCase):
    get_next_headers = {
        "Lambda-Runtime-Aws-Request-Id": "RID1234",
        "Lambda-Runtime-Trace-Id": "TID1234",
        "Lambda-Runtime-Invoked-Function-Arn": "FARN1234",
        "Lambda-Runtime-Deadline-Ms": 12,
        "Lambda-Runtime-Client-Context": "client_context",
        "Lambda-Runtime-Cognito-Identity": "cognito_identity",
        "Lambda-Runtime-Aws-Tenant-Id": "tenant_id",
        "Content-Type": "application/json",
    }

    @patch("awslambdaric.lambda_runtime_client.runtime_client")
    def test_wait_next_invocation(self, mock_runtime_client):
        response_body = b"{}"
        mock_runtime_client.next.return_value = response_body, self.get_next_headers
        runtime_client = LambdaRuntimeClient("localhost:1234")

        event_request = runtime_client.wait_next_invocation()

        self.assertIsNotNone(event_request)
        self.assertEqual(event_request.invoke_id, "RID1234")
        self.assertEqual(event_request.x_amzn_trace_id, "TID1234")
        self.assertEqual(event_request.invoked_function_arn, "FARN1234")
        self.assertEqual(event_request.deadline_time_in_ms, 12)
        self.assertEqual(event_request.client_context, "client_context")
        self.assertEqual(event_request.cognito_identity, "cognito_identity")
        self.assertEqual(event_request.tenant_id, "tenant_id")
        self.assertEqual(event_request.content_type, "application/json")
        self.assertEqual(event_request.event_body, response_body)

        # Using ThreadPoolExecutor to polling next()
        runtime_client = LambdaRuntimeClient("localhost:1234", True)

        event_request = runtime_client.wait_next_invocation()

        self.assertIsNotNone(event_request)
        self.assertEqual(event_request.invoke_id, "RID1234")
        self.assertEqual(event_request.x_amzn_trace_id, "TID1234")
        self.assertEqual(event_request.invoked_function_arn, "FARN1234")
        self.assertEqual(event_request.deadline_time_in_ms, 12)
        self.assertEqual(event_request.client_context, "client_context")
        self.assertEqual(event_request.cognito_identity, "cognito_identity")
        self.assertEqual(event_request.tenant_id, "tenant_id")
        self.assertEqual(event_request.content_type, "application/json")
        self.assertEqual(event_request.event_body, response_body)

    @patch("awslambdaric.lambda_runtime_client.runtime_client")
    def test_wait_next_invocation_calls_next_from_separate_thread(
        self, mock_runtime_client
    ):
        thread_ids = []

        def record_thread_id():
            thread_ids.append(threading.get_ident())
            return b"{}", self.get_next_headers

        mock_runtime_client.next.side_effect = record_thread_id

        main_thread_id = threading.get_ident()

        runtime_client = LambdaRuntimeClient("localhost:1234", True)
        runtime_client.wait_next_invocation()

        self.assertEqual(len(thread_ids), 1)
        self.assertNotEqual(
            thread_ids[0],
            main_thread_id,
            "runtime_client.next() was not called from a separate thread",
        )

    @patch("awslambdaric.lambda_runtime_client.runtime_client")
    def test_wait_next_invocation_without_tenant_id_header(self, mock_runtime_client):
        response_body = b"{}"
        headers = {
            "Lambda-Runtime-Aws-Request-Id": "RID1234",
            "Lambda-Runtime-Trace-Id": "TID1234",
            "Lambda-Runtime-Invoked-Function-Arn": "FARN1234",
            "Lambda-Runtime-Deadline-Ms": 12,
            "Lambda-Runtime-Client-Context": "client_context",
            "Lambda-Runtime-Cognito-Identity": "cognito_identity",
            "Content-Type": "application/json",
        }
        mock_runtime_client.next.return_value = response_body, headers
        runtime_client = LambdaRuntimeClient("localhost:1234")

        event_request = runtime_client.wait_next_invocation()

        self.assertIsNotNone(event_request)
        self.assertIsNone(event_request.tenant_id)
        self.assertEqual(event_request.event_body, response_body)

    @patch("awslambdaric.lambda_runtime_client.runtime_client")
    def test_wait_next_invocation_with_null_tenant_id_header(self, mock_runtime_client):
        response_body = b"{}"
        headers = {
            "Lambda-Runtime-Aws-Request-Id": "RID1234",
            "Lambda-Runtime-Trace-Id": "TID1234",
            "Lambda-Runtime-Invoked-Function-Arn": "FARN1234",
            "Lambda-Runtime-Deadline-Ms": 12,
            "Lambda-Runtime-Client-Context": "client_context",
            "Lambda-Runtime-Cognito-Identity": "cognito_identity",
            "Lambda-Runtime-Aws-Tenant-Id": None,
            "Content-Type": "application/json",
        }
        mock_runtime_client.next.return_value = response_body, headers
        runtime_client = LambdaRuntimeClient("localhost:1234")

        event_request = runtime_client.wait_next_invocation()

        self.assertIsNotNone(event_request)
        self.assertIsNone(event_request.tenant_id)
        self.assertEqual(event_request.event_body, response_body)

    @patch("awslambdaric.lambda_runtime_client.runtime_client")
    def test_wait_next_invocation_with_empty_tenant_id_header(
        self, mock_runtime_client
    ):
        response_body = b"{}"
        headers = {
            "Lambda-Runtime-Aws-Request-Id": "RID1234",
            "Lambda-Runtime-Trace-Id": "TID1234",
            "Lambda-Runtime-Invoked-Function-Arn": "FARN1234",
            "Lambda-Runtime-Deadline-Ms": 12,
            "Lambda-Runtime-Client-Context": "client_context",
            "Lambda-Runtime-Cognito-Identity": "cognito_identity",
            "Lambda-Runtime-Aws-Tenant-Id": "",
            "Content-Type": "application/json",
        }
        mock_runtime_client.next.return_value = response_body, headers
        runtime_client = LambdaRuntimeClient("localhost:1234")

        event_request = runtime_client.wait_next_invocation()

        self.assertIsNotNone(event_request)
        self.assertEqual(event_request.tenant_id, "")
        self.assertEqual(event_request.event_body, response_body)

    error_result = {
        "errorMessage": "Dummy message",
        "errorType": "Runtime.DummyError",
        "requestId": "",
        "stackTrace": [],
    }

    headers = {"Lambda-Runtime-Function-Error-Type": error_result["errorType"]}

    restore_error_result = {
        "errorMessage": "Dummy Restore error",
        "errorType": "Runtime.DummyRestoreError",
        "requestId": "",
        "stackTrace": [],
    }

    restore_error_header = {
        "Lambda-Runtime-Function-Error-Type": "Runtime.AfterRestoreError"
    }

    before_snapshot_error_header = {
        "Lambda-Runtime-Function-Error-Type": "Runtime.BeforeSnapshotError"
    }

    @patch("http.client.HTTPConnection", autospec=http.client.HTTPConnection)
    def test_post_init_error(self, MockHTTPConnection):
        mock_conn = MockHTTPConnection.return_value
        mock_response = MagicMock(autospec=http.client.HTTPResponse)
        mock_conn.getresponse.return_value = mock_response
        mock_response.read.return_value = b""
        mock_response.code = http.HTTPStatus.ACCEPTED

        runtime_client = LambdaRuntimeClient("localhost:1234")
        runtime_client.post_init_error(self.error_result)

        MockHTTPConnection.assert_called_with("localhost:1234")
        mock_conn.request.assert_called_once_with(
            "POST",
            "/2018-06-01/runtime/init/error",
            to_json(self.error_result),
            headers=self.headers,
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
            runtime_client.post_init_error(self.error_result)
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
    def test_get_next_falls_back_to_backoff_if_multi_concurrent(
        self, mock_runtime_client
    ):
        # First call raises, second call succeeds
        mock_runtime_client.next.side_effect = [RuntimeError("first fail"), (b"{}", {})]
        client = LambdaMultiConcurrentRuntimeClient(
            "localhost:1234", use_thread_for_polling_next=True
        )

        result = client._get_next()
        self.assertEqual(result, (b"{}", {}))
        self.assertEqual(mock_runtime_client.next.call_count, 2)

    @patch("awslambdaric.lambda_runtime_client.runtime_client")
    def test_get_next_raises_if_not_multi_concurrent(self, mock_runtime_client):
        mock_runtime_client.next.side_effect = RuntimeError("fail")

        client = LambdaRuntimeClient("localhost:1234", use_thread_for_polling_next=True)

        with self.assertRaises(RuntimeError):
            client._get_next()

        self.assertEqual(mock_runtime_client.next.call_count, 1)

    @patch("awslambdaric.lambda_runtime_client.runtime_client")
    @patch("time.sleep", return_value=None)
    def test_get_next_retries_with_exponential_backoff(
        self, mock_sleep, mock_runtime_client
    ):
        # Simulate all attempts failing
        mock_runtime_client.next.side_effect = RuntimeError("always fail")
        client = LambdaMultiConcurrentRuntimeClient(
            "localhost:1234", use_thread_for_polling_next=True
        )

        with self.assertRaises(RuntimeError):
            client._get_next()

        # 1 initial + 4 retries
        self.assertEqual(mock_runtime_client.next.call_count, 5)

        expected_delays = [0.1, 0.2, 0.4, 0.8]
        actual_delays = [call.args[0] for call in mock_sleep.call_args_list]
        self.assertEqual(actual_delays, expected_delays)

    @patch("awslambdaric.lambda_runtime_client.runtime_client")
    def test_post_invocation_result_suppresses_error_if_multi_concurrent(
        self, mock_runtime_client
    ):
        mock_runtime_client.post_invocation_result.side_effect = RuntimeError("failure")

        client = LambdaMultiConcurrentRuntimeClient(
            "localhost:1234", use_thread_for_polling_next=True
        )

        with self.assertLogs(level="WARNING"):
            client.post_invocation_result("invoke_id", "result")

    @patch("awslambdaric.lambda_runtime_client.runtime_client")
    def test_post_invocation_result_raises_if_not_multi_concurrent(
        self, mock_runtime_client
    ):
        mock_runtime_client.post_invocation_result.side_effect = RuntimeError("failure")

        client = LambdaRuntimeClient("localhost:1234", use_thread_for_polling_next=True)

        with self.assertRaises(RuntimeError):
            client.post_invocation_result("invoke_id", "result")

    @patch("awslambdaric.lambda_runtime_client.runtime_client")
    def test_post_invocation_error_suppresses_error_if_multi_concurrent(
        self, mock_runtime_client
    ):
        mock_runtime_client.post_error.side_effect = RuntimeError("post error")

        client = LambdaMultiConcurrentRuntimeClient(
            "localhost:1234", use_thread_for_polling_next=True
        )

        with self.assertLogs(level="WARNING"):
            client.post_invocation_error("invoke_id", "error_data", "xray_data")

    @patch("awslambdaric.lambda_runtime_client.runtime_client")
    def test_post_invocation_error_raises_if_not_multi_concurrent(
        self, mock_runtime_client
    ):
        mock_runtime_client.post_error.side_effect = RuntimeError("post error")

        client = LambdaRuntimeClient("localhost:1234", use_thread_for_polling_next=True)

        with self.assertRaises(RuntimeError):
            client.post_invocation_error("invoke_id", "error_data", "xray_data")

    @patch("http.client.HTTPConnection", autospec=http.client.HTTPConnection)
    def test_post_init_error_suppresses_403_if_multi_concurrent(
        self, MockHTTPConnection
    ):
        mock_conn = MockHTTPConnection.return_value
        mock_response = MagicMock(autospec=http.client.HTTPResponse)
        mock_conn.getresponse.return_value = mock_response
        mock_response.read.return_value = b""
        mock_response.code = http.HTTPStatus.FORBIDDEN

        client = LambdaMultiConcurrentRuntimeClient("localhost:1234")

        # Should not raise exception for 403 error
        client.post_init_error(self.error_result)

    @patch("http.client.HTTPConnection", autospec=http.client.HTTPConnection)
    def test_post_init_error_raises_non_403_if_multi_concurrent(
        self, MockHTTPConnection
    ):
        mock_conn = MockHTTPConnection.return_value
        mock_response = MagicMock(autospec=http.client.HTTPResponse)
        mock_conn.getresponse.return_value = mock_response
        mock_response.read.return_value = b""
        mock_response.code = http.HTTPStatus.INTERNAL_SERVER_ERROR

        client = LambdaMultiConcurrentRuntimeClient("localhost:1234")

        with self.assertRaises(LambdaRuntimeClientError):
            client.post_init_error(self.error_result)

    @patch("http.client.HTTPConnection", autospec=http.client.HTTPConnection)
    def test_post_init_error_raises_403_if_not_multi_concurrent(
        self, MockHTTPConnection
    ):
        mock_conn = MockHTTPConnection.return_value
        mock_response = MagicMock(autospec=http.client.HTTPResponse)
        mock_conn.getresponse.return_value = mock_response
        mock_response.read.return_value = b""
        mock_response.code = http.HTTPStatus.FORBIDDEN

        client = LambdaRuntimeClient("localhost:1234")

        with self.assertRaises(LambdaRuntimeClientError):
            client.post_init_error(self.error_result)

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

    @patch("http.client.HTTPConnection", autospec=http.client.HTTPConnection)
    def test_restore_next(self, MockHTTPConnection):
        mock_conn = MockHTTPConnection.return_value
        mock_response = MagicMock(autospec=http.client.HTTPResponse)
        mock_conn.getresponse.return_value = mock_response
        mock_response.read.return_value = b""
        mock_response.code = http.HTTPStatus.OK

        runtime_client = LambdaRuntimeClient("localhost:1234")
        runtime_client.restore_next()

        MockHTTPConnection.assert_called_with("localhost:1234")
        mock_conn.request.assert_called_once_with(
            "GET",
            "/2018-06-01/runtime/restore/next",
        )
        mock_response.read.assert_called_once()

    @patch("http.client.HTTPConnection", autospec=http.client.HTTPConnection)
    def test_restore_error(self, MockHTTPConnection):
        mock_conn = MockHTTPConnection.return_value
        mock_response = MagicMock(autospec=http.client.HTTPResponse)
        mock_conn.getresponse.return_value = mock_response
        mock_response.read.return_value = b""
        mock_response.code = http.HTTPStatus.ACCEPTED

        runtime_client = LambdaRuntimeClient("localhost:1234")
        runtime_client.report_restore_error(self.restore_error_result)

        MockHTTPConnection.assert_called_with("localhost:1234")
        mock_conn.request.assert_called_once_with(
            "POST",
            "/2018-06-01/runtime/restore/error",
            to_json(self.restore_error_result),
            headers=self.restore_error_header,
        )
        mock_response.read.assert_called_once()

    @patch("http.client.HTTPConnection", autospec=http.client.HTTPConnection)
    def test_init_before_snapshot_error(self, MockHTTPConnection):
        mock_conn = MockHTTPConnection.return_value
        mock_response = MagicMock(autospec=http.client.HTTPResponse)
        mock_conn.getresponse.return_value = mock_response
        mock_response.read.return_value = b""
        mock_response.code = http.HTTPStatus.ACCEPTED

        runtime_client = LambdaRuntimeClient("localhost:1234")
        runtime_client.post_init_error(self.error_result, "Runtime.BeforeSnapshotError")

        MockHTTPConnection.assert_called_with("localhost:1234")
        mock_conn.request.assert_called_once_with(
            "POST",
            "/2018-06-01/runtime/init/error",
            to_json(self.error_result),
            headers=self.before_snapshot_error_header,
        )
        mock_response.read.assert_called_once()

    def test_connection_refused(self):
        with self.assertRaises(ConnectionRefusedError):
            runtime_client = LambdaRuntimeClient("127.0.0.1:1")
            runtime_client.post_init_error(self.error_result)

    def test_invalid_addr(self):
        with self.assertRaises(OSError):
            runtime_client = LambdaRuntimeClient("::::")
            runtime_client.post_init_error(self.error_result)

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
