"""Tests for routes server response framing behavior."""

import unittest

from pyrevit.routes.server import base
from pyrevit.routes.server import server


class _DummyWriter(object):
    def __init__(self):
        self.writes = []

    def write(self, payload):
        self.writes.append(payload)


class _DummyHttpHandler(object):
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
        orig_parse_response = server.handler.RequestHandler.parse_response
        server.handler.RequestHandler.parse_response = staticmethod(
            lambda _response: parsed_response
        )
        try:
            server.HttpRequestHandler._write_response(handler_instance, object())
        finally:
            server.handler.RequestHandler.parse_response = orig_parse_response

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
