"""
Copyright 2026 Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import http.server
import json
import os
import subprocess
import sys
import threading
import unittest

INVOCATION_ID_HEADER = "Lambda-Runtime-Invocation-Id"
REQUEST_ID = "request-id-1"

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT_PROBE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "invocation_id_probe.py"
)


class StubRapidHandler(http.server.BaseHTTPRequestHandler):
    """Minimal stand-in for the RAPID /next, /response and /error endpoints.

    Each request's raw header block is appended to the server's `received` list
    so that tests can assert on what actually went over the wire rather than on
    what the Python layer believed it was sending.
    """

    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        pass  # keep the test output clean

    def _record(self):
        self.server.received.append((self.path, self.headers))

    def do_GET(self):
        self._record()
        body = b"{}"
        self.send_response(200)
        self.send_header("Lambda-Runtime-Aws-Request-Id", REQUEST_ID)
        self.send_header("Lambda-Runtime-Invoked-Function-Arn", "arn:aws:lambda:::f")
        self.send_header("Lambda-Runtime-Deadline-Ms", "1735689600000")
        self.send_header("Content-Type", "application/json")
        if self.server.invocation_id is not None:
            self.send_header(INVOCATION_ID_HEADER, self.server.invocation_id)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        self._record()
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)
        self.send_response(202)
        self.send_header("Content-Length", "0")
        self.end_headers()


class StubRapid(http.server.ThreadingHTTPServer):

    def __init__(self):
        super().__init__(("127.0.0.1", 0), StubRapidHandler)
        self.invocation_id = None
        self.received = []

    @property
    def endpoint(self):
        return "{}:{}".format(*self.server_address)


class TestInvocationIdOnTheWire(unittest.TestCase):
    """End-to-end coverage of the Lambda-Runtime-Invocation-Id echo.

    These tests drive the compiled extension against a real socket, so they
    cover the header-emitting C++ code in aws-lambda-cpp that the mocked unit
    tests in test_lambda_runtime_client.py cannot reach. If
    aws-lambda-cpp-add-invocation-id.patch is ever dropped from the vendored
    tarball, these are the tests that fail.
    """

    def _run_client(self, invocation_id, mode="response"):
        """Serve one invocation to a real client and return its POST headers."""
        server = StubRapid()
        server.invocation_id = invocation_id
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 5)
        self.addCleanup(server.shutdown)
        self.addCleanup(server.server_close)

        env = dict(
            os.environ,
            AWS_LAMBDA_RUNTIME_API=server.endpoint,
            PYTHONPATH=os.pathsep.join(
                [REPO_ROOT]
                + ([os.environ["PYTHONPATH"]] if os.environ.get("PYTHONPATH") else [])
            ),
        )
        completed = subprocess.run(
            [sys.executable, CLIENT_PROBE, mode],
            env=env,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(
            0,
            completed.returncode,
            f"client failed:\nstdout={completed.stdout}\nstderr={completed.stderr}",
        )

        posted = [h for path, h in server.received if path.endswith("/" + mode)]
        self.assertEqual(1, len(posted), f"expected exactly one POST to /{mode}")
        return json.loads(completed.stdout), posted[0]

    def test_invocation_id_is_echoed_on_response(self):
        seen, posted = self._run_client("inv-uuid-round-trip")

        self.assertEqual("inv-uuid-round-trip", seen["next_invocation_id"])
        # get_all, not get: a duplicated header must be visible, not normalized.
        self.assertEqual(["inv-uuid-round-trip"], posted.get_all(INVOCATION_ID_HEADER))

    def test_invocation_id_is_echoed_on_error(self):
        seen, posted = self._run_client("inv-uuid-error-path", mode="error")

        self.assertEqual("inv-uuid-error-path", seen["next_invocation_id"])
        self.assertEqual(["inv-uuid-error-path"], posted.get_all(INVOCATION_ID_HEADER))

    def test_no_header_is_sent_when_rapid_did_not_send_one(self):
        seen, posted = self._run_client(None)

        self.assertIsNone(seen["next_invocation_id"])
        self.assertIsNone(posted.get_all(INVOCATION_ID_HEADER))


if __name__ == "__main__":
    unittest.main()
