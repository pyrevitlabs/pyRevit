# -*- coding: utf-8 -*-
"""Tests for Unicode-safe JSON serialization in routes server handler.

Verifies that _safe_json_dumps correctly serializes objects containing
non-ASCII characters (e.g. French accented letters) that cause
UnicodeDecodeError in IronPython 2.7's json.dumps.

Also verifies that parse_response falls back to _safe_json_dumps
when json.dumps raises Unicode errors.
"""

import json
import unittest

from pyrevit.routes.server import handler
from pyrevit.routes.server import base


class SafeJsonDumpsTests(unittest.TestCase):
    """Tests for handler._safe_json_dumps."""

    # --- Primitives ---

    def test_none(self):
        self.assertEqual("null", handler._safe_json_dumps(None))

    def test_bool_true(self):
        self.assertEqual("true", handler._safe_json_dumps(True))

    def test_bool_false(self):
        self.assertEqual("false", handler._safe_json_dumps(False))

    def test_integer(self):
        self.assertEqual("42", handler._safe_json_dumps(42))

    def test_zero(self):
        self.assertEqual("0", handler._safe_json_dumps(0))

    def test_negative_integer(self):
        self.assertEqual("-7", handler._safe_json_dumps(-7))

    def test_float(self):
        result = handler._safe_json_dumps(3.14)
        self.assertAlmostEqual(3.14, float(result))

    # --- Plain ASCII strings ---

    def test_ascii_string(self):
        result = handler._safe_json_dumps("hello")
        self.assertEqual('"hello"', result)
        # Must be valid JSON
        self.assertEqual("hello", json.loads(result))

    def test_empty_string(self):
        result = handler._safe_json_dumps("")
        self.assertEqual('""', result)

    # --- Non-ASCII strings (the bug this fix addresses) ---

    def test_french_accented_string(self):
        """French accented chars like é (U+00E9) caused UnicodeDecodeError."""
        result = handler._safe_json_dumps(u"caf\u00e9")
        self.assertIn("\\u00e9", result)
        # Must round-trip through json.loads
        self.assertEqual(u"caf\u00e9", json.loads(result))

    def test_multiple_accented_chars(self):
        """Typical French Revit view names with multiple accents."""
        text = u"\u00c9L\u00c9VATIONS EXT\u00c9RIEURES"  # ÉLÉVATIONS EXTÉRIEURES
        result = handler._safe_json_dumps(text)
        self.assertEqual(text, json.loads(result))

    def test_e_grave(self):
        """è (U+00E8) as in 'Système'."""
        result = handler._safe_json_dumps(u"Syst\u00e8me")
        self.assertEqual(u"Syst\u00e8me", json.loads(result))

    def test_circumflex(self):
        """ê (U+00EA) as in 'Fenêtres'."""
        result = handler._safe_json_dumps(u"Fen\u00eatres")
        self.assertEqual(u"Fen\u00eatres", json.loads(result))

    def test_mixed_ascii_and_unicode(self):
        """Mix of ASCII and non-ASCII in same string."""
        text = u"Level 1 - \u00c9tage"
        result = handler._safe_json_dumps(text)
        self.assertEqual(text, json.loads(result))

    # --- String escaping ---

    def test_backslash(self):
        result = handler._safe_json_dumps("a\\b")
        self.assertEqual("a\\b", json.loads(result))

    def test_double_quote(self):
        result = handler._safe_json_dumps('say "hi"')
        self.assertEqual('say "hi"', json.loads(result))

    def test_newline(self):
        result = handler._safe_json_dumps("line1\nline2")
        self.assertEqual("line1\nline2", json.loads(result))

    def test_tab(self):
        result = handler._safe_json_dumps("a\tb")
        self.assertEqual("a\tb", json.loads(result))

    def test_carriage_return(self):
        result = handler._safe_json_dumps("a\rb")
        self.assertEqual("a\rb", json.loads(result))

    def test_control_char(self):
        result = handler._safe_json_dumps("a\x01b")
        self.assertIn("\\u0001", result)
        self.assertEqual("a\x01b", json.loads(result))

    # --- Collections ---

    def test_list(self):
        result = handler._safe_json_dumps([1, "two", None])
        parsed = json.loads(result)
        self.assertEqual([1, "two", None], parsed)

    def test_dict(self):
        result = handler._safe_json_dumps({"key": "value", "n": 42})
        parsed = json.loads(result)
        self.assertEqual("value", parsed["key"])
        self.assertEqual(42, parsed["n"])

    def test_nested_dict_with_unicode(self):
        """Nested structure with non-ASCII values — the real-world scenario."""
        obj = {
            "views": [
                {"name": u"PLAN G\u00c9N\u00c9RALE"},
                {"name": u"Nomenclature des r\u00e9visions"},
            ],
            "total": 2,
        }
        result = handler._safe_json_dumps(obj)
        parsed = json.loads(result)
        self.assertEqual(u"PLAN G\u00c9N\u00c9RALE", parsed["views"][0]["name"])
        self.assertEqual(u"Nomenclature des r\u00e9visions", parsed["views"][1]["name"])
        self.assertEqual(2, parsed["total"])

    def test_tuple(self):
        result = handler._safe_json_dumps((1, 2, 3))
        self.assertEqual([1, 2, 3], json.loads(result))

    def test_empty_list(self):
        self.assertEqual("[]", handler._safe_json_dumps([]))

    def test_empty_dict(self):
        self.assertEqual("{}", handler._safe_json_dumps({}))

    def test_dict_with_unicode_key(self):
        result = handler._safe_json_dumps({u"\u00e9tage": 1})
        parsed = json.loads(result)
        self.assertEqual(1, parsed[u"\u00e9tage"])

    # --- Bool before int (isinstance ordering) ---

    def test_bool_not_treated_as_int(self):
        """bool is a subclass of int; must check bool first."""
        self.assertEqual("true", handler._safe_json_dumps(True))
        self.assertNotEqual("1", handler._safe_json_dumps(True))


