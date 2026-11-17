"""Tests for resolving the load timeline type in pyrevit._perf."""

import importlib.util
import os.path as op
import sys
import types
import unittest
from pathlib import Path


TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

ROOT_DIR = str(Path(__file__).resolve().parents[4])
PERF_PATH = op.join(ROOT_DIR, "pyrevitlib", "pyrevit", "_perf.py")


class _FakeTimeline(object):
    ElapsedMilliseconds = 1500.0


class _FakeLoadTimeline(object):
    Active = _FakeTimeline()


class _FakeClr(object):
    def __init__(self):
        self.resolvable = False

    def AddReference(self, name):
        if not self.resolvable:
            raise IOError("Could not add reference to assembly " + name)


def _load_perf():
    spec = importlib.util.spec_from_file_location("_perf_under_test", PERF_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ElapsedLoadSecondsTests(unittest.TestCase):
    """The load timeline type is resolved even if the first lookup fails.

    Regression coverage for pyrevitlabs/pyRevit#4108.
    """

    def setUp(self):
        """Install a fake clr and timeline, then load a fresh _perf module."""
        self.clr = _FakeClr()
        common = types.ModuleType("pyRevitLabs.Common")
        common.LoadTimeline = _FakeLoadTimeline
        namespace = types.ModuleType("pyRevitLabs")
        namespace.Common = common
        self._saved = dict(
            (name, sys.modules.get(name))
            for name in ("clr", "pyRevitLabs", "pyRevitLabs.Common", "pyrevit.labs")
        )
        sys.modules["clr"] = self.clr
        sys.modules["pyRevitLabs"] = namespace
        sys.modules["pyRevitLabs.Common"] = common
        sys.modules.pop("pyrevit.labs", None)
        self.perf = _load_perf()

    def tearDown(self):
        """Restore the modules replaced in setUp."""
        for name, module in self._saved.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module

    def test_timeline_resolved_at_use_after_labs_entry_checkpoint(self):
        """A checkpoint taken while pyrevit.labs is importing does not end retries."""
        self.assertIsNone(self.perf.elapsed_load_seconds())
        sys.modules["pyrevit.labs"] = types.ModuleType("pyrevit.labs")
        self.perf.mark("pyrevit.labs:entry")
        self.clr.resolvable = True
        self.assertEqual(1.5, self.perf.elapsed_load_seconds())

    def test_checkpoints_do_not_retry_a_failed_lookup(self):
        """Checkpoints stay cheap: only elapsed_load_seconds retries."""
        self.assertIsNone(self.perf.elapsed_load_seconds())
        self.clr.resolvable = True
        self.perf.mark("any")
        self.assertIsNone(self.perf._active_timeline())

    def test_timeline_resolved_when_reference_works_first_time(self):
        """A lookup that succeeds at once reports the elapsed seconds."""
        self.clr.resolvable = True
        self.assertEqual(1.5, self.perf.elapsed_load_seconds())


if __name__ == "__main__":
    unittest.main()
