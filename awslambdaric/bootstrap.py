"""
Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import importlib
import json
import logging
import os
import sys
import time
import traceback

from .lambda_context import LambdaContext
from .lambda_runtime_client import LambdaRuntimeClient
from .lambda_runtime_exception import FaultException
from .lambda_runtime_marshaller import to_json

ERROR_LOG_LINE_TERMINATE = "\r"
ERROR_LOG_IDENT = "\u00a0"  # NO-BREAK SPACE U+00A0


def _get_handler(handler):
    try:
        (modname, fname) = handler.rsplit(".", 1)
    except ValueError as e:
        fault = FaultException(
            FaultException.MALFORMED_HANDLER_NAME,
            "Bad handler '{}': {}".format(handler, str(e)),
        )
        return make_fault_handler(fault)

    try:
        if modname.split(".")[0] in sys.builtin_module_names:
            fault = FaultException(
                FaultException.BUILT_IN_MODULE_CONFLICT,
                "Cannot use built-in module {} as a handler module".format(modname),
            )
            return make_fault_handler(fault)
        m = importlib.import_module(modname)
    except ImportError as e:
        fault = FaultException(
            FaultException.IMPORT_MODULE_ERROR,
            "Unable to import module '{}': {}".format(modname, str(e)),
        )
        request_handler = make_fault_handler(fault)
        return request_handler
    except SyntaxError as e:
        trace = ['  File "%s" Line %s\n    %s' % (e.filename, e.lineno, e.text)]
        fault = FaultException(
            FaultException.USER_CODE_SYNTAX_ERROR,
            "Syntax error in module '{}': {}".format(modname, str(e)),
            trace,
        )
        request_handler = make_fault_handler(fault)
        return request_handler

    try:
        request_handler = getattr(m, fname)
    except AttributeError:
        fault = FaultException(
            FaultException.HANDLER_NOT_FOUND,
            "Handler '{}' missing on module '{}'".format(fname, modname),
            None,
        )
        request_handler = make_fault_handler(fault)
    return request_handler


def make_fault_handler(fault):
    def result(*args):
        raise fault

    return result


def make_error(error_message, error_type, stack_trace):
    result = {
        "errorMessage": error_message if error_message else "",
        "errorType": error_type if error_type else "",
        "stackTrace": stack_trace if stack_trace else [],
    }
    return result


def replace_line_indentation(line, indent_char, new_indent_char):
    ident_chars_count = 0
    for c in line:
        if c != indent_char:
            break
        ident_chars_count += 1
    return (new_indent_char * ident_chars_count) + line[ident_chars_count:]


def log_error(error_result, log_sink):
    error_description = "[ERROR]"

    error_result_type = error_result.get("errorType")
    if error_result_type:
        error_description += " " + error_result_type

    error_result_message = error_result.get("errorMessage")
    if error_result_message:
        if error_result_type:
            error_description += ":"
        error_description += " " + error_result_message

    error_message_lines = [error_description]

    stack_trace = error_result.get("stackTrace")
    if stack_trace is not None:
        error_message_lines += ["Traceback (most recent call last):"]
        for trace_element in stack_trace:
            if trace_element == "":
                error_message_lines += [""]
            else:
                for trace_line in trace_element.splitlines():
                    error_message_lines += [
                        replace_line_indentation(trace_line, " ", ERROR_LOG_IDENT)
                    ]

    log_sink.log_error(error_message_lines)


def handle_event_request(
    lambda_runtime_client,
    request_handler,
    invoke_id,
    event_body,
    content_type,
    client_context_json,
    cognito_identity_json,
    invoked_function_arn,
    epoch_deadline_time_in_ms,
    log_sink,
):
    error_result = None
    try:
        lambda_context = create_lambda_context(
            client_context_json,
            cognito_identity_json,
            epoch_deadline_time_in_ms,
            invoke_id,
            invoked_function_arn,
        )
        event = lambda_runtime_client.marshaller.unmarshal_request(
            event_body, content_type
        )
        response = request_handler(event, lambda_context)
        result, result_content_type = lambda_runtime_client.marshaller.marshal_response(
            response
        )
    except FaultException as e:
        xray_fault = make_xray_fault("LambdaValidationError", e.msg, os.getcwd(), [])
        error_result = make_error(e.msg, e.exception_type, e.trace)

    except Exception:
        etype, value, tb = sys.exc_info()
        tb_tuples = extract_traceback(tb)
        for i in range(len(tb_tuples)):
            if "/bootstrap.py" not in tb_tuples[i][0]:  # filename of the tb tuple
                tb_tuples = tb_tuples[i:]
                break

        xray_fault = make_xray_fault(etype.__name__, str(value), os.getcwd(), tb_tuples)
        error_result = make_error(
            str(value), etype.__name__, traceback.format_list(tb_tuples)
        )

    if error_result is not None:
        log_error(error_result, log_sink)
        lambda_runtime_client.post_invocation_error(
            invoke_id, to_json(error_result), to_json(xray_fault)
        )
    else:
        lambda_runtime_client.post_invocation_result(
            invoke_id, result, result_content_type
        )


def parse_json_header(header, name):
    try:
        return json.loads(header)
    except Exception as e:
        raise FaultException(
            FaultException.LAMBDA_CONTEXT_UNMARSHAL_ERROR,
            "Unable to parse {} JSON: {}".format(name, str(e)),
            None,
        )


def create_lambda_context(
    client_context_json,
    cognito_identity_json,
    epoch_deadline_time_in_ms,
    invoke_id,
    invoked_function_arn,
):
    client_context = None
    if client_context_json:
        client_context = parse_json_header(client_context_json, "Client Context")
    cognito_identity = None
    if cognito_identity_json:
        cognito_identity = parse_json_header(cognito_identity_json, "Cognito Identity")

    return LambdaContext(
        invoke_id,
        client_context,
        cognito_identity,
        epoch_deadline_time_in_ms,
        invoked_function_arn,
    )


def build_fault_result(exc_info, msg):
    etype, value, tb = exc_info
    tb_tuples = extract_traceback(tb)
    for i in range(len(tb_tuples)):
        if "/bootstrap.py" not in tb_tuples[i][0]:  # filename of the tb tuple
            tb_tuples = tb_tuples[i:]
            break

    return make_error(
        msg if msg else str(value), etype.__name__, traceback.format_list(tb_tuples)
    )


def make_xray_fault(ex_type, ex_msg, working_dir, tb_tuples):
    stack = []
    files = set()
    for t in tb_tuples:
        tb_file, tb_line, tb_method, tb_code = t
        tb_xray = {"label": tb_method, "path": tb_file, "line": tb_line}
        stack.append(tb_xray)
        files.add(tb_file)

    formatted_ex = {"message": ex_msg, "type": ex_type, "stack": stack}
    xray_fault = {
        "working_directory": working_dir,
        "exceptions": [formatted_ex],
        "paths": list(files),
    }
    return xray_fault


def extract_traceback(tb):
    return [
        (frame.filename, frame.lineno, frame.name, frame.line)
        for frame in traceback.extract_tb(tb)
    ]


class LambdaLoggerHandler(logging.Handler):
    def __init__(self, log_sink):
        logging.Handler.__init__(self)
        self.log_sink = log_sink

    def emit(self, record):
        msg = self.format(record)
        self.log_sink.log(msg)


class LambdaLoggerFilter(logging.Filter):
    def filter(self, record):
        record.aws_request_id = _GLOBAL_AWS_REQUEST_ID or ""
        return True


class Unbuffered(object):
    def __init__(self, stream):
        self.stream = stream

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        pass

    def __getattr__(self, attr):
        return getattr(self.stream, attr)

    def write(self, msg):
        self.stream.write(msg)
        self.stream.flush()

    def writelines(self, msgs):
        self.stream.writelines(msgs)
        self.stream.flush()


class StandardLogSink(object):
    def __init__(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        pass

    def log(self, msg):
        sys.stdout.write(msg)

    def log_error(self, message_lines):
        error_message = ERROR_LOG_LINE_TERMINATE.join(message_lines) + "\n"
        sys.stdout.write(error_message)


class FramedTelemetryLogSink(object):
    """
    FramedTelemetryLogSink implements the logging contract between runtimes and the platform. It implements a simple
    framing protocol so message boundaries can be determined. Each frame can be visualized as follows:
     <pre>
    {@code
    +----------------------+------------------------+-----------------------+
    | Frame Type - 4 bytes | Length (len) - 4 bytes | Message - 'len' bytes |
    +----------------------+------------------------+-----------------------+
    }
    </pre>
    The first 4 bytes indicate the type of the frame - log frames have a type defined as the hex value 0xa55a0001. The
    second 4 bytes should indicate the message's length. The next 'len' bytes contain the message. The byte order is
    big-endian.
    """

    def __init__(self, filename):
        self.filename = filename
        self.frame_type = 0xA55A0001 .to_bytes(4, "big")

    def __enter__(self):
        self.file = open(self.filename, "wb", 0)
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.file.close()

    def log(self, msg):
        encoded_msg = msg.encode("utf8")
        log_msg = self.frame_type + len(encoded_msg).to_bytes(4, "big") + encoded_msg
        self.file.write(log_msg)

    def log_error(self, message_lines):
        error_message = "\n".join(message_lines)
        self.log(error_message)


def update_xray_env_variable(xray_trace_id):
    if xray_trace_id is not None:
        os.environ["_X_AMZN_TRACE_ID"] = xray_trace_id
    else:
        if "_X_AMZN_TRACE_ID" in os.environ:
            del os.environ["_X_AMZN_TRACE_ID"]


def create_log_sink():
    if "_LAMBDA_TELEMETRY_LOG_FD" in os.environ:
        fd = os.environ["_LAMBDA_TELEMETRY_LOG_FD"]
        del os.environ["_LAMBDA_TELEMETRY_LOG_FD"]
        return FramedTelemetryLogSink("/proc/self/fd/" + fd)

    else:
        return StandardLogSink()


_GLOBAL_AWS_REQUEST_ID = None


def run(app_root, handler, lambda_runtime_api_addr):
    sys.stdout = Unbuffered(sys.stdout)
    sys.stderr = Unbuffered(sys.stderr)

    with create_log_sink() as log_sink:
        lambda_runtime_client = LambdaRuntimeClient(lambda_runtime_api_addr)

        try:
            logging.Formatter.converter = time.gmtime
            logger = logging.getLogger()
            logger_handler = LambdaLoggerHandler(log_sink)
            logger_handler.setFormatter(
                logging.Formatter(
                    "[%(levelname)s]\t%(asctime)s.%(msecs)dZ\t%(aws_request_id)s\t%(message)s\n",
                    "%Y-%m-%dT%H:%M:%S",
                )
            )
            logger_handler.addFilter(LambdaLoggerFilter())
            logger.addHandler(logger_handler)

            global _GLOBAL_AWS_REQUEST_ID

            request_handler = _get_handler(handler)
        except Exception:
            error_result = build_fault_result(sys.exc_info(), None)

            log_error(error_result, log_sink)
            lambda_runtime_client.post_init_error(to_json(error_result))

            sys.exit(1)

        while True:
            event_request = lambda_runtime_client.wait_next_invocation()

            _GLOBAL_AWS_REQUEST_ID = event_request.invoke_id

            update_xray_env_variable(event_request.x_amzn_trace_id)

            handle_event_request(
                lambda_runtime_client,
                request_handler,
                event_request.invoke_id,
                event_request.event_body,
                event_request.content_type,
                event_request.client_context,
                event_request.cognito_identity,
                event_request.invoked_function_arn,
                event_request.deadline_time_in_ms,
                log_sink,
            )
