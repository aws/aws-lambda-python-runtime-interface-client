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
    LAMBDA_CONTEXT_UNMARSHAL_ERROR = "Runtime.LambdaContextUnmarshalError"

    def __init__(self, exception_type, msg, trace=None):
        self.msg = msg
        self.exception_type = exception_type
        self.trace = trace
