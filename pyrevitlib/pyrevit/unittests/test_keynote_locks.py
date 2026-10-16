# -*- coding: utf-8 -*-
"""Hosted unit tests for releasing Keynote Manager locks.

Run from Revit via the DevTools "Run All Tests" button, which discovers every
``test_*`` module in this package. The tests pin the contract of the Release
Locks button in ``keynotesdb``: a crashed session's record lock is released,
locks held by the current window are never offered, and a write sidecar is
only deleted while it is still the stale one the user agreed to release.
Breaking any of these lets two writes overlap and lose keynote changes.
"""

import ast
import os
import os.path as op
import shutil
import re
import sys
import tempfile
import time
import unittest

import System
from pyrevit import EXTENSIONS_DEFAULT_DIR, HOST_APP


KEYNOTES_BUNDLE_DIR = op.join(
    EXTENSIONS_DEFAULT_DIR,
    "pyRevitTools.extension",
    "pyRevit.tab",
    "Drawing Set.panel",
    "Keynotes.pushbutton",
)
CRASHED_USER = "crashed-user"


def _load_keynotesdb():
    """Import the Keynote Manager's keynotesdb module from its bundle."""
    sys.path.insert(0, KEYNOTES_BUNDLE_DIR)
    try:
        import keynotesdb
    finally:
        sys.path.remove(KEYNOTES_BUNDLE_DIR)
    return keynotesdb


kdb = _load_keynotesdb()


class _KeynoteFileTestCase(unittest.TestCase):
    """Give each test its own keynote file in a scratch folder."""

    def setUp(self):
        """Create an empty keynote file in a new scratch folder."""
        self.folder = tempfile.mkdtemp(prefix="pyrevit_keynote_locks_")
        self.kfile = op.join(self.folder, "Keynotes.txt")
        open(self.kfile, "w").close()

    def tearDown(self):
        """Remove the scratch folder and everything in it."""
        shutil.rmtree(self.folder, ignore_errors=True)


class StaleWriteLockTests(_KeynoteFileTestCase):
    """Releasing the sidecar DeffrelDB holds while it writes the file."""

    def _write_sidecar(self, age_seconds):
        """Create the sidecar as if a save started `age_seconds` ago."""
        lock_path = kdb.datastore_lock_path(self.kfile)
        open(lock_path, "w").close()
        written = time.time() - age_seconds
        os.utime(lock_path, (written, written))
        return kdb.datastore_lock_stamp(self.kfile)

    def _stale_age(self):
        """Return an age comfortably past the stale threshold."""
        return kdb.DATASTORE_LOCK_STALE_SECONDS + 60

    def _folder_contents(self):
        """List the scratch folder, to catch leftover claimed sidecars."""
        return sorted(os.listdir(self.folder))

    def test_sidecar_is_named_without_the_file_extension(self):
        """DeffrelDB guards Keynotes.txt with Keynotes.lock."""
        self.assertEqual(
            op.join(self.folder, "Keynotes.lock"),
            kdb.datastore_lock_path(self.kfile),
        )

    def test_save_in_progress_is_not_stale(self):
        """A sidecar younger than the threshold belongs to a live save."""
        self.assertFalse(kdb.is_stale_datastore_lock(self._write_sidecar(5)))

    def test_missing_sidecar_is_not_stale(self):
        """No sidecar means there is nothing to release."""
        self.assertIsNone(kdb.datastore_lock_stamp(self.kfile))
        self.assertFalse(kdb.is_stale_datastore_lock(None))

    def test_unchanged_stale_sidecar_is_released(self):
        """The stale sidecar the user confirmed is deleted, with no leftovers."""
        stamp = self._write_sidecar(self._stale_age())
        self.assertTrue(kdb.is_stale_datastore_lock(stamp))
        self.assertTrue(kdb.clear_datastore_lock(self.kfile, stamp))
        self.assertEqual(["Keynotes.txt"], self._folder_contents())

    def test_sidecar_replaced_during_confirmation_is_kept(self):
        """A live save's new sidecar survives a release confirmed on the old one."""
        stale_stamp = self._write_sidecar(self._stale_age())
        os.remove(kdb.datastore_lock_path(self.kfile))
        live_stamp = self._write_sidecar(0)
        self.assertRaises(
            kdb.DataStoreLockChanged,
            kdb.clear_datastore_lock,
            self.kfile,
            stale_stamp,
        )
        self.assertEqual(live_stamp, kdb.datastore_lock_stamp(self.kfile))
        self.assertEqual(["Keynotes.lock", "Keynotes.txt"], self._folder_contents())

    def test_live_sidecar_is_put_back_after_being_claimed(self):
        """A sidecar that is no longer stale is restored, not deleted."""
        live_stamp = self._write_sidecar(5)
        self.assertRaises(
            kdb.DataStoreLockChanged,
            kdb.clear_datastore_lock,
            self.kfile,
            live_stamp,
        )
        self.assertEqual(live_stamp, kdb.datastore_lock_stamp(self.kfile))
        self.assertEqual(["Keynotes.lock", "Keynotes.txt"], self._folder_contents())

    def test_sidecar_cleared_elsewhere_reports_nothing_released(self):
        """A sidecar someone else already removed is not an error."""
        stamp = self._write_sidecar(self._stale_age())
        os.remove(kdb.datastore_lock_path(self.kfile))
        self.assertFalse(kdb.clear_datastore_lock(self.kfile, stamp))


