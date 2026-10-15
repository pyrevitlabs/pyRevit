# -*- coding: utf-8 -*-
"""Utility functions and types.

The HTTP status codes exported here are spelled out rather than imported from
the standard library http client, which is expensive to import under IronPython
and is not otherwise needed to describe a request or a response.
"""

# pylint: disable=import-error,invalid-name,broad-except
# pylint: disable=unused-import,useless-object-inheritance

OK = 200
ACCEPTED = 202
NO_CONTENT = 204
INTERNAL_SERVER_ERROR = 500

DEFAULT_SOURCE = "pyrevit.routes"


class CaseInsensitiveHeaders(dict):
    """A mapping of HTTP header names to values that ignores key case.

    HTTP field names are case-insensitive (RFC 9110, section 5.1), but the
    casing a handler is handed depends on the engine that parsed the request.
    IronPython 2 parses headers into a `mimetools.Message`, which lower-cases
    every field name, while CPython 3 parses them into an
    `email.message.Message`, which preserves the casing the client sent.
    Normalizing here is what lets `headers.get("Authorization")` resolve to the
    same value on both engines.

    Note:
        Names are normalized to lower case on the way in, so iterating the
        mapping yields lower-cased names rather than the ones the client sent.

    Invariant:
        A repeated field name collapses into a single entry. The wire format
        lets a client send a name more than once - `Cookie` and `Accept` are
        routinely repeated - and which of the repeats survives here is decided
        by the order the engine reports them in, which IronPython 2 does not
        define.
    """

    @staticmethod
    def _normalize(key):
        return key.lower() if isinstance(key, str) else key

    def __init__(self, *args, **kwargs):
        """Build the mapping from an optional mapping or iterable of pairs.

        Args:
            *args: An optional mapping, or an iterable of key:value pairs.
            **kwargs: Additional header names and values.
        """
        super(CaseInsensitiveHeaders, self).__init__()
        self.update(*args, **kwargs)

    def __setitem__(self, key, value):
        super(CaseInsensitiveHeaders, self).__setitem__(self._normalize(key), value)

    def __getitem__(self, key):
        return super(CaseInsensitiveHeaders, self).__getitem__(self._normalize(key))

    def __delitem__(self, key):
        super(CaseInsensitiveHeaders, self).__delitem__(self._normalize(key))

    def __contains__(self, key):
        return super(CaseInsensitiveHeaders, self).__contains__(self._normalize(key))

    def get(self, key, default=None):
        """Look up a header value without regard to the case of the name.

        Args:
            key (str): Header name.
            default: Value returned when the header is absent.

        Returns:
            The header value, or `default`.
        """
        return super(CaseInsensitiveHeaders, self).get(self._normalize(key), default)

    def pop(self, key, *args):
        """Remove a header and return its value, ignoring the case of the name."""
        return super(CaseInsensitiveHeaders, self).pop(self._normalize(key), *args)

    def setdefault(self, key, default=None):
        """Return the value for a header, setting it to `default` if it is absent."""
        normalized = self._normalize(key)
        if normalized not in self:
            self[normalized] = default
        return super(CaseInsensitiveHeaders, self).__getitem__(normalized)

    def update(self, *args, **kwargs):
        """Add several headers at once, each name normalized on the way in."""
        for key, value in dict(*args, **kwargs).items():
            self[key] = value

    def copy(self):
        """Return an independent case-insensitive copy of these headers."""
        return CaseInsensitiveHeaders(self)


class Request(object):
    """Request wrapper object."""

    def __init__(
        self, path="/", method="GET", data=None, params=None, query_params=None
    ):
        self.path = path
        self.method = method
        self.data = data
        self._headers = CaseInsensitiveHeaders()
        self._params = params or []
        self._query_params = query_params or {}

    @property
    def headers(self):
        """Request headers, looked up without regard to the case of the name."""
        return self._headers

    @property
    def params(self):
        """Request parameters."""
        return self._params

    @property
    def query_params(self):
        """Request query string parameters as a dictionary."""
        return self._query_params

    @property
    def callback_url(self):
        """Request callback url, if provided in payload."""
        if isinstance(self.data, dict):
            return self.data.get("callbackUrl", None)
        return None

    def add_header(self, key, value):
        """Add new header key:value, replacing any value already held for the name.

        Args:
            key (str): Header name, matched without regard to case.
            value (str): Header value.
        """
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
