# -*- coding: utf-8 -*-
"""Tests for routes server response framing behavior."""

import unittest

from pyrevit.routes.server import base
from pyrevit.routes.server import handler
from pyrevit.routes.server import server


class _DummyWriter(object):
    def __init__(self):
        self.writes = []

    def write(self, payload):
        self.writes.append(payload)


class _DummyHttpHandler(server.HttpRequestHandler):
    def __init__(self):
        self.statuses = []
        self.headers = []
        self.end_headers_calls = 0
        self.wfile = _DummyWriter()

    def send_response(self, status):
        self.statuses.append(status)

    def send_header(self, key, value):
        self.headers.append((key, value))

    def end_headers(self):
        self.end_headers_calls += 1


class _FakeResponseObject(object):
    def __init__(self, status=base.OK, data=None, headers=None):
        self.status = status
        self.data = data
        self.headers = headers or {}


class RoutesServerWriteResponseTests(unittest.TestCase):
    def _run_write_response(self, parsed_response):
        handler_instance = _DummyHttpHandler()

        # Call HttpRequestHandler._write_response with a fake request handler
        # object that only implements the methods/attributes it needs.
        orig_request_handler_cls = server.handler.RequestHandler

        class _PatchedRequestHandler(object):
            @staticmethod
            def parse_response(_response):
                return parsed_response

        server.handler.RequestHandler = _PatchedRequestHandler
        try:
            server.HttpRequestHandler._write_response(handler_instance, object())
        finally:
            server.handler.RequestHandler = orig_request_handler_cls

        return handler_instance

    def test_sets_content_length_for_large_json_payload(self):
        data = "x" * 4096
        parsed = _FakeResponseObject(
            status=base.OK,
            data=data,
            headers={"Content-Type": "application/json"},
        )

        result = self._run_write_response(parsed)

        self.assertEqual([base.OK], result.statuses)
        self.assertEqual(1, result.end_headers_calls)
        self.assertEqual(data.encode("utf-8"), result.wfile.writes[0])
        self.assertIn(
            ("Content-Length", str(len(data.encode("utf-8")))), result.headers
        )

    def test_encodes_string_body_as_utf8_bytes(self):
        data = u"caf\u00e9"
        parsed = _FakeResponseObject(
            status=base.OK,
            data=data,
            headers={"Content-Type": "application/json"},
        )

        result = self._run_write_response(parsed)
        expected = data.encode("utf-8")

        self.assertEqual(expected, result.wfile.writes[0])
        self.assertIn(("Content-Length", str(len(expected))), result.headers)

    def test_writes_newline_when_body_is_none(self):
        parsed = _FakeResponseObject(status=base.NO_CONTENT, data=None, headers={})

        result = self._run_write_response(parsed)

        self.assertEqual([base.NO_CONTENT], result.statuses)
        self.assertEqual([b"\n"], result.wfile.writes)
        self.assertIn(("Content-Length", "1"), result.headers)
        self.assertEqual(1, result.end_headers_calls)

    def test_calls_end_headers_without_custom_headers(self):
        parsed = _FakeResponseObject(status=base.OK, data="ok", headers={})

        result = self._run_write_response(parsed)

        self.assertEqual(1, result.end_headers_calls)
        self.assertEqual([b"ok"], result.wfile.writes)

    def test_overrides_existing_content_length_header(self):
        data = "abc123"
        parsed = _FakeResponseObject(
            status=base.OK,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Content-Length": "99999",
            },
        )

        result = self._run_write_response(parsed)

        content_length_headers = [
            pair for pair in result.headers if pair[0].lower() == "content-length"
        ]
        self.assertEqual(1, len(content_length_headers))
        self.assertEqual(str(len(data.encode("utf-8"))), content_length_headers[0][1])


# ---------------------------------------------------------------------------
# Helpers shared by query-parsing and handler-kwargs tests
# ---------------------------------------------------------------------------


class _FakeRoute(object):
    """Minimal route stub that carries a pattern string."""

    def __init__(self, pattern="/"):
        self.pattern = pattern


class _FakeHeaders(object):
    """Minimal HTTP headers stub (IronPython uses getheader, CPython uses get)."""

    def getheader(self, key, default=None):
        return default

    # CPython 3 BaseHTTPRequestHandler uses headers[key] / headers.get()
    def get(self, key, default=None):
        return default

    def __getitem__(self, key):
        raise KeyError(key)


class _FakeHttpHandlerForPrepare(server.HttpRequestHandler):
    """Minimal HttpRequestHandler stub for exercising _prepare_request."""

    def __init__(self):
        # Bypass BaseHTTPRequestHandler.__init__ entirely; we only need
        # _prepare_request which reads self.headers and self.rfile.
        self.headers = _FakeHeaders()
        self.rfile = None


# ---------------------------------------------------------------------------
# Query-string parsing tests
# ---------------------------------------------------------------------------


