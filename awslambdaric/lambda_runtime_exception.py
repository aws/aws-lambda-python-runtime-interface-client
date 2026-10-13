"""
Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""


class FaultException(Exception):
    MARSHAL_ERROR = "Runtime.MarshalError"
    UNMARSHAL_ERROR = "Runtime.UnmarshalError"
    USER_CODE_SYNTAX_ERROR = "Runtime.UserCodeSyntaxError"
    HANDLER_NOT_FOUND = "Runtime.HandlerNotFound"
    IMPORT_MODULE_ERROR = "Runtime.ImportModuleError"
    BUILT_IN_MODULE_CONFLICT = "Runtime.BuiltInModuleConflict"
    MALFORMED_HANDLER_NAME = "Runtime.MalformedHandlerName"
    BEFORE_SNAPSHOT_ERROR = "Runtime.BeforeSnapshotError"
    AFTER_RESTORE_ERROR = "Runtime.AfterRestoreError"
    LAMBDA_CONTEXT_UNMARSHAL_ERROR = "Runtime.LambdaContextUnmarshalError"
    LAMBDA_RUNTIME_CLIENT_ERROR = "Runtime.LambdaRuntimeClientError"

    def __init__(self, exception_type, msg, trace=None):
        self.msg = msg
        self.exception_type = exception_type
        self.trace = trace
