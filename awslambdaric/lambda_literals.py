"""
Copyright 2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

lambda_warning = "LAMBDA_WARNING"

_PREVIEW_DOC_LINK = "https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html"
_PREVIEW_DOC_LINK_CN = "https://docs.amazonaws.cn/lambda/latest/dg/lambda-runtimes.html"


def _get_preview_doc_link():
    import os

    region = os.environ.get("AWS_REGION", "")
    if region.startswith("cn-"):
        return _PREVIEW_DOC_LINK_CN
    return _PREVIEW_DOC_LINK


# Holds warning message that is emitted when the runtime is a preview version.
def get_lambda_preview_runtime_warning_message():
    return str(
        f"{lambda_warning}: "
        "This is a preview runtime version and should not be used for production workloads. "
        "For further information and to provide feedback, see "
        f"{_get_preview_doc_link()}\r"
    )


# Holds warning message that is emitted when an unhandled exception is raised during function invocation.
lambda_unhandled_exception_warning_message = str(
    f"{lambda_warning}: "
    "Unhandled exception. "
    "The most likely cause is an issue in the function code. "
    "However, in rare cases, a Lambda runtime update can cause unexpected function behavior. "
    "For functions using managed runtimes, runtime updates can be triggered by a function change, or can be applied automatically. "
    "To determine if the runtime has been updated, check the runtime version in the INIT_START log entry. "
    "If this error correlates with a change in the runtime version, you may be able to mitigate this error by temporarily rolling back to the previous runtime version. "
    "For more information, see https://docs.aws.amazon.com/lambda/latest/dg/runtimes-update.html\r"
)
