# -*- coding: utf-8 -*-
"""Revit-hosted engine-portability tests for the Python 3 migration.

Run from Revit via the pyRevit DevTools "Py3 Compat Tests" buttons
(doc-project context). One button runs on the attached IronPython engine,
its twin carries a ``#! python3`` shebang and runs the same suite on
CPython, so results can be compared per engine.

The suite exercises the compatibility hotspots cataloged in
IRONPYTHON_TO_PYTHON3_ANALYSIS.md sections 4.3-4.5 and 6.1: Python-2-only
idioms, IronPython-only CLR loading, out/ref marshaling, and heterogeneous
sorting. A failing test is a coverage signal, not necessarily a regression:
it marks a spot the current engine does not support yet.

Static counterpart: ``dev/scripts/check_py3_compat.py`` (no Revit needed).
"""

import importlib
import unittest

from pyrevit.compat import IRONPY, IRONPY3, NETCORE

# Markdown conversion needs ~768KB of stack under IronPython 3.4 (fat DLR
# frames + recursive parser; measured standalone against the IPY342 engine).
# On Revit's already-deep UI thread that overflows — an uncatchable
# StackOverflowException that kills the process — so markdown tests are
# excluded on that engine. The vendored package has no first-party runtime
# consumers (output.print_md renders via C#); it is public surface for
# third-party scripts only.
MARKDOWN_IPY3_SKIP = unittest.skipIf(
    IRONPY3,
    "markdown conversion can overflow the host thread's stack under "
    "IronPython 3 (hard-crashes Revit)",
)

# Path to a loadable .rfa for the out/ref-marshaling test; injected by the
# invoking tool because the fixture ships with the DevTools extension, not
# with pyrevitlib. Tests skip when unset.
FAMILY_FILE = None

# Modules every engine must import cleanly today.
CORE_MODULES = [
    "pyrevit",
    "pyrevit.compat",
    "pyrevit.coreutils",
    "pyrevit.coreutils.envvars",
    "pyrevit.coreutils.markdown",
    "pyrevit.coreutils.pyutils",
    "pyrevit.forms",
    "pyrevit.framework",
    "pyrevit.output",
    "pyrevit.revit",
    "pyrevit.script",
]

# Modules that load managed CLR assemblies at import time via
# IronPython-only APIs; expected to fail under CPython until the framework
# shim lands.
INTEROP_MODULES = [
    "pyrevit.interop.dxf",
    "pyrevit.interop.ifc",
]

# Interop modules whose import pulls native or externally-installed
# binaries into the Revit process (rhino3dm's native DLL, Desktop
# Connector assemblies). A bad native load is an access violation that
# kills the host, so these are opt-in.
INTEROP_NATIVE_MODULES = [
    "pyrevit.interop.adc",
    "pyrevit.interop.rhino",
]
TEST_NATIVE_INTEROP = False


def _import_failures(module_names):
    failures = []
    for name in module_names:
        try:
            importlib.import_module(name)
        except Exception as err:  # pylint: disable=broad-except
            failures.append("{}: {}".format(name, err))
    return failures


class ImportTests(unittest.TestCase):
    """Every supported module must be importable on the running engine."""

    def test_core_module_imports(self):
        """Core pyrevit modules import cleanly on this engine."""
        failures = _import_failures(CORE_MODULES)
        self.assertEqual(
            [], failures, "import failures:\n{}".format("\n".join(failures))
        )

    @unittest.skipIf(
        NETCORE,
        "interop assemblies (IxMilia.Dxf, Ifc.Net) are not shipped for "
        ".NET 8 hosts — dev/libs/netcore omits them",
    )
    def test_interop_module_imports(self):
        """interop modules import cleanly (needs the framework CLR shim)."""
        failures = _import_failures(INTEROP_MODULES)
        self.assertEqual(
            [], failures, "import failures:\n{}".format("\n".join(failures))
        )

    def test_interop_native_module_imports(self):
        """interop modules that load native/external binaries (opt-in)."""
        if not TEST_NATIVE_INTEROP:
            self.skipTest(
                "loads native binaries into the Revit process; set "
                "test_py3_compat.TEST_NATIVE_INTEROP to run"
            )
        failures = _import_failures(INTEROP_NATIVE_MODULES)
        self.assertEqual(
            [], failures, "import failures:\n{}".format("\n".join(failures))
        )


