# -*- coding: utf-8 -*-
"""Utility functions and types."""
#pylint: disable=import-error,invalid-name,broad-except
#pylint: disable=unused-import,useless-object-inheritance
from pyrevit.compat import IRONPY3, PY3

if IRONPY3:
    from http.client import OK, ACCEPTED, INTERNAL_SERVER_ERROR, NO_CONTENT
elif PY3:
    from http import HTTPStatus as _s
    OK = _s.OK
    ACCEPTED = _s.ACCEPTED
    INTERNAL_SERVER_ERROR = _s.INTERNAL_SERVER_ERROR
    NO_CONTENT = _s.NO_CONTENT
else:
    from httplib import OK, ACCEPTED, INTERNAL_SERVER_ERROR, NO_CONTENT

DEFAULT_SOURCE = "pyrevit.routes"


class Request(object):
    """Request wrapper object."""
    def __init__(self, path='/', method='GET', data=None, params=None):
        self.path = path
        self.method = method
        self.data = data
        self._headers = {}
        self._params = params or []

    @property
    def headers(self):
        """Request headers dict."""
        return self._headers

    @property
    def params(self):
        """Request parameters."""
        return self._params

    @property
    def callback_url(self):
        """Request callback url, if provided in payload."""
        if isinstance(self.data, dict):
            return self.data.get("callbackUrl", None)
        return None

    def add_header(self, key, value):
        """Add new header key:value."""
        self._headers[key] = value


class Response(object):
    """Response wrapper object."""
    def __init__(self, status=200, data=None, headers=None):
        self.status = status
        self.data = data
        self._headers = headers or {}

    @property
    def headers(self):
        """Response headers dict."""
        return self._headers

    def add_header(self, key, value):
        """Add new header key:value."""
        self._headers[key] = value
