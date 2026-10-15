"""Exercise Keynote Manager connection errors without starting Revit."""

import ast
from pathlib import Path
import re
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    REPO_ROOT
    / "extensions/pyRevitTools.extension/pyRevit.tab"
    / "Drawing Set.panel/Keynotes.pushbutton/script.py"
)


def _load_error_handlers():
    """Execute the real helper and connection methods without the WPF window."""
    tree = ast.parse(SCRIPT_PATH.read_text(encoding="utf-8"))
    names = {
        "KeynoteSetupError",
        "describe_lock_error",
        "RELEASE_LOCKS_HINT",
        "_RESTRICTING_LOCK_RE",
        "MAX_KFILE_ATTEMPTS",
    }
    nodes = []
    for node in tree.body:
        if getattr(node, "name", None) in names:
            nodes.append(node)
        elif isinstance(node, ast.Assign) and any(
            getattr(target, "id", None) in names for target in node.targets
        ):
            nodes.append(node)
        elif getattr(node, "name", None) == "KeynoteManagerWindow":
            node.bases = []
            node.body = [
                method
                for method in node.body
                if getattr(method, "name", None) in ("_open_kfile", "_connect_kfile")
            ]
            nodes.append(node)
    tree.body = nodes
    namespace = {"re": re}
    exec(compile(tree, str(SCRIPT_PATH), "exec"), namespace)
    return namespace


class _TimeoutError(Exception):
    """Expose the .NET exception properties used by the production handlers."""

    def __init__(self, message, inner=None):
        super().__init__(message)
        self.Message = message
        self.InnerException = inner


class _AccessDeniedError(Exception):
    """Expose the .NET access-denied exception message."""

    def __init__(self, message):
        super().__init__(message)
        self.Message = message


class KeynoteReadErrorTests(unittest.TestCase):
    """Read failures never suggest releasing another user's save lock."""

    def setUp(self):
        """Load production code with inert substitutes for hosted dependencies."""
        self.namespace = _load_error_handlers()
        self.namespace.update(
            System=SimpleNamespace(
                TimeoutException=_TimeoutError,
                UnauthorizedAccessException=_AccessDeniedError,
            ),
            logger=Mock(),
            op=SimpleNamespace(exists=lambda path: True),
            kdb=Mock(),
        )
        self.window = self.namespace["KeynoteManagerWindow"]()
        self.window._kfile = "Keynotes.txt"
        self.window._conn = None
        self.window._preflight_kfile = Mock()
        self.window._offer_write_lock_release = Mock(return_value=False)

    def _connect_error(self, method_name, message):
        self.namespace["kdb"].connect.side_effect = _TimeoutError(message)
        method = getattr(self.window, method_name)
        args = (self.window._kfile,) if method_name == "_open_kfile" else ()
        with self.assertRaises(self.namespace["KeynoteSetupError"]) as raised:
            method(*args)
        return str(raised.exception)

    def test_read_timeout_explanation(self):
        """A read timeout names syncing rather than a colleague's save."""
        headline, details = self.namespace["describe_lock_error"](
            _TimeoutError("Read timeout.")
        )
        self.assertEqual("The keynote file could not be read.", headline)
        self.assertIn("Desktop Connector or OneDrive", details)
        self.assertNotIn("saving", details)
        self.assertNotIn("padlock", details)

    def test_read_timeout_includes_underlying_file_error(self):
        """Read timeout details retain the original file exception message."""
        error = _TimeoutError(
            "Read timeout.",
            SimpleNamespace(Message="The process cannot access the file."),
        )
        headline, details = self.namespace["describe_lock_error"](error)
        self.assertEqual("The keynote file could not be read.", headline)
        self.assertIn(error.InnerException.Message, details)

    def test_both_connection_paths_explain_read_timeout(self):
        """Initial open and project switching use the same read explanation."""
        for method_name in ("_open_kfile", "_connect_kfile"):
            with self.subTest(method=method_name):
                message = self._connect_error(method_name, "Read timeout.")
                self.assertIn("The keynote file could not be read.", message)
                self.assertIn("Desktop Connector or OneDrive", message)
                self.assertNotIn("saving", message)
        self.window._offer_write_lock_release.assert_not_called()

    def test_both_connection_paths_explain_write_timeout(self):
        """Only write timeouts offer stale-lock recovery and save guidance."""
        for method_name in ("_open_kfile", "_connect_kfile"):
            with self.subTest(method=method_name):
                message = self._connect_error(method_name, "Wait for unlock timeout.")
                self.assertIn("Someone else is saving", message)
                self.assertIn("padlock", message)
        self.window._offer_write_lock_release.assert_called_once_with("Keynotes.txt")

    def test_unknown_timeout_keeps_original_message(self):
        """Unrecognized timeouts are not mislabeled as another user's save."""
        for method_name in ("_open_kfile", "_connect_kfile"):
            with self.subTest(method=method_name):
                self.assertEqual(
                    "Unexpected timeout.",
                    self._connect_error(method_name, "Unexpected timeout."),
                )
        self.window._offer_write_lock_release.assert_not_called()

    def test_connection_paths_preserve_underlying_file_error(self):
        """Both connection paths show the I/O cause supplied by DeffrelDB."""
        error = _TimeoutError(
            "Read timeout.", SimpleNamespace(Message="Sharing violation.")
        )
        self.namespace["kdb"].connect.side_effect = error
        for method_name in ("_open_kfile", "_connect_kfile"):
            method = getattr(self.window, method_name)
            args = (self.window._kfile,) if method_name == "_open_kfile" else ()
            with self.assertRaises(self.namespace["KeynoteSetupError"]) as raised:
                method(*args)
            self.assertIn("Sharing violation.", str(raised.exception))

    def test_access_denied_does_not_offer_conversion(self):
        """Both connection paths report permissions and preserve the cause."""
        self.namespace["forms"] = Mock()
        self.namespace["kdb"].connect.side_effect = _AccessDeniedError(
            "Access to Keynotes.txt is denied."
        )
        for method_name in ("_open_kfile", "_connect_kfile"):
            with self.subTest(method=method_name):
                method = getattr(self.window, method_name)
                args = (self.window._kfile,) if method_name == "_open_kfile" else ()
                with self.assertRaises(self.namespace["KeynoteSetupError"]) as raised:
                    method(*args)
                message = str(raised.exception)
                self.assertIn("permission", message)
                self.assertIn("Access to Keynotes.txt is denied.", message)
                self.assertNotIn("conversion", message.lower())
                self.assertNotIn("saving", message)
        self.namespace["forms"].alert.assert_not_called()
        self.window._offer_write_lock_release.assert_not_called()
        self.assertEqual(2, self.namespace["kdb"].connect.call_count)


if __name__ == "__main__":
    unittest.main()
