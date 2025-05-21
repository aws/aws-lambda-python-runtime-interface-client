"""
Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from awslambdaric.lambda_context import LambdaContext


class TestLambdaContext(unittest.TestCase):
    def setUp(self):
        self.org_os_environ = os.environ

    def tearDown(self):
        os.environ = self.org_os_environ

    def test_init(self):
        os.environ = {
            "AWS_LAMBDA_LOG_GROUP_NAME": "log-group-name1",
            "AWS_LAMBDA_LOG_STREAM_NAME": "log-stream-name1",
            "AWS_LAMBDA_FUNCTION_NAME": "function-name1",
            "AWS_LAMBDA_FUNCTION_MEMORY_SIZE": "1234",
            "AWS_LAMBDA_FUNCTION_VERSION": "version1",
        }
        client_context = {"client": {}}
        cognito_identity = {}

        context = LambdaContext(
            "invoke-id1", client_context, cognito_identity, 1415836801000, "arn:test1"
        )
        self.assertEqual(context.aws_request_id, "invoke-id1")
        self.assertEqual(context.log_group_name, "log-group-name1")
        self.assertEqual(context.log_stream_name, "log-stream-name1")
        self.assertEqual(context.function_name, "function-name1")
        self.assertEqual(context.memory_limit_in_mb, "1234")
        self.assertEqual(context.function_version, "version1")
        self.assertEqual(context.invoked_function_arn, "arn:test1")
        self.assertEqual(context.tenant_id, None)
        self.assertEqual(context.identity.cognito_identity_id, None)
        self.assertEqual(context.identity.cognito_identity_pool_id, None)
        self.assertEqual(context.client_context.client.installation_id, None)
        self.assertEqual(context.client_context.client.app_title, None)
        self.assertEqual(context.client_context.client.app_version_name, None)
        self.assertEqual(context.client_context.client.app_version_code, None)
        self.assertEqual(context.client_context.client.app_package_name, None)
        self.assertEqual(context.client_context.custom, None)
        self.assertEqual(context.client_context.env, None)

    def test_init_empty_env(self):
        client_context = {}
        cognito_identity = {}
        context = LambdaContext(
            "invoke-id1", client_context, cognito_identity, 1415836801000, "arn:test"
        )

        self.assertEqual(context.log_group_name, None)
        self.assertEqual(context.log_stream_name, None)
        self.assertEqual(context.function_name, None)
        self.assertEqual(context.memory_limit_in_mb, None)
        self.assertEqual(context.function_version, None)
        self.assertEqual(context.client_context.client, None)

    def test_init_cognito(self):
        client_context = {}
        cognito_identity = {
            "cognitoIdentityId": "id1",
            "cognitoIdentityPoolId": "poolid1",
        }
        context = LambdaContext(
            "invoke-id1", client_context, cognito_identity, 1415836801000, "arn:test"
        )

        self.assertEqual(context.identity.cognito_identity_id, "id1")
        self.assertEqual(context.identity.cognito_identity_pool_id, "poolid1")

    def test_init_tenant_id(self):
        client_context = {}
        cognito_identity = {}
        tenant_id = "blue"

        context = LambdaContext(
            "invoke-id1",
            client_context,
            cognito_identity,
            1415836801000,
            "arn:test",
            tenant_id,
        )
        self.assertEqual(context.tenant_id, "blue")

    def test_init_client_context(self):
        client_context = {
            "client": {
                "installation_id": "installid1",
                "app_title": "title1",
                "app_version_name": "name1",
                "app_version_code": "versioncode1",
                "app_package_name": "package1",
            },
            "custom": {"custom-key": "custom-value"},
            "env": {"custom-env": "custom-value"},
        }
        cognito_identity = {}

        context = LambdaContext(
            "invoke-id1", client_context, cognito_identity, 1415836801000, "arn:test"
        )

        self.assertEqual(context.client_context.client.installation_id, "installid1")
        self.assertEqual(context.client_context.client.app_title, "title1")
        self.assertEqual(context.client_context.client.app_version_name, "name1")
        self.assertEqual(context.client_context.client.app_version_code, "versioncode1")
        self.assertEqual(context.client_context.client.app_package_name, "package1")

    @patch("time.time")
    def test_get_remaining_time_in_millis(self, mock_time):
        deadline_epoch_ms = 1415836801003
        mock_time.return_value = (deadline_epoch_ms - 3000) / 1000

        context = LambdaContext("", {}, {}, deadline_epoch_ms, "")
        remaining_time_in_millis = context.get_remaining_time_in_millis()
        self.assertEqual(remaining_time_in_millis, 3000)

    @patch("time.time")
    def test_get_remaining_time_in_millis_not_less_then_zero(self, mock_time):
        deadline_epoch_ms = 1415836801000
        mock_time.return_value = (deadline_epoch_ms + 9000) / 1000

        context = LambdaContext("", {}, {}, deadline_epoch_ms, "")
        remaining_time_in_millis = context.get_remaining_time_in_millis()
        self.assertEqual(remaining_time_in_millis, 0)

    @patch("awslambdaric.lambda_context.logging")
    def test_log(self, mock_logging):
        mock_log_sink = MagicMock()

        mock_handler = MagicMock()
        mock_handler.log_sink = mock_log_sink

        mock_logger = MagicMock()
        mock_logger.handlers = [mock_handler]

        mock_logging.getLogger.return_value = mock_logger

        context = LambdaContext("", {}, {}, 12345678, "")

        context.log("YOLO!")
        mock_logging.getLogger.assert_called_once()

        mock_log_sink.log.assert_called_once_with("YOLO!")

    @patch("awslambdaric.lambda_context.logging", MagicMock())
    @patch("awslambdaric.bootstrap.sys")
    def test_log_without_handlers(self, mock_sys):
        context = LambdaContext("", {}, {}, 12345678, "")

        context.log("YOLO!")

        mock_sys.stdout.write("YOLO!")