class RecordLockReleaseTests(_KeynoteFileTestCase):
    """Releasing lock rows a crashed session left in the keynote file."""

    def setUp(self):
        """Open a crashed session holding A.01 and a live window connection."""
        super(RecordLockReleaseTests, self).setUp()
        self.crashed = kdb.connect(self.kfile, username=CRASHED_USER)
        kdb.add_category(self.crashed, "A", "Group A")
        kdb.begin_edit(self.crashed, "A", category=True)
        self.window = kdb.connect(self.kfile)

    def tearDown(self):
        """Close both connections before the scratch folder goes."""
        for conn in (self.window, self.crashed):
            try:
                conn.Dispose()
            except Exception:
                pass
        super(RecordLockReleaseTests, self).tearDown()

    def _requesters(self, locks):
        """Return who holds each of the given locks."""
        return sorted(lk.LockRequester for lk in locks)

    def test_crashed_session_lock_is_offered(self):
        """The crashed session's lock is the one Release Locks lists."""
        self.assertEqual(
            [CRASHED_USER],
            self._requesters(kdb.foreign_locks(self.window, [self.window])),
        )

    def test_crashed_session_lock_is_released(self):
        """After release the record can be locked and saved again."""
        stale = kdb.foreign_locks(self.window, [self.window])
        self.assertEqual(1, kdb.release_locks(self.kfile, [lk.LockId for lk in stale]))
        self.assertEqual([], kdb.foreign_locks(self.window, [self.window]))
        kdb.begin_edit(self.window, "A", category=True)
        kdb.update_category_title(self.window, "A", "Group A renamed")
        kdb.end_edit(self.window)
        self.assertEqual(
            "Group A renamed",
            kdb.find(self.window, "A").text,
        )

    def test_window_locks_are_never_offered(self):
        """Locks held by the window's own connections are left alone."""
        kdb.add_category(self.window, "B", "Group B")
        kdb.begin_edit(self.window, "B", category=True)
        try:
            stale = kdb.foreign_locks(self.window, [self.window])
            self.assertNotIn(self.window.ConnectionId, [lk.LockConnId for lk in stale])
            kdb.release_locks(self.kfile, [lk.LockId for lk in stale])
            self.assertEqual(
                ["B"],
                [
                    lk.LockTargetRecordKey
                    for lk in kdb.get_locks(self.window)
                    if lk.LockConnId == self.window.ConnectionId
                ],
            )
        finally:
            kdb.end_edit(self.window)

    def test_window_commit_does_not_bring_a_released_lock_back(self):
        """A window that was mid-edit during the release does not restore it."""
        kdb.add_category(self.window, "B", "Group B")
        kdb.begin_edit(self.window, "B", category=True)
        stale = kdb.foreign_locks(self.window, [self.window])
        kdb.release_locks(self.kfile, [lk.LockId for lk in stale])
        kdb.end_edit(self.window)
        self.assertEqual([], kdb.foreign_locks(self.window, [self.window]))


def _load_error_description():
    """Load the real error formatter without opening Keynote Manager."""
    with open(op.join(KEYNOTES_BUNDLE_DIR, "script.py"), "r") as script_file:
        tree = ast.parse(script_file.read())
    names = {
        "describe_lock_error",
        "lock_owner_label",
        "lock_target_label",
        "RELEASE_LOCKS_HINT",
        "_RESTRICTING_LOCK_RE",
        "WRITE_LOCK_TIMEOUT_MARKER",
        "READ_TIMEOUT_MARKER",
    }
    tree.body = [
        node
        for node in tree.body
        if getattr(node, "name", None) in names
        or (
            isinstance(node, ast.Assign)
            and any(getattr(target, "id", None) in names for target in node.targets)
        )
    ]
    namespace = {"re": re, "System": System, "HOST_APP": HOST_APP, "kdb": kdb}
    eval(compile(tree, "script.py", "exec"), namespace)
    return namespace["describe_lock_error"]


