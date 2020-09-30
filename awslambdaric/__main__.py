"""
Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import os
import sys

from . import bootstrap


def main(args):
    app_root = os.getcwd()
    handler = args[1]
    lambda_runtime_api_addr = os.environ["AWS_LAMBDA_RUNTIME_API"]

    print(f"Executing '{handler}' in function directory '{app_root}'")
    bootstrap.run(app_root, handler, lambda_runtime_api_addr)


if __name__ == "__main__":
    main(sys.argv)
