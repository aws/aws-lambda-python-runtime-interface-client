/* Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved. */

#include <Python.h>
#include <aws/lambda-runtime/runtime.h>
#include <aws/lambda-runtime/version.h>
#include <chrono>

#define NULL_IF_EMPTY(v) (((v) == NULL || (v)[0] == 0) ? NULL : (v))

static const std::string ENDPOINT(getenv("AWS_LAMBDA_RUNTIME_API") ? getenv("AWS_LAMBDA_RUNTIME_API") : "127.0.0.1:9001");
static aws::lambda_runtime::runtime *CLIENT;

static PyObject *method_initialize_client(PyObject *self, PyObject *args) {
    char *user_agent_arg;
    if (!PyArg_ParseTuple(args, "s", &user_agent_arg)) {
        PyErr_SetString(PyExc_RuntimeError, "Wrong arguments");
        return NULL;
    }

    const std::string user_agent = std::string(user_agent_arg);

    CLIENT = new aws::lambda_runtime::runtime(ENDPOINT, user_agent);
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *method_next(PyObject *self) {
    aws::lambda_runtime::invocation_request response;

    // Release GIL and save thread state
    // ref: https://docs.python.org/3/c-api/init.html#thread-state-and-the-global-interpreter-lock
    PyThreadState *_save;
    _save = PyEval_SaveThread();

    auto outcome = CLIENT->get_next();
    if (!outcome.is_success()) {
        // Reacquire GIL before exiting
        PyEval_RestoreThread(_save);
        PyErr_SetString(PyExc_RuntimeError, "Failed to get next");
        return NULL;
    }

    response = outcome.get_result();
    // Reacquire GIL before constructing return object
    PyEval_RestoreThread(_save);

    auto payload = response.payload;
    auto request_id = response.request_id.c_str();
    auto trace_id = response.xray_trace_id.c_str();
    auto function_arn = response.function_arn.c_str();
    auto deadline = std::chrono::duration_cast<std::chrono::milliseconds>(response.deadline.time_since_epoch()).count();
    auto client_context = response.client_context.c_str();
    auto content_type = response.content_type.c_str();
    auto cognito_id = response.cognito_identity.c_str();

    PyObject *payload_bytes = PyBytes_FromStringAndSize(payload.c_str(), payload.length());
    PyObject *result = Py_BuildValue("(O,{s:s,s:s,s:s,s:l,s:s,s:s,s:s})",
                         payload_bytes,  //Py_BuildValue() increments reference counter
                         "Lambda-Runtime-Aws-Request-Id", request_id,
                         "Lambda-Runtime-Trace-Id", NULL_IF_EMPTY(trace_id),
                         "Lambda-Runtime-Invoked-Function-Arn", function_arn,
                         "Lambda-Runtime-Deadline-Ms", deadline,
                         "Lambda-Runtime-Client-Context", NULL_IF_EMPTY(client_context),
                         "Content-Type", NULL_IF_EMPTY(content_type),
                         "Lambda-Runtime-Cognito-Identity", NULL_IF_EMPTY(cognito_id)
    );

    Py_XDECREF(payload_bytes);
    return result;
}

static PyObject *method_post_invocation_result(PyObject *self, PyObject *args) {
    if (CLIENT == nullptr) {
        PyErr_SetString(PyExc_RuntimeError, "Client not yet initalized");
        return NULL;
    }

    PyObject *invocation_response;
    Py_ssize_t length;
    char *request_id, *content_type, *response_as_c_string;

    if (!PyArg_ParseTuple(args, "sSs", &request_id, &invocation_response, &content_type)) {
        PyErr_SetString(PyExc_RuntimeError, "Wrong arguments");
        return NULL;
    }

    length = PyBytes_Size(invocation_response);
    response_as_c_string = PyBytes_AsString(invocation_response);
    std::string response_string(response_as_c_string, response_as_c_string + length);

    auto response = aws::lambda_runtime::invocation_response::success(response_string, content_type);
    auto outcome = CLIENT->post_success(request_id, response);
    if (!outcome.is_success()) {
        PyErr_SetString(PyExc_RuntimeError, "Failed to post invocation response");
        return NULL;
    }

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *method_post_error(PyObject *self, PyObject *args) {
    if (CLIENT == nullptr) {
        PyErr_SetString(PyExc_RuntimeError, "Client not yet initalized");
        return NULL;
    }

    char *request_id, *response_string, *xray_fault;

    if (!PyArg_ParseTuple(args, "sss", &request_id, &response_string, &xray_fault)) {
        PyErr_SetString(PyExc_RuntimeError, "Wrong arguments");
        return NULL;
    }

    auto response = aws::lambda_runtime::invocation_response(response_string, "application/json", false, xray_fault);
    auto outcome = CLIENT->post_failure(request_id, response);
    if (!outcome.is_success()) {
        PyErr_SetString(PyExc_RuntimeError, "Failed to post invocation error");
        return NULL;
    }

    Py_INCREF(Py_None);
    return Py_None;
}

static PyMethodDef Runtime_Methods[] = {
        {"initialize_client",      method_initialize_client,      METH_VARARGS, NULL},
        {"next",                   (PyCFunction) method_next,     METH_NOARGS,  NULL},
        {"post_invocation_result", method_post_invocation_result, METH_VARARGS, NULL},
        {"post_error",             method_post_error,             METH_VARARGS, NULL},
        {NULL,                     NULL,                          0,            NULL}
};

static struct PyModuleDef runtime_client = {
        PyModuleDef_HEAD_INIT,
        "runtime",
        NULL,
        -1,
        Runtime_Methods,
        NULL,
        NULL,
        NULL,
        NULL
};

PyMODINIT_FUNC PyInit_runtime_client(void) {
    return PyModule_Create(&runtime_client);
}
