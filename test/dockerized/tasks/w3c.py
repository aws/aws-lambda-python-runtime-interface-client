# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

def _serialize_client_context(client_context):
    if client_context is None:
        return None
    result = {}
    for field in ("custom", "env"):
        value = getattr(client_context, field, None)
        if value is not None:
            result[field] = value
    return result

def get_w3c(event, context):
    return context.w3c()

def get_w3c_and_source(event, context):
    client_context = context.client_context
    return {
        "w3c": context.w3c(),
        "clientContextIsDefined": client_context is not None,
        "clientContextHasW3c": client_context is not None
        and hasattr(client_context, "w3c"),
        "clientContext": _serialize_client_context(client_context),
    }

def echo_client_context(event, context):
    return _serialize_client_context(context.client_context)

def w3c_is_callable(event, context):
    return {"isCallable": callable(getattr(context, "w3c", None))}
