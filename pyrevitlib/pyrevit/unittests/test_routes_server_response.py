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
        data = u"caf\u00e9"  # fmt: skip
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
    """HTTP headers stub matching the two shapes the routes server can be handed.

    IronPython 2 parses request headers into a `mimetools.Message`, whose
    `items()` yields lower-cased names. CPython 3 parses them into an
    `email.message.Message`, whose `items()` yields the names as the client sent
    them. Both shapes are reproduced here, because a header lookup has to
    resolve the same way on either engine.
    """

    def __init__(self, headers=None, lower_case_names=False):
        self._headers = {}
        for key, value in (headers or {}).items():
            name = key.lower() if lower_case_names else key
            self._headers[name] = value

    def getheader(self, key, default=None):
        return self.get(key, default)

    # CPython 3 BaseHTTPRequestHandler uses headers[key] / headers.get()
    def get(self, key, default=None):
        """Look up a header, ignoring the case of the name, as both engines do."""
        lowered = key.lower()
        for name, value in self._headers.items():
            if name.lower() == lowered:
                return value
        return default

    def __getitem__(self, key):
        return self._headers[key]

    def items(self):
        return list(self._headers.items())


class _FakeHttpHandlerForPrepare(server.HttpRequestHandler):
    """Minimal HttpRequestHandler stub for exercising _prepare_request."""

    def __init__(self, headers=None, lower_case_names=False):
        # Bypass BaseHTTPRequestHandler.__init__ entirely; we only need
        # _prepare_request which reads self.headers and self.rfile.
        self.headers = _FakeHeaders(headers, lower_case_names=lower_case_names)
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
        self.assertIn(u"caf\u00e9", request.query_params["q"])  # fmt: skip

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
# Request header tests
# ---------------------------------------------------------------------------


