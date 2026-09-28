# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from typing import Any, Callable

# The customer-facing name lives only here: the runner consumes get_pre_fork(),
# so a later rename is one line plus a backwards-compatible alias.
__all__ = ["register_pre_fork"]

_pre_fork_registry: list[tuple[Callable[..., Any], tuple, dict]] = []


def register_pre_fork(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Register a function to run once in the parent, before workers are forked.

    Runs for any worker count, so a hook's side effects are in place whatever
    concurrency the execution environment is configured with.

        from awslambdaric.lambda_concurrency_hooks import register_pre_fork

        @register_pre_fork
        def start_inference_server():
            subprocess.Popen(["python", "serve.py", "--port", "8000"])
    """
    _pre_fork_registry.append((func, (), {}))
    return func


def get_pre_fork() -> list[tuple[Callable[..., Any], tuple, dict]]:
    return _pre_fork_registry
