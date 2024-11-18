# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from snapshot_restore_py import get_before_snapshot, get_after_restore


def run_before_snapshot():
    before_snapshot_callables = get_before_snapshot()
    while before_snapshot_callables:
        # Using pop as before checkpoint callables are executed in the reverse order of their registration
        func, args, kwargs = before_snapshot_callables.pop()
        func(*args, **kwargs)


def run_after_restore():
    after_restore_callables = get_after_restore()
    for func, args, kwargs in after_restore_callables:
        func(*args, **kwargs)
