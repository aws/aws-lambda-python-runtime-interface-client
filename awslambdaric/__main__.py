"""
Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import sys

from .lambda_config import LambdaConfigProvider
from .lambda_runtime_client import LambdaRuntimeClient
from .lambda_multi_concurrent_utils import MultiConcurrentRunner
from . import bootstrap


def main(args):
    config = LambdaConfigProvider(args)
    handler = config.handler
    api_addr = config.api_address
    use_thread = config.use_thread_polling

    if config.is_multi_concurrent:
        # Multi-concurrent mode: redirect fork, stdout/stderr and run
        max_conc = int(config.max_concurrency)
        socket_path = config.lmi_socket_path
        MultiConcurrentRunner.run_concurrent(
            handler, api_addr, use_thread, socket_path, max_conc
        )
    else:
        # Standard Lambda mode: single call
        client = LambdaRuntimeClient(api_addr, use_thread)
        bootstrap.run(handler, client)


if __name__ == "__main__":
    main(sys.argv)
