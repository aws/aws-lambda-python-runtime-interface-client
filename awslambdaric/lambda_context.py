"""
Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import logging
import os
import sys
import time


class LambdaContext(object):
    def __init__(
        self,
        invoke_id,
        client_context,
        cognito_identity,
        epoch_deadline_time_in_ms,
        invoked_function_arn=None,
    ):
        self.aws_request_id = invoke_id
        self.log_group_name = os.environ.get("AWS_LAMBDA_LOG_GROUP_NAME")
        self.log_stream_name = os.environ.get("AWS_LAMBDA_LOG_STREAM_NAME")
        self.function_name = os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
        self.memory_limit_in_mb = os.environ.get("AWS_LAMBDA_FUNCTION_MEMORY_SIZE")
        self.function_version = os.environ.get("AWS_LAMBDA_FUNCTION_VERSION")
        self.invoked_function_arn = invoked_function_arn

        self.client_context = make_obj_from_dict(ClientContext, client_context)
        if self.client_context is not None:
            self.client_context.client = make_obj_from_dict(
                Client, self.client_context.client
            )

        self.identity = make_obj_from_dict(CognitoIdentity, {})
        if cognito_identity is not None:
            self.identity.cognito_identity_id = cognito_identity.get(
                "cognitoIdentityId"
            )
            self.identity.cognito_identity_pool_id = cognito_identity.get(
                "cognitoIdentityPoolId"
            )

        self._epoch_deadline_time_in_ms = epoch_deadline_time_in_ms

    def get_remaining_time_in_millis(self):
        epoch_now_in_ms = int(time.time() * 1000)
        delta_ms = self._epoch_deadline_time_in_ms - epoch_now_in_ms
        return delta_ms if delta_ms > 0 else 0

    def log(self, msg):
        for handler in logging.getLogger().handlers:
            if hasattr(handler, "log_sink"):
                handler.log_sink.log(str(msg))
                return
        sys.stdout.write(str(msg))

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(["
            f"aws_request_id={self.aws_request_id},"
            f"log_group_name={self.log_group_name},"
            f"log_stream_name={self.log_stream_name},"
            f"function_name={self.function_name},"
            f"memory_limit_in_mb={self.memory_limit_in_mb},"
            f"function_version={self.function_version},"
            f"invoked_function_arn={self.invoked_function_arn},"
            f"client_context={self.client_context},"
            f"identity={self.identity}"
            "])"
        )


class CognitoIdentity(object):
    __slots__ = ["cognito_identity_id", "cognito_identity_pool_id"]

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(["
            f"cognito_identity_id={self.cognito_identity_id},"
            f"cognito_identity_pool_id={self.cognito_identity_pool_id}"
            "])"
        )


class Client(object):
    __slots__ = [
        "installation_id",
        "app_title",
        "app_version_name",
        "app_version_code",
        "app_package_name",
    ]

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(["
            f"installation_id={self.installation_id},"
            f"app_title={self.app_title},"
            f"app_version_name={self.app_version_name},"
            f"app_version_code={self.app_version_code},"
            f"app_package_name={self.app_package_name}"
            "])"
        )


class ClientContext(object):
    __slots__ = ["custom", "env", "client"]

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(["
            f"custom={self.custom},"
            f"env={self.env},"
            f"client={self.client}"
            "])"
        )


def make_obj_from_dict(_class, _dict, fields=None):
    if _dict is None:
        return None
    obj = _class()
    set_obj_from_dict(obj, _dict)
    return obj


def set_obj_from_dict(obj, _dict, fields=None):
    if fields is None:
        fields = obj.__class__.__slots__
    for field in fields:
        setattr(obj, field, _dict.get(field, None))
