"""
Copyright 2026 Amazon.com, Inc. or its affiliates. All Rights Reserved.

Client half of test_runtime_client_headers.py, run as a subprocess.

It is a separate process rather than a thread because the native
post_invocation_result/post_error entry points hold the GIL for the duration of
the blocking curl call so an in-process stub server thread could never be scheduled to answer the POST.
"""

import json
import sys

import runtime_client

INVOCATION_ID_HEADER = "Lambda-Runtime-Invocation-Id"
REQUEST_ID_HEADER = "Lambda-Runtime-Aws-Request-Id"


def main(mode):
    runtime_client.initialize_client("test-agent")

    _, headers = runtime_client.next()
    invocation_id = headers[INVOCATION_ID_HEADER]

    # Thread the invocation id straight back, exactly as bootstrap does. Passing
    # it through untouched is what makes the POST assertions meaningful.
    if mode == "response":
        runtime_client.post_invocation_result(
            headers[REQUEST_ID_HEADER],
            b'{"ok": true}',
            "application/json",
            invocation_id,
        )
    elif mode == "error":
        runtime_client.post_error(
            headers[REQUEST_ID_HEADER],
            '{"errorMessage": "boom"}',
            "{}",
            invocation_id,
        )
    else:
        raise SystemExit(f"unknown mode: {mode!r}")

    print(json.dumps({"next_invocation_id": invocation_id}))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
