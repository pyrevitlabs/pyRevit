# -*- coding: utf-8 -*-
"""Hosted unit tests for pyRevit's sys.path management.

Run from Revit via the DevTools "Run All Tests" aggregator. Covers the
dedupe-on-insert contract (``pyrevit.add_to_sys_path``,
``pyrevit.dedupe_sys_path``) and asserts the invariant on the *live*
``sys.path`` of the running engine: no folder appears twice.

The live assertion is the one that matters. The helpers are only half the
fix, because IronPython's ``clr.AddReferenceToFileAndPath`` appends the
referenced assembly's folder to ``sys.path`` itself, once per call, and
pyRevit references several assemblies from the one engine folder. #3687.

The text-type filter is tested against every text type the running engine
actually exposes. pyRevit's patched IronPython unifies ``str`` and
``unicode`` into one type, so on that engine a unicode-specific repeat
cannot exist and the cases that need one skip rather than pass quietly.
"""

import os
import os.path as op
import shutil
import sys
import tempfile
import unittest

import pyrevit
from pyrevit import add_to_sys_path, dedupe_sys_path
from pyrevit.compat import safe_strtype


try:
    basestring  # noqa: B018 pylint: disable=used-before-assignment
except NameError:
    basestring = str

try:
    _UNICODE_TYPE = unicode  # noqa: F821 pylint: disable=undefined-variable
except NameError:
    _UNICODE_TYPE = str

# Mirrors pyrevit._TEXT_TYPES. A bare unicode literal cannot be used here: ruff
# format strips the u prefix, collapsing it to str on IronPython 2.
_TEXT_TYPES = (basestring,)

# pyRevit's patched IronPython collapses str and unicode into a single type, so
# a repeat that differs only by text type cannot exist there. Cases that need
# the distinction skip on that engine instead of passing vacuously.
needs_separate_unicode = unittest.skipIf(
    str is _UNICODE_TYPE,
    "this engine unifies str and unicode, so a unicode-only repeat cannot exist",
)


def _key(path):
    """Return the comparison key pyRevit uses for a sys.path entry."""
    return op.normcase(op.normpath(path))


def _count(paths, folder):
    """Return how many of the given entries resolve to the same folder."""
    return [p for p in paths if _key(p) == _key(folder)]


def _repeated():
    """Return every folder listed more than once on the live sys.path."""
    counts = {}
    for entry in sys.path:
        if not isinstance(entry, _TEXT_TYPES) or not entry:
            continue
        key = _key(entry)
        counts[key] = counts.get(key, 0) + 1
    return sorted(path for path, count in counts.items() if count > 1)