class ParseResponseUnicodeTests(unittest.TestCase):
    """Tests that parse_response handles non-ASCII data without crashing.

    In IronPython 2.7, json.dumps raises UnicodeDecodeError on non-ASCII
    strings. parse_response must fall back to _safe_json_dumps.
    """

    def test_string_response_with_accents(self):
        """Plain string response containing accented characters."""
        response = u"Fen\u00eatres ext\u00e9rieures"
        result = handler.RequestHandler.parse_response(response)
        self.assertEqual(base.OK, result.status)
        self.assertIsNotNone(result.data)
        # The data should be valid JSON (a JSON-encoded string)
        parsed = json.loads(result.data)
        self.assertEqual(response, parsed)

    def test_dict_response_with_accents(self):
        """Response object with .data containing non-ASCII strings."""

        class _Resp(object):
            status = base.OK
            headers = {"Content-Type": "application/json"}
            data = {
                "views": [
                    u"\u00c9L\u00c9VATIONS",
                    u"R\u00c9SERVOIRS",
                ]
            }

        result = handler.RequestHandler.parse_response(_Resp())
        self.assertIsNotNone(result.data)
        parsed = json.loads(result.data)
        self.assertEqual(u"\u00c9L\u00c9VATIONS", parsed["views"][0])

    def test_exception_response_with_accents(self):
        """Exception-like response with non-ASCII in message."""

        class _ExcResp(object):
            message = u"Erreur: \u00e9l\u00e9ment introuvable"
            status = base.INTERNAL_SERVER_ERROR
            source = "test"

        result = handler.RequestHandler.parse_response(_ExcResp())
        self.assertEqual(base.INTERNAL_SERVER_ERROR, result.status)
        parsed = json.loads(result.data)
        self.assertIn(u"\u00e9l\u00e9ment", parsed["exception"]["message"])
