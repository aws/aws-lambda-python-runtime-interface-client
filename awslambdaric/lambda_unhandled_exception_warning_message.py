"""
Copyright 2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.
Holds warning message that is emitted when an unhandled exception is raised during function invocation.
"""
lambda_unhandled_exception_warning_message_warning_type = "LAMBDA_WARNING"
lambda_unhandled_exception_warning_message = "Unhandled exception. The most likely cause is an issue in the function code. However, in rare cases, a Lambda runtime update can cause unexpected function behavior. For functions using managed runtimes, runtime updates can be triggered by a function change, or can be applied automatically. To determine if the runtime has been updated, check the runtime version in the INIT_START log entry. If this error correlates with a change in the runtime version, you may be able to mitigate this error by temporarily rolling back to the previous runtime version. For more information, see https://docs.aws.amazon.com/lambda/latest/dg/runtimes-update.html"
lambda_unhandled_exception_warning_test_message = "[WARNING] " + lambda_unhandled_exception_warning_message_warning_type+ ": " + lambda_unhandled_exception_warning_message + "\n"