class RoutesServerQueryParsingTests(unittest.TestCase):
    """Tests for the query-string parsing logic in _prepare_request."""

    def _prepare(self, route_pattern, path, query_string):
        """Call _prepare_request and return the resulting Request object."""
        http_handler = _FakeHttpHandlerForPrepare()
        route = _FakeRoute(pattern=route_pattern)
        return http_handler._prepare_request(route, path, "GET", query_string)

    # ------------------------------------------------------------------
    # Basic single-value keys
    # ------------------------------------------------------------------

    def test_single_value_key_flattened_to_string(self):
        """A query param with one value should be stored as a plain string."""
        request = self._prepare("/items/", "/items/", "a=1")
        self.assertEqual("1", request.query_params["a"])

    def test_multiple_distinct_keys_parsed_independently(self):
        """Each distinct key in the query string is stored as its own entry."""
        request = self._prepare("/items/", "/items/", "a=1&b=2")
        self.assertEqual("1", request.query_params["a"])
        self.assertEqual("2", request.query_params["b"])

    def test_empty_query_string_produces_empty_dict(self):
        """An absent query string leaves query_params empty."""
        request = self._prepare("/items/", "/items/", "")
        self.assertEqual({}, request.query_params)

    def test_none_query_string_produces_empty_dict(self):
        """A None query string leaves query_params empty."""
        request = self._prepare("/items/", "/items/", None)
        self.assertEqual({}, request.query_params)

    # ------------------------------------------------------------------
    # Multi-value (repeated) keys
    # ------------------------------------------------------------------

    def test_repeated_key_stored_as_list(self):
        """A key that appears more than once should be stored as a list."""
        request = self._prepare("/items/", "/items/", "tag=a&tag=b")
        self.assertIsInstance(request.query_params["tag"], list)
        self.assertIn("a", request.query_params["tag"])
        self.assertIn("b", request.query_params["tag"])

    def test_repeated_key_list_preserves_all_values(self):
        """All values for a repeated key must be present — none are dropped."""
        request = self._prepare("/items/", "/items/", "tag=x&tag=y&tag=z")
        self.assertEqual(3, len(request.query_params["tag"]))

    def test_mixed_single_and_multi_value_keys(self):
        """Single-value and multi-value keys can coexist in the same query."""
        request = self._prepare("/search/", "/search/", "q=hello&tag=a&tag=b")
        self.assertEqual("hello", request.query_params["q"])
        self.assertIsInstance(request.query_params["tag"], list)
        self.assertEqual(2, len(request.query_params["tag"]))

    # ------------------------------------------------------------------
    # URL-encoded values
    # ------------------------------------------------------------------

    def test_url_encoded_value_is_decoded(self):
        """URL percent-encoding in query values must be decoded."""
        request = self._prepare("/items/", "/items/", "name=hello+world")
        # parse_qs decodes '+' as a space by default
        self.assertIn("hello", request.query_params["name"])

    def test_url_encoded_special_characters(self):
        """Percent-encoded characters in query values are decoded properly."""
        request = self._prepare("/items/", "/items/", "q=caf%C3%A9")
        self.assertIn(u"caf\u00e9", request.query_params["q"])

    # ------------------------------------------------------------------
    # Path and query string isolation
    # ------------------------------------------------------------------

    def test_query_params_do_not_affect_request_path(self):
        """Query string parameters must not bleed into the request path."""
        request = self._prepare("/items/", "/items/", "a=1&b=2")
        self.assertEqual("/items/", request.path)

    def test_query_params_do_not_affect_route_params(self):
        """Query parameters are stored separately from URL path parameters."""
        request = self._prepare("/items/<id>", "/items/42", "filter=active")
        # route params captured from path placeholders
        param_keys = [p.key for p in request.params]
        self.assertNotIn("filter", param_keys)
        # query params available via query_params
        self.assertEqual("active", request.query_params["filter"])


# ---------------------------------------------------------------------------
# Handler-kwargs injection tests
# ---------------------------------------------------------------------------


class RoutesServerHandlerKwargsTests(unittest.TestCase):
    """Tests that query_params are injected into handler kwargs correctly."""

    def _make_request(self, query_params=None, params=None):
        return base.Request(
            path="/",
            method="GET",
            data=None,
            params=params or [],
            query_params=query_params or {},
        )

    def test_single_query_param_injected_as_kwarg(self):
        """A single-value query param is passed to the handler as a kwarg."""
        captured = {}

        def my_handler(request, limit):
            captured["limit"] = limit

        request = self._make_request(query_params={"limit": "10"})
        kwargs = handler.RequestHandler.prepare_handler_kwargs(
            request=request, handler=my_handler
        )
        self.assertIn("limit", kwargs)
        self.assertEqual("10", kwargs["limit"])

    def test_multi_value_query_param_injected_as_list(self):
        """A repeated query param is passed to the handler as a list kwarg."""
        captured = {}

        def my_handler(request, tag):
            captured["tag"] = tag

        request = self._make_request(query_params={"tag": ["a", "b"]})
        kwargs = handler.RequestHandler.prepare_handler_kwargs(
            request=request, handler=my_handler
        )
        self.assertIn("tag", kwargs)
        self.assertIsInstance(kwargs["tag"], list)
        self.assertEqual(["a", "b"], kwargs["tag"])

    def test_query_param_not_in_handler_signature_is_excluded(self):
        """Query params that don't match handler parameters are filtered out."""

        def my_handler(request):
            pass

        request = self._make_request(query_params={"unknown_param": "value"})
        kwargs = handler.RequestHandler.prepare_handler_kwargs(
            request=request, handler=my_handler
        )
        self.assertNotIn("unknown_param", kwargs)

    def test_request_object_always_injected(self):
        """The request object is always present in handler kwargs."""

        def my_handler(request):
            pass

        request = self._make_request(query_params={"a": "1"})
        kwargs = handler.RequestHandler.prepare_handler_kwargs(
            request=request, handler=my_handler
        )
        self.assertIn("request", kwargs)
        self.assertIs(request, kwargs["request"])

    def test_query_params_and_route_params_coexist_in_kwargs(self):
        """Route path params and query params are both present in kwargs."""
        from pyrevit.routes.server.router import RouteParam

        route_params = [RouteParam(key="item_id", value="99")]

        def my_handler(request, item_id, sort):
            pass

        request = self._make_request(
            query_params={"sort": "asc"}, params=route_params
        )
        kwargs = handler.RequestHandler.prepare_handler_kwargs(
            request=request, handler=my_handler
        )
        self.assertEqual("99", kwargs["item_id"])
        self.assertEqual("asc", kwargs["sort"])
