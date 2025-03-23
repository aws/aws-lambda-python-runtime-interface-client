"""
Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import decimal
import math
import os
import json

from .lambda_runtime_exception import FaultException


# We force a serialization of a Decimal's string as raw instead of wrapped by quotes
# by mocking a float, and overriding the __repr__ method to return the string
class DecimalStr(float):
    def __init__(self, value: decimal.Decimal):
        self._value = value
    def __repr__(self):
        return str(self._value)

class Encoder(json.JSONEncoder):
    def __init__(self):
        if os.environ.get("AWS_EXECUTION_ENV") in {
            "AWS_Lambda_python3.12",
            "AWS_Lambda_python3.13",
        }:
            # We also set 'ensure_ascii=False' so that the encoded json contains unicode characters instead of unicode escape sequences
            super().__init__(ensure_ascii=False, allow_nan=True)
        else:
            super().__init__(allow_nan=True)

    # simplejson's Decimal encoding allows '-NaN' as an output, which is a parse error for json.loads
    # to get the good parts of Decimal support, we'll special-case NaN decimals and otherwise duplicate the encoding for decimals the same way simplejson does
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            if obj.is_nan():
                return math.nan
            return DecimalStr(obj)
        return super().default(obj)


def to_json(obj):
    return Encoder().encode(obj)


class LambdaMarshaller:
    def __init__(self):
        self.jsonEncoder = Encoder()

    def unmarshal_request(self, request, content_type="application/json"):
        if content_type != "application/json":
            return request
        try:
            return json.loads(request)
        except Exception as e:
            raise FaultException(
                FaultException.UNMARSHAL_ERROR,
                "Unable to unmarshal input: {}".format(str(e)),
                None,
            )

    def marshal_response(self, response):
        if isinstance(response, bytes):
            return response, "application/unknown"

        try:
            return self.jsonEncoder.encode(response), "application/json"
        except Exception as e:
            raise FaultException(
                FaultException.MARSHAL_ERROR,
                "Unable to marshal response: {}".format(str(e)),
                None,
            )
