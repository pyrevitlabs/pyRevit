"""Check coreutils.get_exception_message without Revit (regression for #4182)."""

import ast
from pathlib import Path
import unittest

import pytest


TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

COREUTILS = (
    Path(__file__).resolve().parents[4] / "pyrevitlib/pyrevit/coreutils/__init__.py"
)


def _load_get_exception_message(safe_strtype=str):
    tree = ast.parse(COREUTILS.read_text(encoding="utf-8"))
    node = next(
        n
        for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == "get_exception_message"
    )
    namespace = {"safe_strtype": safe_strtype}
    exec(
        compile(ast.Module(body=[node], type_ignores=[]), str(COREUTILS), "exec"),
        namespace,
    )
    return namespace["get_exception_message"]


class _DotNetException(Exception):
    Message = "Printer not found"

    def GetType(self):
        return type(self)

    def __str__(self):
        return "System.Exception: {}\n   at Foo.Bar()\n   at Baz.Qux()".format(
            self.Message
        )


@pytest.mark.regression
class GetExceptionMessageTests(unittest.TestCase):
    def setUp(self):
        self.get_exception_message = _load_get_exception_message()

    def test_dotnet_exception_returns_message_without_trace(self):
        message = self.get_exception_message(_DotNetException())
        self.assertEqual(message, "Printer not found")
        self.assertNotIn("at Foo.Bar", message)

    def test_python_exception_returns_str(self):
        self.assertEqual(
            self.get_exception_message(ValueError("bad value")), "bad value"
        )

    def test_dotnet_exception_with_empty_message_returns_empty_string(self):
        ex = _DotNetException()
        ex.Message = ""
        self.assertEqual(self.get_exception_message(ex), "")

    def test_dotnet_exception_with_none_message_returns_empty_string(self):
        ex = _DotNetException()
        ex.Message = None
        self.assertEqual(self.get_exception_message(ex), "")

    def test_python_exception_does_not_use_safe_strtype(self):
        def failing_safe_strtype(value):
            raise UnicodeDecodeError("ascii", b"x", 0, 1, "ordinal")

        get_message = _load_get_exception_message(failing_safe_strtype)
        self.assertEqual(get_message(ValueError("caf" + chr(233))), "caf" + chr(233))


if __name__ == "__main__":
    unittest.main()
