"""
Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import importlib
import json
import os
import re
import tempfile
import traceback
import unittest
from io import StringIO
from tempfile import NamedTemporaryFile
from unittest.mock import MagicMock, Mock, patch

import awslambdaric.bootstrap as bootstrap
from awslambdaric.lambda_runtime_exception import FaultException
from awslambdaric.lambda_runtime_marshaller import LambdaMarshaller


class TestUpdateXrayEnv(unittest.TestCase):
    def setUp(self):
        self.org_os_environ = os.environ

    def tearDown(self):
        os.environ = self.org_os_environ

    def test_update_xray_env_variable_empty(self):
        os.environ = {}
        bootstrap.update_xray_env_variable(None)
        self.assertEqual(os.environ.get("_X_AMZN_TRACE_ID"), None)

    def test_update_xray_env_variable_remove_old_value(self):
        os.environ = {"_X_AMZN_TRACE_ID": "old-id"}
        bootstrap.update_xray_env_variable(None)
        self.assertEqual(os.environ.get("_X_AMZN_TRACE_ID"), None)

    def test_update_xray_env_variable_new_value(self):
        os.environ = {}
        bootstrap.update_xray_env_variable("new-id")
        self.assertEqual(os.environ.get("_X_AMZN_TRACE_ID"), "new-id")

    def test_update_xray_env_variable_overwrite(self):
        os.environ = {"_X_AMZN_TRACE_ID": "old-id"}
        bootstrap.update_xray_env_variable("new-id")
        self.assertEqual(os.environ.get("_X_AMZN_TRACE_ID"), "new-id")


class TestHandleEventRequest(unittest.TestCase):
    def setUp(self):
        self.lambda_runtime = Mock()
        self.lambda_runtime.marshaller = LambdaMarshaller()
        self.event_body = '"event_body"'
        self.working_directory = os.getcwd()

    @staticmethod
    def dummy_handler(json_input, lambda_context):
        return {"input": json_input, "aws_request_id": lambda_context.aws_request_id}

    def test_handle_event_request_happy_case(self):
        bootstrap.handle_event_request(
            self.lambda_runtime,
            self.dummy_handler,
            "invoke_id",
            self.event_body,
            "application/json",
            {},
            {},
            "invoked_function_arn",
            0,
            bootstrap.StandardLogSink(),
        )
        self.lambda_runtime.post_invocation_result.assert_called_once_with(
            "invoke_id",
            '{"input": "event_body", "aws_request_id": "invoke_id"}',
            "application/json",
        )

    def test_handle_event_request_invalid_client_context(self):
        expected_response = {
            "errorType": "Runtime.LambdaContextUnmarshalError",
            "errorMessage": "Unable to parse Client Context JSON: Expecting value: line 1 column 1 (char 0)",
        }
        bootstrap.handle_event_request(
            self.lambda_runtime,
            self.dummy_handler,
            "invoke_id",
            self.event_body,
            "application/json",
            "invalid_client_context_not_json",
            {},
            "invoked_function_arn",
            0,
            bootstrap.StandardLogSink(),
        )
        args, _ = self.lambda_runtime.post_invocation_error.call_args
        error_response = json.loads(args[1])
        self.assertEqual(args[0], "invoke_id")
        self.assertTrue(
            expected_response.items() <= error_response.items(),
            "Response doesn't contain all the necessary fields\nExpected: {}\nActual: {}".format(
                expected_response, error_response
            ),
        )
        self.assertEqual(
            json.loads(args[2]),
            {
                "working_directory": self.working_directory,
                "exceptions": [
                    {
                        "message": expected_response["errorMessage"],
                        "type": "LambdaValidationError",
                        "stack": [],
                    }
                ],
                "paths": [],
            },
        )

    def test_handle_event_request_invalid_cognito_idenity(self):
        expected_response = {
            "errorType": "Runtime.LambdaContextUnmarshalError",
            "errorMessage": "Unable to parse Cognito Identity JSON: Expecting value: line 1 column 1 (char 0)",
        }
        bootstrap.handle_event_request(
            self.lambda_runtime,
            self.dummy_handler,
            "invoke_id",
            self.event_body,
            "application/json",
            {},
            "invalid_cognito_identity",
            "invoked_function_arn",
            0,
            bootstrap.StandardLogSink(),
        )
        args, _ = self.lambda_runtime.post_invocation_error.call_args
        error_response = json.loads(args[1])
        self.assertEqual(args[0], "invoke_id")
        self.assertTrue(
            expected_response.items() <= error_response.items(),
            "Response doesn't contain all the necessary fields\nExpected: {}\nActual: {}".format(
                expected_response, error_response
            ),
        )
        self.assertEqual(
            json.loads(args[2]),
            {
                "working_directory": self.working_directory,
                "exceptions": [
                    {
                        "message": expected_response["errorMessage"],
                        "type": "LambdaValidationError",
                        "stack": [],
                    }
                ],
                "paths": [],
            },
        )

    def test_handle_event_request_invalid_event_body(self):
        expected_response = {
            "errorType": "Runtime.UnmarshalError",
            "errorMessage": "Unable to unmarshal input: Expecting value: line 1 column 1 (char 0)",
        }
        invalid_event_body = "not_valid_json"
        bootstrap.handle_event_request(
            self.lambda_runtime,
            self.dummy_handler,
            "invoke_id",
            invalid_event_body,
            "application/json",
            {},
            {},
            "invoked_function_arn",
            0,
            bootstrap.StandardLogSink(),
        )
        args, _ = self.lambda_runtime.post_invocation_error.call_args
        error_response = json.loads(args[1])
        self.assertEqual(args[0], "invoke_id")
        self.assertTrue(
            expected_response.items() <= error_response.items(),
            "Response doesn't contain all the necessary fields\nExpected: {}\nActual: {}".format(
                expected_response, error_response
            ),
        )
        self.assertEqual(
            json.loads(args[2]),
            {
                "working_directory": self.working_directory,
                "exceptions": [
                    {
                        "message": expected_response["errorMessage"],
                        "type": "LambdaValidationError",
                        "stack": [],
                    }
                ],
                "paths": [],
            },
        )

    def test_handle_event_request_invalid_response(self):
        def invalid_json_response(json_input, lambda_context):
            return type("obj", (object,), {"propertyName": "propertyValue"})

        expected_response = {
            "errorType": "Runtime.MarshalError",
            "errorMessage": "Unable to marshal response: Object of type type is not JSON serializable",
        }
        bootstrap.handle_event_request(
            self.lambda_runtime,
            invalid_json_response,
            "invoke_id",
            self.event_body,
            "application/json",
            {},
            {},
            "invoked_function_arn",
            0,
            bootstrap.StandardLogSink(),
        )
        args, _ = self.lambda_runtime.post_invocation_error.call_args
        error_response = json.loads(args[1])
        self.assertEqual(args[0], "invoke_id")
        self.assertTrue(
            expected_response.items() <= error_response.items(),
            "Expected response is not a subset of the actual response\nExpected: {}\nActual: {}".format(
                expected_response, error_response
            ),
        )
        self.assertEqual(
            json.loads(args[2]),
            {
                "working_directory": self.working_directory,
                "exceptions": [
                    {
                        "message": expected_response["errorMessage"],
                        "type": "LambdaValidationError",
                        "stack": [],
                    }
                ],
                "paths": [],
            },
        )

    def test_handle_event_request_custom_exception(self):
        def raise_exception_handler(json_input, lambda_context):
            class MyError(Exception):
                def __init__(self, message):
                    self.message = message

            raise MyError("My error")

        expected_response = {"errorType": "MyError", "errorMessage": "My error"}
        bootstrap.handle_event_request(
            self.lambda_runtime,
            raise_exception_handler,
            "invoke_id",
            self.event_body,
            "application/json",
            {},
            {},
            "invoked_function_arn",
            0,
            bootstrap.StandardLogSink(),
        )
        args, _ = self.lambda_runtime.post_invocation_error.call_args
        error_response = json.loads(args[1])
        self.assertEqual(args[0], "invoke_id")
        self.assertTrue(
            expected_response.items() <= error_response.items(),
            "Expected response is not a subset of the actual response\nExpected: {}\nActual: {}".format(
                expected_response, error_response
            ),
        )
        xray_fault = json.loads(args[2])
        self.assertEqual(xray_fault["working_directory"], self.working_directory)
        self.assertEqual(len(xray_fault["exceptions"]), 1)
        self.assertEqual(
            xray_fault["exceptions"][0]["message"], expected_response["errorMessage"]
        )
        self.assertEqual(
            xray_fault["exceptions"][0]["type"], expected_response["errorType"]
        )
        self.assertEqual(len(xray_fault["exceptions"][0]["stack"]), 1)
        self.assertEqual(
            xray_fault["exceptions"][0]["stack"][0]["label"], "raise_exception_handler"
        )
        self.assertIsInstance(xray_fault["exceptions"][0]["stack"][0]["line"], int)
        self.assertTrue(
            xray_fault["exceptions"][0]["stack"][0]["path"].endswith(
                os.path.relpath(__file__)
            )
        )
        self.assertEqual(len(xray_fault["paths"]), 1)
        self.assertTrue(xray_fault["paths"][0].endswith(os.path.relpath(__file__)))

    def test_handle_event_request_custom_empty_error_message_exception(self):
        def raise_exception_handler(json_input, lambda_context):
            class MyError(Exception):
                def __init__(self, message):
                    self.message = message

            raise MyError("")

        expected_response = {"errorType": "MyError", "errorMessage": ""}
        bootstrap.handle_event_request(
            self.lambda_runtime,
            raise_exception_handler,
            "invoke_id",
            self.event_body,
            "application/json",
            {},
            {},
            "invoked_function_arn",
            0,
            bootstrap.StandardLogSink(),
        )
        args, _ = self.lambda_runtime.post_invocation_error.call_args
        error_response = json.loads(args[1])
        self.assertEqual(args[0], "invoke_id")
        self.assertTrue(
            expected_response.items() <= error_response.items(),
            "Expected response is not a subset of the actual response\nExpected: {}\nActual: {}".format(
                expected_response, error_response
            ),
        )
        xray_fault = json.loads(args[2])
        self.assertEqual(xray_fault["working_directory"], self.working_directory)
        self.assertEqual(len(xray_fault["exceptions"]), 1)
        self.assertEqual(
            xray_fault["exceptions"][0]["message"], expected_response["errorMessage"]
        )
        self.assertEqual(
            xray_fault["exceptions"][0]["type"], expected_response["errorType"]
        )
        self.assertEqual(len(xray_fault["exceptions"][0]["stack"]), 1)
        self.assertEqual(
            xray_fault["exceptions"][0]["stack"][0]["label"], "raise_exception_handler"
        )
        self.assertIsInstance(xray_fault["exceptions"][0]["stack"][0]["line"], int)
        self.assertTrue(
            xray_fault["exceptions"][0]["stack"][0]["path"].endswith(
                os.path.relpath(__file__)
            )
        )
        self.assertEqual(len(xray_fault["paths"]), 1)
        self.assertTrue(xray_fault["paths"][0].endswith(os.path.relpath(__file__)))

    def test_handle_event_request_no_module(self):
        def unable_to_import_module(json_input, lambda_context):
            import invalid_module  # noqa: F401

        expected_response = {
            "errorType": "ModuleNotFoundError",
            "errorMessage": "No module named 'invalid_module'",
        }
        bootstrap.handle_event_request(
            self.lambda_runtime,
            unable_to_import_module,
            "invoke_id",
            self.event_body,
            "application/json",
            {},
            {},
            "invoked_function_arn",
            0,
            bootstrap.StandardLogSink(),
        )
        args, _ = self.lambda_runtime.post_invocation_error.call_args
        error_response = json.loads(args[1])
        self.assertEqual(args[0], "invoke_id")
        self.assertTrue(
            expected_response.items() <= error_response.items(),
            "Expected response is not a subset of the actual response\nExpected: {}\nActual: {}".format(
                expected_response, error_response
            ),
        )

    def test_handle_event_request_fault_exception(self):
        def raise_exception_handler(json_input, lambda_context):
            try:
                import invalid_module  # noqa: F401
            except ImportError:
                raise FaultException(
                    "FaultExceptionType",
                    "Fault exception msg",
                    ["trace_line1\ntrace_line2", "trace_line3\ntrace_line4"],
                )

        expected_response = {
            "errorType": "FaultExceptionType",
            "errorMessage": "Fault exception msg",
            "requestId": "invoke_id",
            "stackTrace": ["trace_line1\ntrace_line2", "trace_line3\ntrace_line4"],
        }
        bootstrap.handle_event_request(
            self.lambda_runtime,
            raise_exception_handler,
            "invoke_id",
            self.event_body,
            "application/json",
            {},
            {},
            "invoked_function_arn",
            0,
            bootstrap.StandardLogSink(),
        )
        args, _ = self.lambda_runtime.post_invocation_error.call_args
        error_response = json.loads(args[1])
        self.assertEqual(args[0], "invoke_id")
        self.assertEqual(error_response.items(), expected_response.items())
        self.assertEqual(
            json.loads(args[2]),
            {
                "working_directory": self.working_directory,
                "exceptions": [
                    {
                        "message": expected_response["errorMessage"],
                        "type": "LambdaValidationError",
                        "stack": [],
                    }
                ],
                "paths": [],
            },
        )

    @patch("sys.stdout", new_callable=StringIO)
    def test_handle_event_request_fault_exception_logging(self, mock_stdout):
        def raise_exception_handler(json_input, lambda_context):
            try:
                import invalid_module  # noqa: F401
            except ImportError:
                raise bootstrap.FaultException(
                    "FaultExceptionType",
                    "Fault exception msg",
                    traceback.format_list(
                        [
                            ("spam.py", 3, "<module>", "spam.eggs()"),
                            ("eggs.py", 42, "eggs", 'return "bacon"'),
                        ]
                    ),
                )

        bootstrap.handle_event_request(
            self.lambda_runtime,
            raise_exception_handler,
            "invoke_id",
            self.event_body,
            "application/json",
            {},
            {},
            "invoked_function_arn",
            0,
            bootstrap.StandardLogSink(),
        )

        # NOTE: Indentation characters are NO-BREAK SPACE (U+00A0) not SPACE (U+0020)
        error_logs = "[ERROR] FaultExceptionType: Fault exception msg\r"
        error_logs += "Traceback (most recent call last):\r"
        error_logs += '  File "spam.py", line 3, in <module>\r'
        error_logs += "    spam.eggs()\r"
        error_logs += '  File "eggs.py", line 42, in eggs\r'
        error_logs += '    return "bacon"\n'

        self.assertEqual(mock_stdout.getvalue(), error_logs)

    @patch("sys.stdout", new_callable=StringIO)
    def test_handle_event_request_fault_exception_logging_notrace(self, mock_stdout):
        def raise_exception_handler(json_input, lambda_context):
            try:
                import invalid_module  # noqa: F401
            except ImportError:
                raise bootstrap.FaultException(
                    "FaultExceptionType", "Fault exception msg", None
                )

        bootstrap.handle_event_request(
            self.lambda_runtime,
            raise_exception_handler,
            "invoke_id",
            self.event_body,
            "application/json",
            {},
            {},
            "invoked_function_arn",
            0,
            bootstrap.StandardLogSink(),
        )
        error_logs = "[ERROR] FaultExceptionType: Fault exception msg\rTraceback (most recent call last):\n"

        self.assertEqual(mock_stdout.getvalue(), error_logs)

    @patch("sys.stdout", new_callable=StringIO)
    def test_handle_event_request_fault_exception_logging_nomessage_notrace(
        self, mock_stdout
    ):
        def raise_exception_handler(json_input, lambda_context):
            try:
                import invalid_module  # noqa: F401
            except ImportError:
                raise bootstrap.FaultException("FaultExceptionType", None, None)

        bootstrap.handle_event_request(
            self.lambda_runtime,
            raise_exception_handler,
            "invoke_id",
            self.event_body,
            "application/json",
            {},
            {},
            "invoked_function_arn",
            0,
            bootstrap.StandardLogSink(),
        )
        error_logs = "[ERROR] FaultExceptionType\rTraceback (most recent call last):\n"

        self.assertEqual(mock_stdout.getvalue(), error_logs)

    @patch("sys.stdout", new_callable=StringIO)
    def test_handle_event_request_fault_exception_logging_notype_notrace(
        self, mock_stdout
    ):
        def raise_exception_handler(json_input, lambda_context):
            try:
                import invalid_module  # noqa: F401
            except ImportError:
                raise bootstrap.FaultException(None, "Fault exception msg", None)

        bootstrap.handle_event_request(
            self.lambda_runtime,
            raise_exception_handler,
            "invoke_id",
            self.event_body,
            "application/json",
            {},
            {},
            "invoked_function_arn",
            0,
            bootstrap.StandardLogSink(),
        )
        error_logs = "[ERROR] Fault exception msg\rTraceback (most recent call last):\n"

        self.assertEqual(mock_stdout.getvalue(), error_logs)

    @patch("sys.stdout", new_callable=StringIO)
    def test_handle_event_request_fault_exception_logging_notype_nomessage(
        self, mock_stdout
    ):
        def raise_exception_handler(json_input, lambda_context):
            try:
                import invalid_module  # noqa: F401
            except ImportError:
                raise bootstrap.FaultException(
                    None,
                    None,
                    traceback.format_list(
                        [
                            ("spam.py", 3, "<module>", "spam.eggs()"),
                            ("eggs.py", 42, "eggs", 'return "bacon"'),
                        ]
                    ),
                )

        bootstrap.handle_event_request(
            self.lambda_runtime,
            raise_exception_handler,
            "invoke_id",
            self.event_body,
            "application/json",
            {},
            {},
            "invoked_function_arn",
            0,
            bootstrap.StandardLogSink(),
        )

        error_logs = "[ERROR]\r"
        error_logs += "Traceback (most recent call last):\r"
        error_logs += '  File "spam.py", line 3, in <module>\r'
        error_logs += "    spam.eggs()\r"
        error_logs += '  File "eggs.py", line 42, in eggs\r'
        error_logs += '    return "bacon"\n'

        self.assertEqual(mock_stdout.getvalue(), error_logs)

    @patch("sys.stdout", new_callable=StringIO)
    @patch("importlib.import_module")
    def test_handle_event_request_fault_exception_logging_syntax_error(
        self, mock_import_module, mock_stdout
    ):
        try:
            eval("-")
        except SyntaxError as e:
            syntax_error = e

        mock_import_module.side_effect = syntax_error

        response_handler = bootstrap._get_handler("a.b")

        bootstrap.handle_event_request(
            self.lambda_runtime,
            response_handler,
            "invoke_id",
            self.event_body,
            "application/json",
            {},
            {},
            "invoked_function_arn",
            0,
            bootstrap.StandardLogSink(),
        )

        import sys

        sys.stderr.write(mock_stdout.getvalue())

        error_logs = (
            "[ERROR] Runtime.UserCodeSyntaxError: Syntax error in module 'a': "
            "unexpected EOF while parsing (<string>, line 1)\r"
        )
        error_logs += "Traceback (most recent call last):\r"
        error_logs += '  File "<string>" Line 1\r'
        error_logs += "    -\n"

        self.assertEqual(mock_stdout.getvalue(), error_logs)


class TestXrayFault(unittest.TestCase):
    def test_make_xray(self):
        class CustomException(Exception):
            def __init__(self):
                pass

        actual = bootstrap.make_xray_fault(
            CustomException.__name__,
            "test_message",
            "working/dir",
            [["test.py", 28, "test_method", "does_not_matter"]],
        )

        self.assertEqual(actual["working_directory"], "working/dir")
        self.assertEqual(actual["paths"], ["test.py"])
        self.assertEqual(len(actual["exceptions"]), 1)
        self.assertEqual(actual["exceptions"][0]["message"], "test_message")
        self.assertEqual(actual["exceptions"][0]["type"], "CustomException")
        self.assertEqual(len(actual["exceptions"][0]["stack"]), 1)
        self.assertEqual(actual["exceptions"][0]["stack"][0]["label"], "test_method")
        self.assertEqual(actual["exceptions"][0]["stack"][0]["path"], "test.py")
        self.assertEqual(actual["exceptions"][0]["stack"][0]["line"], 28)

    def test_make_xray_with_multiple_tb(self):
        class CustomException(Exception):
            def __init__(self):
                pass

        actual = bootstrap.make_xray_fault(
            CustomException.__name__,
            "test_message",
            "working/dir",
            [
                ["test.py", 28, "test_method", ""],
                ["another_test.py", 2718, "another_test_method", ""],
            ],
        )

        self.assertEqual(len(actual["exceptions"]), 1)
        self.assertEqual(len(actual["exceptions"][0]["stack"]), 2)
        self.assertEqual(actual["exceptions"][0]["stack"][0]["label"], "test_method")
        self.assertEqual(actual["exceptions"][0]["stack"][0]["path"], "test.py")
        self.assertEqual(actual["exceptions"][0]["stack"][0]["line"], 28)
        self.assertEqual(
            actual["exceptions"][0]["stack"][1]["label"], "another_test_method"
        )
        self.assertEqual(actual["exceptions"][0]["stack"][1]["path"], "another_test.py")
        self.assertEqual(actual["exceptions"][0]["stack"][1]["line"], 2718)


class TestGetEventHandler(unittest.TestCase):
    class FaultExceptionMatcher(BaseException):
        def __init__(self, msg, exception_type=None, trace_pattern=None):
            self.msg = msg
            self.exception_type = exception_type
            self.trace = (
                trace_pattern if trace_pattern is None else re.compile(trace_pattern)
            )

        def __eq__(self, other):
            trace_matches = True
            if self.trace is not None:
                # Validate that trace is an array
                if not isinstance(other.trace, list):
                    trace_matches = False
                elif not self.trace.match("".join(other.trace)):
                    trace_matches = False

            return (
                self.msg in other.msg
                and self.exception_type == other.exception_type
                and trace_matches
            )

    def test_get_event_handler_bad_handler(self):
        handler_name = "bad_handler"
        response_handler = bootstrap._get_handler(handler_name)
        with self.assertRaises(FaultException) as cm:
            response_handler()

        returned_exception = cm.exception
        self.assertEqual(
            self.FaultExceptionMatcher(
                "Bad handler 'bad_handler': not enough values to unpack (expected 2, got 1)",
                "Runtime.MalformedHandlerName",
            ),
            returned_exception,
        )

    def test_get_event_handler_import_error(self):
        handler_name = "no_module.handler"
        response_handler = bootstrap._get_handler(handler_name)
        with self.assertRaises(FaultException) as cm:
            response_handler()
        returned_exception = cm.exception
        self.assertEqual(
            self.FaultExceptionMatcher(
                "Unable to import module 'no_module': No module named 'no_module'",
                "Runtime.ImportModuleError",
            ),
            returned_exception,
        )

    def test_get_event_handler_syntax_error(self):
        importlib.invalidate_caches()
        with tempfile.NamedTemporaryFile(
            suffix=".py", dir=".", delete=False
        ) as tmp_file:
            tmp_file.write(
                b"def syntax_error()\n\tprint('syntax error, no colon after function')"
            )
            tmp_file.flush()

            filename_w_ext = os.path.basename(tmp_file.name)
            filename, _ = os.path.splitext(filename_w_ext)
            handler_name = "{}.syntax_error".format(filename)
            response_handler = bootstrap._get_handler(handler_name)

            with self.assertRaises(FaultException) as cm:
                response_handler()
            returned_exception = cm.exception
            self.assertEqual(
                self.FaultExceptionMatcher(
                    "Syntax error in",
                    "Runtime.UserCodeSyntaxError",
                    ".*File.*\\.py.*Line 1.*",
                ),
                returned_exception,
            )

    def test_get_event_handler_missing_error(self):
        importlib.invalidate_caches()
        with tempfile.NamedTemporaryFile(
            suffix=".py", dir=".", delete=False
        ) as tmp_file:
            tmp_file.write(b"def wrong_handler_name():\n\tprint('hello')")
            tmp_file.flush()

            filename_w_ext = os.path.basename(tmp_file.name)
            filename, _ = os.path.splitext(filename_w_ext)
            handler_name = "{}.my_handler".format(filename)
            response_handler = bootstrap._get_handler(handler_name)
            with self.assertRaises(FaultException) as cm:
                response_handler()
            returned_exception = cm.exception
            self.assertEqual(
                self.FaultExceptionMatcher(
                    "Handler 'my_handler' missing on module '{}'".format(filename),
                    "Runtime.HandlerNotFound",
                ),
                returned_exception,
            )

    def test_get_event_handler_slash(self):
        importlib.invalidate_caches()
        handler_name = "tests/test_handler_with_slash/test_handler.my_handler"
        response_handler = bootstrap._get_handler(handler_name)
        response_handler()

    def test_get_event_handler_build_in_conflict(self):
        response_handler = bootstrap._get_handler("sys.hello")
        with self.assertRaises(FaultException) as cm:
            response_handler()
        returned_exception = cm.exception
        self.assertEqual(
            self.FaultExceptionMatcher(
                "Cannot use built-in module sys as a handler module",
                "Runtime.BuiltInModuleConflict",
            ),
            returned_exception,
        )

    def test_get_event_handler_doesnt_throw_build_in_module_name_slash(self):
        response_handler = bootstrap._get_handler(
            "tests/test_built_in_module_name/sys.my_handler"
        )
        response_handler()

    def test_get_event_handler_doent_throw_build_in_module_name(self):
        response_handler = bootstrap._get_handler(
            "tests.test_built_in_module_name.sys.my_handler"
        )
        response_handler()


class TestContentType(unittest.TestCase):
    def setUp(self):
        self.lambda_runtime = Mock()
        self.lambda_runtime.marshaller = LambdaMarshaller()

    def test_application_json(self):
        bootstrap.handle_event_request(
            lambda_runtime_client=self.lambda_runtime,
            request_handler=lambda event, ctx: {"response": event["msg"]},
            invoke_id="invoke-id",
            event_body=b'{"msg":"foo"}',
            content_type="application/json",
            client_context_json=None,
            cognito_identity_json=None,
            invoked_function_arn="invocation-arn",
            epoch_deadline_time_in_ms=1415836801003,
            log_sink=bootstrap.StandardLogSink(),
        )

        self.lambda_runtime.post_invocation_result.assert_called_once_with(
            "invoke-id", '{"response": "foo"}', "application/json"
        )

    def test_binary_request_binary_response(self):
        event_body = b"\x89PNG\r\n\x1a\n\x00\x00\x00"
        bootstrap.handle_event_request(
            lambda_runtime_client=self.lambda_runtime,
            request_handler=lambda event, ctx: event,
            invoke_id="invoke-id",
            event_body=event_body,
            content_type="image/png",
            client_context_json=None,
            cognito_identity_json=None,
            invoked_function_arn="invocation-arn",
            epoch_deadline_time_in_ms=1415836801003,
            log_sink=bootstrap.StandardLogSink(),
        )

        self.lambda_runtime.post_invocation_result.assert_called_once_with(
            "invoke-id", event_body, "application/unknown"
        )

    def test_json_request_binary_response(self):
        binary_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00"
        bootstrap.handle_event_request(
            lambda_runtime_client=self.lambda_runtime,
            request_handler=lambda event, ctx: binary_data,
            invoke_id="invoke-id",
            event_body=b'{"msg":"ignored"}',
            content_type="application/json",
            client_context_json=None,
            cognito_identity_json=None,
            invoked_function_arn="invocation-arn",
            epoch_deadline_time_in_ms=1415836801003,
            log_sink=bootstrap.StandardLogSink(),
        )

        self.lambda_runtime.post_invocation_result.assert_called_once_with(
            "invoke-id", binary_data, "application/unknown"
        )

    def test_binary_with_application_json(self):
        bootstrap.handle_event_request(
            lambda_runtime_client=self.lambda_runtime,
            request_handler=lambda event, ctx: event,
            invoke_id="invoke-id",
            event_body=b"\x89PNG\r\n\x1a\n\x00\x00\x00",
            content_type="application/json",
            client_context_json=None,
            cognito_identity_json=None,
            invoked_function_arn="invocation-arn",
            epoch_deadline_time_in_ms=1415836801003,
            log_sink=bootstrap.StandardLogSink(),
        )

        self.lambda_runtime.post_invocation_result.assert_not_called()
        self.lambda_runtime.post_invocation_error.assert_called_once()

        (
            invoke_id,
            error_result,
            xray_fault,
        ), _ = self.lambda_runtime.post_invocation_error.call_args
        error_dict = json.loads(error_result)

        self.assertEqual("invoke-id", invoke_id)
        self.assertEqual("Runtime.UnmarshalError", error_dict["errorType"])


class TestLogError(unittest.TestCase):
    @patch("sys.stdout", new_callable=StringIO)
    def test_log_error_standard_log_sink(self, mock_stdout):
        err_to_log = bootstrap.make_error("Error message", "ErrorType", None)
        bootstrap.log_error(err_to_log, bootstrap.StandardLogSink())

        expected_logged_error = (
            "[ERROR] ErrorType: Error message\rTraceback (most recent call last):\n"
        )
        self.assertEqual(mock_stdout.getvalue(), expected_logged_error)

    def test_log_error_framed_log_sink(self):
        with NamedTemporaryFile() as temp_file:
            with bootstrap.FramedTelemetryLogSink(
                os.open(temp_file.name, os.O_CREAT | os.O_RDWR)
            ) as log_sink:
                err_to_log = bootstrap.make_error("Error message", "ErrorType", None)
                bootstrap.log_error(err_to_log, log_sink)

            expected_logged_error = (
                "[ERROR] ErrorType: Error message\nTraceback (most recent call last):"
            )

            with open(temp_file.name, "rb") as f:
                content = f.read()

                frame_type = int.from_bytes(content[:4], "big")
                self.assertEqual(frame_type, 0xA55A0001)

                length = int.from_bytes(content[4:8], "big")
                self.assertEqual(length, len(expected_logged_error.encode("utf8")))

                actual_message = content[8:].decode()
                self.assertEqual(actual_message, expected_logged_error)

    @patch("sys.stdout", new_callable=StringIO)
    def test_log_error_indentation_standard_log_sink(self, mock_stdout):
        err_to_log = bootstrap.make_error(
            "Error message", "ErrorType", ["  line1  ", "  line2  ", "  "]
        )
        bootstrap.log_error(err_to_log, bootstrap.StandardLogSink())

        expected_logged_error = (
            "[ERROR] ErrorType: Error message\rTraceback (most recent call last):"
            "\r\xa0\xa0line1  \r\xa0\xa0line2  \r\xa0\xa0\n"
        )
        self.assertEqual(mock_stdout.getvalue(), expected_logged_error)

    def test_log_error_indentation_framed_log_sink(self):
        with NamedTemporaryFile() as temp_file:
            with bootstrap.FramedTelemetryLogSink(
                os.open(temp_file.name, os.O_CREAT | os.O_RDWR)
            ) as log_sink:
                err_to_log = bootstrap.make_error(
                    "Error message", "ErrorType", ["  line1  ", "  line2  ", "  "]
                )
                bootstrap.log_error(err_to_log, log_sink)

            expected_logged_error = (
                "[ERROR] ErrorType: Error message\nTraceback (most recent call last):"
                "\n\xa0\xa0line1  \n\xa0\xa0line2  \n\xa0\xa0"
            )

            with open(temp_file.name, "rb") as f:
                content = f.read()

                frame_type = int.from_bytes(content[:4], "big")
                self.assertEqual(frame_type, 0xA55A0001)

                length = int.from_bytes(content[4:8], "big")
                self.assertEqual(length, len(expected_logged_error.encode("utf8")))

                actual_message = content[8:].decode()
                self.assertEqual(actual_message, expected_logged_error)

    @patch("sys.stdout", new_callable=StringIO)
    def test_log_error_empty_stacktrace_line_standard_log_sink(self, mock_stdout):
        err_to_log = bootstrap.make_error(
            "Error message", "ErrorType", ["line1", "", "line2"]
        )
        bootstrap.log_error(err_to_log, bootstrap.StandardLogSink())

        expected_logged_error = "[ERROR] ErrorType: Error message\rTraceback (most recent call last):\rline1\r\rline2\n"
        self.assertEqual(mock_stdout.getvalue(), expected_logged_error)

    def test_log_error_empty_stacktrace_line_framed_log_sink(self):
        with NamedTemporaryFile() as temp_file:
            with bootstrap.FramedTelemetryLogSink(
                os.open(temp_file.name, os.O_CREAT | os.O_RDWR)
            ) as log_sink:
                err_to_log = bootstrap.make_error(
                    "Error message", "ErrorType", ["line1", "", "line2"]
                )
                bootstrap.log_error(err_to_log, log_sink)

            expected_logged_error = (
                "[ERROR] ErrorType: Error message\nTraceback "
                "(most recent call last):\nline1\n\nline2"
            )

            with open(temp_file.name, "rb") as f:
                content = f.read()

                frame_type = int.from_bytes(content[:4], "big")
                self.assertEqual(frame_type, 0xA55A0001)

                length = int.from_bytes(content[4:8], "big")
                self.assertEqual(length, len(expected_logged_error))

                actual_message = content[8:].decode()
                self.assertEqual(actual_message, expected_logged_error)

    # Just to ensure we are not logging the requestId from error response, just sending in the response
    def test_log_error_invokeId_line_framed_log_sink(self):
        with NamedTemporaryFile() as temp_file:
            with bootstrap.FramedTelemetryLogSink(temp_file.name) as log_sink:
                err_to_log = bootstrap.make_error(
                    "Error message",
                    "ErrorType",
                    ["line1", "", "line2"],
                    "testrequestId",
                )
                bootstrap.log_error(err_to_log, log_sink)

            expected_logged_error = (
                "[ERROR] ErrorType: Error message\nTraceback "
                "(most recent call last):\nline1\n\nline2"
            )

            with open(temp_file.name, "rb") as f:
                content = f.read()

                frame_type = int.from_bytes(content[:4], "big")
                self.assertEqual(frame_type, 0xA55A0001)

                length = int.from_bytes(content[4:8], "big")
                self.assertEqual(length, len(expected_logged_error))

                actual_message = content[8:].decode()
                self.assertEqual(actual_message, expected_logged_error)


class TestUnbuffered(unittest.TestCase):
    def test_write(self):
        mock_stream = MagicMock()
        unbuffered = bootstrap.Unbuffered(mock_stream)

        unbuffered.write("YOLO!")

        mock_stream.write.assert_called_once_with("YOLO!")
        mock_stream.flush.assert_called_once()

    def test_writelines(self):
        mock_stream = MagicMock()
        unbuffered = bootstrap.Unbuffered(mock_stream)

        unbuffered.writelines(["YOLO!"])

        mock_stream.writelines.assert_called_once_with(["YOLO!"])
        mock_stream.flush.assert_called_once()


class TestLogSink(unittest.TestCase):
    @patch("sys.stdout", new_callable=StringIO)
    def test_create_unbuffered_log_sinks(self, mock_stdout):
        if "_LAMBDA_TELEMETRY_LOG_FD" in os.environ:
            del os.environ["_LAMBDA_TELEMETRY_LOG_FD"]

        actual = bootstrap.create_log_sink()

        self.assertIsInstance(actual, bootstrap.StandardLogSink)
        actual.log("log")
        self.assertEqual(mock_stdout.getvalue(), "log")

    def test_create_framed_telemetry_log_sinks(self):
        fd = 3
        os.environ["_LAMBDA_TELEMETRY_LOG_FD"] = "3"

        actual = bootstrap.create_log_sink()

        self.assertIsInstance(actual, bootstrap.FramedTelemetryLogSink)
        self.assertEqual(actual.fd, fd)
        self.assertFalse("_LAMBDA_TELEMETRY_LOG_FD" in os.environ)

    def test_single_frame(self):
        with NamedTemporaryFile() as temp_file:
            message = "hello world\nsomething on a new line!\n"
            with bootstrap.FramedTelemetryLogSink(
                os.open(temp_file.name, os.O_CREAT | os.O_RDWR)
            ) as ls:
                ls.log(message)
            with open(temp_file.name, "rb") as f:
                content = f.read()

                frame_type = int.from_bytes(content[:4], "big")
                self.assertEqual(frame_type, 0xA55A0001)

                length = int.from_bytes(content[4:8], "big")
                self.assertEqual(length, len(message))

                actual_message = content[8:].decode()
                self.assertEqual(actual_message, message)

    def test_multiple_frame(self):
        with NamedTemporaryFile() as temp_file:
            first_message = "hello world\nsomething on a new line!"
            second_message = "hello again\nhere's another message\n"

            with bootstrap.FramedTelemetryLogSink(
                os.open(temp_file.name, os.O_CREAT | os.O_RDWR)
            ) as ls:
                ls.log(first_message)
                ls.log(second_message)

            with open(temp_file.name, "rb") as f:
                content = f.read()
                pos = 0
                for message in [first_message, second_message]:
                    frame_type = int.from_bytes(content[pos : pos + 4], "big")
                    self.assertEqual(frame_type, 0xA55A0001)
                    pos += 4

                    length = int.from_bytes(content[pos : pos + 4], "big")
                    self.assertEqual(length, len(message))
                    pos += 4

                    actual_message = content[pos : pos + len(message)].decode()
                    self.assertEqual(actual_message, message)
                    pos += len(message)

                self.assertEqual(content[pos:], b"")


class TestBootstrapModule(unittest.TestCase):
    @patch("awslambdaric.bootstrap.handle_event_request")
    @patch("awslambdaric.bootstrap.LambdaRuntimeClient")
    def test_run(self, mock_runtime_client, mock_handle_event_request):
        expected_app_root = "/tmp/test/app_root"
        expected_handler = "app.my_test_handler"
        expected_lambda_runtime_api_addr = "test_addr"

        mock_event_request = MagicMock()
        mock_event_request.x_amzn_trace_id = "123"

        mock_runtime_client.return_value.wait_next_invocation.side_effect = [
            mock_event_request,
            MagicMock(),
        ]

        with self.assertRaises(TypeError):
            bootstrap.run(
                expected_app_root, expected_handler, expected_lambda_runtime_api_addr
            )

        mock_handle_event_request.assert_called_once()

    @patch(
        "awslambdaric.bootstrap.LambdaLoggerHandler",
        Mock(side_effect=Exception("Boom!")),
    )
    @patch("awslambdaric.bootstrap.build_fault_result", MagicMock())
    @patch("awslambdaric.bootstrap.log_error", MagicMock())
    @patch("awslambdaric.bootstrap.LambdaRuntimeClient", MagicMock())
    @patch("awslambdaric.bootstrap.sys")
    def test_run_exception(self, mock_sys):
        class TestException(Exception):
            pass

        expected_app_root = "/tmp/test/app_root"
        expected_handler = "app.my_test_handler"
        expected_lambda_runtime_api_addr = "test_addr"

        mock_sys.exit.side_effect = TestException("Boom!")

        with self.assertRaises(TestException):
            bootstrap.run(
                expected_app_root, expected_handler, expected_lambda_runtime_api_addr
            )

        mock_sys.exit.assert_called_once_with(1)


if __name__ == "__main__":
    unittest.main()