class RoutesServerRequestHeadersTests(unittest.TestCase):
    """Tests that incoming HTTP headers reach the handler on request.headers.

    A route could not do header-based auth, content negotiation or an Origin
    check before, because nothing ever copied the wire headers onto the
    Request. What these pin down is that a header name resolves to the same
    value whichever engine parsed it, since IronPython 2 hands them over
    lower-cased and CPython 3 hands them over as sent.
    """

    INCOMING = {
        "Authorization": "Bearer s3cr3t",
        "Content-Type": "application/json",
        "X-Request-Id": "abc-123",
    }

    def _prepare(self, lower_case_names):
        http_handler = _FakeHttpHandlerForPrepare(
            self.INCOMING, lower_case_names=lower_case_names
        )
        route = _FakeRoute(pattern="/items/")
        return http_handler._prepare_request(route, "/items/", "GET", None)

    def test_incoming_headers_are_not_empty(self):
        """The headers of an incoming request must not be dropped.

        Regression guard for the bug this fixes: request.headers was always {}.
        """
        for lower_case_names in (False, True):
            request = self._prepare(lower_case_names)
            self.assertTrue(
                request.headers,
                "request.headers was empty for lower_case_names=%s" % lower_case_names,
            )

    def test_every_incoming_header_reaches_the_request(self):
        """Each header the client sent is readable on the prepared request."""
        for lower_case_names in (False, True):
            request = self._prepare(lower_case_names)
            for name, value in self.INCOMING.items():
                self.assertEqual(
                    value,
                    request.headers.get(name),
                    "header %r lost on lower_case_names=%s" % (name, lower_case_names),
                )

    def test_authorization_resolves_regardless_of_name_case(self):
        """The lookup a bearer-token check performs must work on both engines.

        IronPython 2 reports 'authorization' and CPython 3 reports 'Authorization'
        for the same request; `get("Authorization")` has to answer both.
        """
        for lower_case_names in (False, True):
            request = self._prepare(lower_case_names)
            self.assertEqual("Bearer s3cr3t", request.headers.get("Authorization"))
            self.assertEqual("Bearer s3cr3t", request.headers.get("authorization"))
            self.assertEqual("Bearer s3cr3t", request.headers["AUTHORIZATION"])

    def test_header_name_membership_ignores_case(self):
        """`in` resolves a header name without regard to case."""
        for lower_case_names in (False, True):
            request = self._prepare(lower_case_names)
            self.assertIn("Authorization", request.headers)
            self.assertIn("authorization", request.headers)
            self.assertNotIn("X-Absent", request.headers)

    def test_absent_header_reads_as_none(self):
        """A header the client did not send has no value, rather than raising."""
        request = self._prepare(lower_case_names=False)
        self.assertIsNone(request.headers.get("X-Absent"))
        self.assertEqual("fallback", request.headers.get("X-Absent", "fallback"))

    def test_header_names_are_exposed_normalized(self):
        """Names are stored lower-cased, so iterating is stable across engines."""
        request = self._prepare(lower_case_names=False)
        self.assertEqual(
            sorted(k.lower() for k in self.INCOMING),
            sorted(request.headers.keys()),
        )

    def test_repeated_header_collapses_to_a_single_value(self):
        """A client repeating a name leaves one entry, whichever value wins.

        Which of the repeats survives is not asserted: the order IronPython 2
        reports repeated names in comes from a dict, which does not define one.
        What must hold is that the repeats do not fan out into several entries.
        """
        http_handler = _FakeHttpHandlerForPrepare()
        http_handler.headers._headers["X-Multi"] = "first"
        http_handler.headers._headers["x-multi"] = "second"
        route = _FakeRoute(pattern="/items/")

        request = http_handler._prepare_request(route, "/items/", "GET", None)

        self.assertEqual(1, len([k for k in request.headers if k == "x-multi"]))
        self.assertIn(request.headers.get("X-Multi"), ("first", "second"))

    def test_setting_the_same_name_differently_replaces_the_value(self):
        """Writing one name twice leaves a single entry, not two."""
        request = base.Request(path="/", method="GET")
        request.add_header("X-Token", "first")
        request.add_header("x-token", "second")

        self.assertEqual(1, len(request.headers))
        self.assertEqual("second", request.headers.get("X-Token"))

    def test_headers_are_removed_by_name_regardless_of_case(self):
        """Deleting and popping match without regard to case."""
        request = base.Request(path="/", method="GET")
        request.add_header("X-Drop", "value")
        del request.headers["x-drop"]
        self.assertNotIn("X-Drop", request.headers)

        request.add_header("X-Pop", "value")
        self.assertEqual("value", request.headers.pop("x-POP"))
        self.assertNotIn("X-Pop", request.headers)

    def test_setdefault_does_not_overwrite_an_existing_header(self):
        """Setdefault fills an absent name only, matching plain dict semantics."""
        request = base.Request(path="/", method="GET")
        request.add_header("X-Set", "kept")

        self.assertEqual("kept", request.headers.setdefault("x-set", "ignored"))
        self.assertEqual("filled", request.headers.setdefault("X-New", "filled"))

    def test_update_normalizes_every_name_it_adds(self):
        """A bulk update routes through the same normalization as add_header."""
        headers = base.CaseInsensitiveHeaders()
        headers.update({"Content-Type": "application/json"})

        self.assertEqual("application/json", headers.get("content-type"))
        self.assertEqual("application/json", headers["CONTENT-TYPE"])

    def test_copy_is_independent_and_case_insensitive(self):
        """A copy keeps the case-insensitive behavior without sharing state."""
        original = base.CaseInsensitiveHeaders({"Authorization": "Bearer s3cr3t"})
        copied = original.copy()

        copied["X-Extra"] = "value"

        self.assertEqual("Bearer s3cr3t", copied.get("authorization"))
        self.assertNotIn("X-Extra", original)

    def test_headers_stay_out_of_the_query_and_path_parameters(self):
        """Headers must not bleed into the handler's other injected arguments."""
        request = self._prepare(lower_case_names=False)

        self.assertEqual({}, request.query_params)
        self.assertEqual([], request.params)
        self.assertNotIn("authorization", request.query_params)
        self.assertEqual("/items/", request.path)

    def test_request_headers_are_a_plain_dict_for_consumers(self):
        """Handlers copy the mapping wholesale, as the issue's repro does."""
        request = self._prepare(lower_case_names=True)

        copied = dict(request.headers)

        self.assertIsInstance(copied, dict)
        self.assertEqual("Bearer s3cr3t", copied.get("authorization"))

    def test_response_headers_are_untouched(self):
        """Only request headers gained case-insensitive lookup."""
        response = base.Response(status=base.OK, data="x")
        response.add_header("Content-Type", "text/html")

        self.assertEqual("text/html", response.headers.get("Content-Type"))
        self.assertIsNone(response.headers.get("content-type"))


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

        request = self._make_request(query_params={"sort": "asc"}, params=route_params)
        kwargs = handler.RequestHandler.prepare_handler_kwargs(
            request=request, handler=my_handler
        )
        self.assertEqual("99", kwargs["item_id"])
        self.assertEqual("asc", kwargs["sort"])