class SysPathDedupeTests(unittest.TestCase):
    """Contract of ``pyrevit.add_to_sys_path`` and ``pyrevit.dedupe_sys_path``."""

    def setUp(self):
        """Snapshot sys.path so each test can mutate it without leaking.

        These tests append and delete real entries, so the engine's own
        search order has to survive the suite intact.
        """
        self._snapshot = list(sys.path)

    def tearDown(self):
        """Restore the snapshot taken in setUp."""
        del sys.path[:]
        sys.path.extend(self._snapshot)

    def test_adds_a_new_folder_once(self):
        """Adding the same folder twice leaves one entry."""
        folder = tempfile.mkdtemp()
        try:
            add_to_sys_path(folder)
            add_to_sys_path(folder)
            self.assertEqual(1, len(_count(sys.path, folder)))
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    def test_skips_a_folder_already_on_sys_path(self):
        """A folder the loader already put on sys.path is not appended again."""
        folder = tempfile.mkdtemp()
        try:
            sys.path.append(folder)
            add_to_sys_path(folder)
            self.assertEqual(1, len(_count(sys.path, folder)))
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    def test_is_case_insensitive(self):
        """A folder differing only in case is the same folder on Windows."""
        folder = tempfile.mkdtemp()
        try:
            sys.path.append(folder)
            add_to_sys_path(folder.upper())
            self.assertEqual(1, len(_count(sys.path, folder)))
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    def test_keeps_the_first_occurrence_order(self):
        """Dedupe drops repeats without reordering the surviving entries.

        Order is the module-resolution priority, so collapsing duplicates
        must not move anything.
        """
        first = tempfile.mkdtemp()
        second = tempfile.mkdtemp()
        try:
            sys.path.append(second)
            sys.path.append(first)
            sys.path.append(second)

            dedupe_sys_path()

            tail = [_key(p) for p in sys.path][-2:]
            self.assertEqual([_key(second), _key(first)], tail)
        finally:
            shutil.rmtree(first, ignore_errors=True)
            shutil.rmtree(second, ignore_errors=True)

    def test_skips_paths_that_are_not_folders(self):
        """Missing, empty and None paths never reach sys.path.

        A stale entry that resolves to nothing makes the path list lie
        about what is searchable without contributing anything.
        """
        before = list(sys.path)
        missing = op.join(tempfile.gettempdir(), "pyrevit-missing-folder")

        add_to_sys_path(missing, None, "")

        self.assertEqual(before, list(sys.path))

    def test_text_types_cover_every_text_type_this_engine_has(self):
        """The filter accepts every text type the running engine exposes.

        Runs everywhere, and is what catches a narrowing back to ``(str,)``:
        on an engine where ``unicode`` is a separate type, dropping it makes
        a unicode repeat invisible to the dedupe.
        """
        for text_type in (str, _UNICODE_TYPE):
            self.assertIsInstance(
                text_type("x"),
                tuple(_TEXT_TYPES),
                "{} is not accepted".format(text_type.__name__),
            )

    def test_accepts_a_unicode_folder(self):
        """A unicode folder is registered, and only once.

        IronPython 2 makes ``str`` and ``unicode`` unrelated types, so a
        filter that accepts one silently drops the other - and a dropped
        entry is a repeat the dedupe never sees.
        """
        folder = safe_strtype(tempfile.mkdtemp())
        try:
            add_to_sys_path(folder)
            add_to_sys_path(folder)

            self.assertEqual(1, len(_count(sys.path, folder)))
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    @needs_separate_unicode
    def test_repeated_unicode_entries_are_counted(self):
        """The live assertion itself must see a repeated unicode entry.

        Guards the assertion rather than the code under it: if
        ``_repeated()`` skipped unicode entries it would report nothing and
        both live-path tests would pass on a path list that does have a
        repeat.
        """
        marker = safe_strtype("pyrevit-unicode-repeat-{}".format(os.getpid()))
        sys.path.append(marker)
        sys.path.append(marker)

        self.assertIn(_key(marker), _repeated())

    @needs_separate_unicode
    def test_dedupe_drops_a_repeated_unicode_entry(self):
        """dedupe_sys_path removes a repeat held as a unicode entry."""
        marker = safe_strtype("pyrevit-unicode-dedupe-{}".format(os.getpid()))
        sys.path.append(marker)
        sys.path.append(marker)

        dedupe_sys_path()

        self.assertEqual([], _repeated())


class EngineDirectoryTests(unittest.TestCase):
    """``pyrevit.ENGINES_DIR`` must name the folder that holds the engine."""

    def test_engine_directory_is_on_sys_path_once(self):
        """The engine folder is reachable, and listed exactly once."""
        engines_dir = pyrevit.ENGINES_DIR
        if not engines_dir:
            self.skipTest("no engine folder: not running from a pyRevit engine")

        occurrences = _count(sys.path, engines_dir)
        self.assertEqual(1, len(occurrences))

    def test_engine_directory_exists(self):
        """ENGINES_DIR is a real directory.

        It used to be assembled as ``bin/<net>/engines/<engine version>`` -
        a version number rather than a folder name - so it pointed at a path
        that does not exist while the real engine folder sat elsewhere.
        """
        engines_dir = pyrevit.ENGINES_DIR
        if not engines_dir:
            self.skipTest("no engine folder: not running from a pyRevit engine")

        self.assertTrue(op.isdir(engines_dir), "does not exist: {}".format(engines_dir))


class LiveSysPathTests(unittest.TestCase):
    """The invariant on the running engine's own ``sys.path``."""

    def test_no_folder_is_repeated(self):
        """Nothing on the live sys.path is listed twice."""
        repeated = _repeated()
        self.assertEqual(
            [], repeated, "duplicated sys.path entries: {}".format(repeated)
        )

    def test_dedupe_is_a_no_op_on_a_clean_path(self):
        """Dedupe leaves an already-clean sys.path byte-for-byte identical."""
        before = list(sys.path)
        dedupe_sys_path()
        self.assertEqual(before, list(sys.path))

    def test_rpw_import_does_not_restore_a_repeat(self):
        """Importing rpw.ui.forms.resources leaves the invariant intact.

        That module references the IronPython and WPF assemblies by path,
        which on IronPython appends the engine folder to sys.path - after
        framework.py has already collapsed it.
        """
        import rpw.ui.forms.resources  # noqa: F401 pylint: disable=unused-import

        repeated = _repeated()
        self.assertEqual(
            [], repeated, "duplicated sys.path entries: {}".format(repeated)
        )