class Py2IdiomTests(unittest.TestCase):
    """Runtime behavior of the section 4.3 syntax residuals."""

    def test_basewrapper_repr(self):
        """ElementWrapper repr works (crashes on .iteritems under Py3)."""
        from pyrevit import revit
        from pyrevit.revit import db

        if not revit.doc or revit.doc.IsFamilyDocument:
            self.skipTest("Requires open project document")
        wrapper = db.ElementWrapper(revit.doc.ProjectInformation)
        self.assertIn("pyrevit.revit.db.ElementWrapper", repr(wrapper))

    @MARKDOWN_IPY3_SKIP
    def test_markdown_render(self):
        """Vendored markdown renders bold + non-ASCII text on this engine."""
        from pyrevit.coreutils import markdown

        html = markdown.markdown(u"**bold** café")
        self.assertIn("<strong>bold</strong>", html)
        self.assertIn(u"café", html)

    @MARKDOWN_IPY3_SKIP
    def test_markdown_safemode(self):
        """Raw-HTML postprocessor coerces the safeMode value to text."""
        from pyrevit.coreutils import markdown

        html = markdown.markdown(u"text <script>x</script>", safe_mode="escape")
        self.assertIn("&lt;script&gt;", html)

    @MARKDOWN_IPY3_SKIP
    def test_markdown_footnotes(self):
        """Footnote reference numbers are text-coerced for ElementTree."""
        from pyrevit.coreutils import markdown
        from pyrevit.coreutils.markdown.extensions.footnotes import (
            FootnoteExtension,
        )

        html = markdown.markdown(
            u"body[^1]\n\n[^1]: note", extensions=[FootnoteExtension()]
        )
        self.assertIn("footnote", html)

    @unittest.skipIf(
        IRONPY,
        "extra's attr_list needs re.Scanner, which IronPython's "
        ".NET-regex-based re module does not provide",
    )
    def test_markdown_in_html_block(self):
        """Markdown-inside-HTML tag placeholders are text-coerced (extra)."""
        from pyrevit.coreutils import markdown
        from pyrevit.coreutils.markdown.extensions.extra import ExtraExtension

        html = markdown.markdown(
            u'<div markdown="1">**bold**</div>', extensions=[ExtraExtension()]
        )
        self.assertIn("<strong>bold</strong>", html)

    @unittest.skipUnless(IRONPY, "forms WPF classes are IronPython-only")
    def test_forms_paramdef_truthiness(self):
        """ParamDef instances stay truthy on Python 3 engines (__bool__)."""
        from pyrevit.forms import _ipy

        param_def = _ipy.ParamDef(
            "name", False, None, False, False, None, "", True, None, False, 0
        )
        self.assertTrue(bool(param_def))

    @unittest.skipUnless(IRONPY, "forms WPF classes are IronPython-only")
    def test_forms_listitem_truthiness(self):
        """TemplateListItem truthiness follows checked state (__bool__)."""
        from pyrevit import forms

        unchecked = forms.TemplateListItem("item", checked=False)
        checked = forms.TemplateListItem("item", checked=True)
        self.assertFalse(
            bool(unchecked),
            "unchecked item is truthy; __nonzero__ is ignored on Python 3 "
            "engines without a __bool__ alias",
        )
        self.assertTrue(bool(checked))


class SortingTests(unittest.TestCase):
    """Heterogeneous-data sorting (the Settings.smartbutton fix pattern)."""

    def test_envvars_sortable_by_name(self):
        """Env vars dict sorts by str-coerced key without comparing values."""
        from pyrevit.coreutils import envvars

        env_vars = envvars.get_pyrevit_env_vars()
        items = sorted(env_vars.items(), key=lambda kv: str(kv[0]))
        self.assertEqual(len(items), len(env_vars))


class QueryStringLookupTests(unittest.TestCase):
    """String-identifier lookups in revit.db.query (isinstance str checks)."""

    def setUp(self):
        from pyrevit import revit

        if not revit.doc:
            self.skipTest("Requires open document")
        if revit.doc.IsFamilyDocument:
            self.skipTest("Requires project document, not family document")
        self.doc = revit.doc

    def test_get_param_by_name(self):
        """get_param resolves a parameter passed by name string."""
        from pyrevit.revit import query

        pinfo = self.doc.ProjectInformation
        param = None
        for candidate in pinfo.Parameters:
            param = candidate
            break
        if param is None:
            self.skipTest("ProjectInformation has no parameters")
        found = query.get_param(pinfo, param.Definition.Name)
        self.assertIsNotNone(found)

    def test_get_category_by_name(self):
        """get_category resolves a category passed by name string."""
        from pyrevit.revit import query

        category = None
        for candidate in self.doc.Settings.Categories:
            category = candidate
            break
        found = query.get_category(category.Name, doc=self.doc)
        self.assertIsNotNone(found)
        self.assertEqual(found.Name, category.Name)


class OutParamMarshalingTests(unittest.TestCase):
    """The two clr.Reference out/ref sites (sections 4.5 / 6.1)."""

    def setUp(self):
        from pyrevit import revit

        if not revit.doc:
            self.skipTest("Requires open document")
        if revit.doc.IsFamilyDocument:
            self.skipTest("Requires project document, not family document")
        self.doc = revit.doc

    def _rollback_transaction(self, name):
        from pyrevit import DB

        txn = DB.Transaction(self.doc, name)
        txn.Start()
        return txn

    def test_load_family_out_param(self):
        """create.load_family marshals the out-param family reference."""
        import os.path as op

        from pyrevit.revit import create

        if not FAMILY_FILE or not op.isfile(FAMILY_FILE):
            self.skipTest("No family file fixture provided")
        txn = self._rollback_transaction("py3compat-load-family")
        try:
            symbols = create.load_family(FAMILY_FILE, doc=self.doc)
            self.assertIsInstance(symbols, list)
        finally:
            txn.RollBack()

    def test_curve_intersect_out_param(self):
        """Curve.Intersect marshals the IntersectionResultArray ref.

        Exercises the exact out-param pattern of query.get_gridpoints
        (query.py's clr.Reference site) on pure geometry, with no element
        creation or view dependency.
        """
        import clr
        from pyrevit import DB

        line_ns = DB.Line.CreateBound(DB.XYZ(0, -10, 0), DB.XYZ(0, 10, 0))
        line_ew = DB.Line.CreateBound(DB.XYZ(-10, 0, 0), DB.XYZ(10, 0, 0))
        results = clr.Reference[DB.IntersectionResultArray]()
        intres = line_ns.Intersect(line_ew, results)
        self.assertEqual(intres, DB.SetComparisonResult.Overlap)
        self.assertEqual(results.Value.Size, 1)
