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
"""

import os.path as op
import shutil
import sys
import tempfile
import unittest

import pyrevit
from pyrevit import add_to_sys_path, dedupe_sys_path


def _key(path):
    """Return the comparison key pyRevit uses for a sys.path entry."""
    return op.normcase(op.normpath(path))


def _count(paths, folder):
    """Return how many of the given entries resolve to the same folder."""
    return [p for p in paths if _key(p) == _key(folder)]


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
        counts = {}
        for entry in sys.path:
            if not isinstance(entry, str) or not entry:
                continue
            key = _key(entry)
            counts[key] = counts.get(key, 0) + 1

        repeated = sorted(path for path, count in counts.items() if count > 1)
        self.assertEqual(
            [], repeated, "duplicated sys.path entries: {}".format(repeated)
        )

    def test_dedupe_is_a_no_op_on_a_clean_path(self):
        """Dedupe leaves an already-clean sys.path byte-for-byte identical."""
        before = list(sys.path)
        dedupe_sys_path()
        self.assertEqual(before, list(sys.path))
