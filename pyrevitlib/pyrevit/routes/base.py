"""Utility functions and types"""
#pylint: disable=import-error,invalid-name,broad-except
#pylint: disable=missing-docstring
import json
#pylint: disable=unused-import
from httplib import OK, ACCEPTED, INTERNAL_SERVER_ERROR, NO_CONTENT


DEFAULT_SOURCE = "pyrevit.routes"


class Request(object):
    def __init__(self, path='/', method='GET', data=None, params=None):
        self.path = path
        self.method = method
        self.data = data
        self._headers = {}
        self._params = params or []

    @property
    def headers(self):
        return self._headers

    @property
    def params(self):
        return self._params

    @property
    def callback_url(self):
        if isinstance(self.data, dict):
            return self.data.get("callbackUrl", None)

    def add_header(self, key, value):
        self._headers[key] = value


class Response(object):
    def __init__(self, status=200, data=None):
        self.status = status
        self.data = data
        self._headers = {}

    @property
    def headers(self):
        return self._headers

    def add_header(self, key, value):
        self._headers[key] = value


def make_response(data, status=OK, headers=None):
    res = Response(status=status, data=data)
    for key, value in (headers or {}).items():
        res.add_header(key, value)
    return res


def parse_response(response):
    """Parse response object and return status, headers, and data"""
    status = OK
    headers = {}
    data = None

    # can not directly check for isinstance(x, Response)
    # this module is executed on a different Engine than the
    # script that registered the request handler function, thus
    # the Response in script engine does not match Response
    # registered when this module was loaded
    #
    # now process reponse based on obj type
    # it is an exception is has .message
    # write the exeption to output and return
    if hasattr(response, 'message'):
        status = \
            response.status if hasattr(response, 'status') \
                else INTERNAL_SERVER_ERROR
        headers = {'Content-Type': 'application/json'}
        data = json.dumps(
            {
                "exception": {
                    "source": response.source
                              if hasattr(response, 'source')
                              else DEFAULT_SOURCE,
                    "message": str(response)
                }
            }
        )

    # plain text response
    elif isinstance(response, str):
        # keey default status
        headers['Content-Type'] = 'text/html'
        data = json.dumps(response)

    # any obj that has .status and .data, OR
    # any json serializable object
    # serialize before sending results
    # in case exceptions happen in serialization,
    # there are no double status in response header
    else:
        # determine status
        status = getattr(response, 'status', OK)

        # determine headers
        headers.update(
            getattr(response, 'headers', {})
            )

        # determine data, or dump the response object
        data = getattr(response, 'data', response)

        # serialize data
        if data:
            data = json.dumps(data)
            headers['Content-Type'] = 'application/json'

    return status, headers, data