class ReadErrorMessageTests(unittest.TestCase):
    """Distinguish an unreadable file from a DeffrelDB save lock."""

    def test_read_timeout_names_sync_clients(self):
        """Read timeouts suggest waiting for syncing, not releasing locks."""
        describe = _load_error_description()
        headline, details = describe(System.TimeoutException("Read timeout."))
        self.assertEqual("The keynote file could not be read.", headline)
        self.assertIn("Desktop Connector or OneDrive", details)
        self.assertNotIn("saving", details)
        self.assertNotIn("padlock", details)

    def test_read_timeout_keeps_the_file_error(self):
        """The original I/O message is visible alongside the explanation."""
        describe = _load_error_description()
        inner = System.IO.IOException("Sharing violation.")
        headline, details = describe(System.TimeoutException("Read timeout.", inner))
        self.assertEqual("The keynote file could not be read.", headline)
        self.assertIn(inner.Message, details)

    def test_unlock_timeout_still_explains_saving(self):
        """Write-lock timeouts retain their save and padlock guidance."""
        describe = _load_error_description()
        headline, details = describe(
            System.TimeoutException("Wait for unlock timeout.")
        )
        self.assertEqual("The keynote file is busy.", headline)
        self.assertIn("Someone else is saving", details)
        self.assertIn("padlock", details)

    def test_access_denied_explains_permissions(self):
        """A .NET access error reports the missing read permission."""
        describe = _load_error_description()
        error = System.UnauthorizedAccessException("Access to Keynotes.txt is denied.")
        headline, details = describe(error, operation="read")
        self.assertIn("permission", headline)
        self.assertIn("read permissions", details)
        self.assertIn(error.Message, details)


class ReadTimeoutCauseTests(_KeynoteFileTestCase):
    """Keep the real file exception when an exclusive handle blocks reads."""

    def test_exclusive_handle_is_preserved_as_timeout_cause(self):
        """A bounded read failure carries the sharing violation."""
        stream = System.IO.File.Open(
            self.kfile,
            System.IO.FileMode.Open,
            System.IO.FileAccess.ReadWrite,
            getattr(System.IO.FileShare, "None"),
        )
        try:
            with self.assertRaises(System.TimeoutException) as raised:
                kdb.connect(self.kfile)
            self.assertEqual("Read timeout.", raised.exception.Message)
            self.assertIsInstance(
                raised.exception.InnerException, System.IO.IOException
            )
        finally:
            stream.Dispose()

    def test_failed_read_leaves_no_lock_sidecar(self):
        """A connect that cannot read the file must not leave a write lock behind."""
        stream = System.IO.File.Open(
            self.kfile,
            System.IO.FileMode.Open,
            System.IO.FileAccess.ReadWrite,
            getattr(System.IO.FileShare, "None"),
        )
        try:
            self.assertRaises(System.TimeoutException, kdb.connect, self.kfile)
            self.assertIsNone(kdb.datastore_lock_stamp(self.kfile))
        finally:
            stream.Dispose()

    def test_failed_load_preserves_error_when_sidecar_cleanup_times_out(self):
        """An undeletable sidecar cannot hide or indefinitely delay a read error."""
        import clr

        flags = (
            System.Reflection.BindingFlags.Instance
            | System.Reflection.BindingFlags.NonPublic
        )
        store_type = clr.GetClrType(kdb.dfdb.DataBase).Assembly.GetType(
            "pyRevitLabs.DeffrelDB.DataStore"
        )
        store = System.Activator.CreateInstance(
            store_type,
            flags | System.Reflection.BindingFlags.Public,
            None,
            System.Array[System.Object](
                [kdb.dfdb.DataStoreType(self.kfile, None, None), False, 100]
            ),
            None,
        )
        store_type.GetProperty("ExclusiveAccess").SetValue(store, True, None)
        store_type.GetMethod("AcquireLock", flags).Invoke(store, None)
        lock_file = op.splitext(self.kfile)[0] + ".lock"
        data_stream = None
        lock_stream = None
        try:
            data_stream = System.IO.File.Open(
                self.kfile,
                System.IO.FileMode.Open,
                System.IO.FileAccess.ReadWrite,
                getattr(System.IO.FileShare, "None"),
            )
            lock_stream = System.IO.File.Open(
                lock_file,
                System.IO.FileMode.Open,
                System.IO.FileAccess.ReadWrite,
                getattr(System.IO.FileShare, "None"),
            )
            timer = System.Diagnostics.Stopwatch.StartNew()
            with self.assertRaises(System.Reflection.TargetInvocationException) as raised:
                store_type.GetMethod("Open", flags).Invoke(store, None)
            self.assertLess(timer.ElapsedMilliseconds, 2000)
            error = raised.exception.InnerException
            self.assertIsInstance(error, System.TimeoutException)
            self.assertEqual("Read timeout.", error.Message)
            self.assertIsInstance(error.InnerException, System.IO.IOException)
        finally:
            if lock_stream:
                lock_stream.Dispose()
            if data_stream:
                data_stream.Dispose()
            store_type.GetMethod("Dispose").Invoke(store, None)
