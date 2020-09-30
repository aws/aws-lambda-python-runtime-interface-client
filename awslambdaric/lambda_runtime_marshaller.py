"""
Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import decimal
import math

import simplejson as json

from .lambda_runtime_exception import FaultException


# simplejson's Decimal encoding allows '-NaN' as an output, which is a parse error for json.loads
# to get the good parts of Decimal support, we'll special-case NaN decimals and otherwise duplicate the encoding for decimals the same way simplejson does
class Encoder(json.JSONEncoder):
    def __init__(self):
        super().__init__(use_decimal=False)

    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            if obj.is_nan():
                return math.nan
            return json.raw_json.RawJSON(str(obj))
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
