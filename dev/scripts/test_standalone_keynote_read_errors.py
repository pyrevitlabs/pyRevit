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
        "alert_db_error",
        "lock_owner_label",
        "lock_target_label",
        "LOCK_ALERT_TITLE",
        "READ_ALERT_TITLE",
        "PERMISSION_ALERT_TITLE",
        "WRITE_LOCK_TIMEOUT_MARKER",
        "READ_TIMEOUT_MARKER",
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
            HOST_APP=SimpleNamespace(username="current-user"),
            forms=Mock(),
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
                self.assertIn("read permissions", message)
                self.assertIn("Access to Keynotes.txt is denied.", message)
                self.assertNotIn("conversion", message.lower())
                self.assertNotIn("saving", message)
        self.namespace["forms"].alert.assert_not_called()
        self.window._offer_write_lock_release.assert_not_called()
        self.assertEqual(2, self.namespace["kdb"].connect.call_count)

    def test_access_denied_without_friendly_description_keeps_message(self):
        """Error handlers tolerate a formatter without an explanation."""
        self.namespace["describe_lock_error"] = Mock(return_value=None)
        self.namespace["kdb"].connect.side_effect = _AccessDeniedError("Access denied.")
        for method_name in ("_open_kfile", "_connect_kfile"):
            with self.subTest(method=method_name):
                method = getattr(self.window, method_name)
                args = (self.window._kfile,) if method_name == "_open_kfile" else ()
                with self.assertRaises(self.namespace["KeynoteSetupError"]) as raised:
                    method(*args)
                self.assertEqual("Access denied.", str(raised.exception))
        self.namespace["forms"].alert.assert_not_called()
        self.window._offer_write_lock_release.assert_not_called()

    def test_read_errors_have_read_alert_title(self):
        """Read and permission failures are not shown as locked files."""
        for error in (
            _TimeoutError("Read timeout."),
            _AccessDeniedError("Access denied."),
        ):
            with self.subTest(error=error):
                self.namespace["alert_db_error"](error, operation="read")
                self.assertEqual(
                    "Keynote Manager - Read Error",
                    self.namespace["forms"].alert.call_args.kwargs["title"],
                )

    def test_unknown_and_save_access_errors_have_neutral_guidance(self):
        """Save and unknown operations never claim a read-permission failure."""
        for operation in (None, "save"):
            with self.subTest(operation=operation):
                self.namespace["alert_db_error"](
                    _AccessDeniedError("Access denied."), operation=operation
                )
                alert = self.namespace["forms"].alert.call_args
                self.assertEqual(
                    "Keynote Manager - Permission Error", alert.kwargs["title"]
                )
                self.assertIn("file permissions", alert.kwargs["sub_msg"])
                self.assertIn("Access denied.", alert.kwargs["sub_msg"])
                self.assertNotIn("read permissions", alert.kwargs["sub_msg"])
                self.assertNotIn("saving", alert.kwargs["sub_msg"])

    def test_write_errors_keep_locked_alert_title(self):
        """Write-lock recovery retains its existing dialog title."""
        self.namespace["alert_db_error"](_TimeoutError("Wait for unlock timeout."))
        self.assertEqual(
            "Keynote Manager - Locked",
            self.namespace["forms"].alert.call_args.kwargs["title"],
        )

    def test_connection_lock_names_owner_and_target(self):
        """The production lock-description helpers are available in the harness."""
        self.namespace["kdb"].CATEGORIES_TABLE = "categories"
        headline, details = self.namespace["describe_lock_error"](
            _TimeoutError(
                'restricted by <ConnectionLock id:"lock-id" '
                'sig:"workstation:other-user:connection-id" locking:"db:categories:A">'
            )
        )
        self.assertEqual(
            "other-user (on computer WORKSTATION) is editing group A.", headline
        )
        self.assertIn("padlock", details)


class KeynoteSchemaReadErrorTests(unittest.TestCase):
    """Schema verification propagates I/O errors without attempting writes."""

    def test_connect_does_not_create_schema_after_read_failure(self):
        """Every schema read preserves both timeout and permission failures."""
        path = SCRIPT_PATH.with_name("keynotesdb.py")
        tree = ast.parse(path.read_text(encoding="utf-8"))
        tree.body = [
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name in ("_verify_keynotesdb_def", "connect")
        ]
        for error_type in (_TimeoutError, _AccessDeniedError):
            for stage in ("database", "categories", "keynotes"):
                with self.subTest(error=error_type.__name__, stage=stage):
                    error = error_type("Cannot read keynote file.")
                    conn = Mock()
                    if stage == "database":
                        conn.ReadDB.side_effect = error
                    elif stage == "categories":
                        conn.ReadTable.side_effect = error
                    else:
                        conn.ReadTable.side_effect = [None, error]
                    namespace = {
                        "System": SimpleNamespace(
                            TimeoutException=_TimeoutError,
                            UnauthorizedAccessException=_AccessDeniedError,
                        ),
                        "KEYNOTES_DB": "keynotes",
                        "CATEGORIES_TABLE": "categories",
                        "KEYNOTES_TABLE": "keynotes",
                        "HOST_APP": SimpleNamespace(username="current-user"),
                        "framework": Mock(),
                        "dfdb": Mock(),
                        "mlogger": Mock(),
                    }
                    namespace["dfdb"].DataBase.Connect.return_value = conn
                    exec(compile(tree, str(path), "exec"), namespace)
                    with self.assertRaises(error_type) as raised:
                        namespace["connect"]("Keynotes.txt")
                    self.assertIs(error, raised.exception)
                    conn.CreateDB.assert_not_called()
                    conn.CreateTable.assert_not_called()


if __name__ == "__main__":
    unittest.main()
