# -*- coding: utf-8 -*-
"""Hosted unit tests for the pyrevit.revit module surface.

Run from Revit via the DevTools "Revit Module Tests" button (zero-doc
context) or the "Run All Tests" aggregator. Document-dependent helpers
are exercised with a skip-unless-doc pattern so the suite stays useful
on an empty Revit session.
"""

import unittest


class HostAppTests(unittest.TestCase):
    """HOST_APP application wrapper sanity checks."""

    def setUp(self):
        """Grab the host application wrapper."""
        from pyrevit import HOST_APP

        self.host_app = HOST_APP

    def test_host_app_available(self):
        """HOST_APP wraps a running Revit application."""
        self.assertIsNotNone(self.host_app)
        self.assertIsNotNone(self.host_app.app)

    def test_version_accessors(self):
        """Version accessors report a numeric Revit version."""
        version = self.host_app.is_newer_than(2000)
        self.assertTrue(version)

    def test_uiapp_application(self):
        """Controlled application exposes the UI application."""
        self.assertIsNotNone(self.host_app.uiapp)


class ModuleSurfaceTests(unittest.TestCase):
    """pyrevit.revit submodules expose their documented entry points."""

    def test_query_module_entry_points(self):
        """Query module exposes core lookup helpers."""
        from pyrevit.revit import query

        for name in (
            "get_builtincategory",
            "get_category",
            "get_param",
            "get_all_elements",
            "get_elements_by_class",
            "get_name",
        ):
            self.assertTrue(callable(getattr(query, name)))

    def test_selection_module_entry_points(self):
        """Selection module exposes selection helpers."""
        from pyrevit.revit import selection

        self.assertTrue(callable(selection.get_selection))

    def test_transaction_classes(self):
        """Database module exposes Transaction and parameter wrappers."""
        from pyrevit.revit import db

        self.assertTrue(hasattr(db, "Transaction"))
        self.assertTrue(hasattr(db, "ProjectParameter"))

    def test_events_module_entry_points(self):
        """Events module exposes subscribe/unsubscribe helpers."""
        from pyrevit.revit import events

        self.assertTrue(callable(events.handle))
        self.assertTrue(callable(events.stop_events))


class DocumentGatedTests(unittest.TestCase):
    """Helpers that need an active project document (skip when absent)."""

    def setUp(self):
        """Skip unless a project document is active."""
        from pyrevit import revit

        if not revit.doc:
            self.skipTest("Requires open document")
        if revit.doc.IsFamilyDocument:
            self.skipTest("Requires project document, not family document")
        self.doc = revit.doc

    def test_get_doc_categories(self):
        """Document categories list non-empty on a project document."""
        from pyrevit.revit import query

        categories = list(query.get_doc_categories(doc=self.doc))
        self.assertTrue(categories)

    def test_get_all_elements(self):
        """Element collection returns elements of the active document."""
        from pyrevit.revit import query

        elements = query.get_all_elements(doc=self.doc)
        self.assertTrue(elements)

    def test_get_name_on_element(self):
        """Name lookup reads element names without schema errors."""
        from pyrevit.revit import query

        name = query.get_name(self.doc.ProjectInformation)
        self.assertIsInstance(name, str)

    def test_get_builtincategory_round_trip(self):
        """Category resolution maps a category back to its enum value."""
        from pyrevit import DB
        from pyrevit.revit import query

        bicat = query.get_builtincategory(DB.BuiltInCategory.OST_Walls, doc=self.doc)
        self.assertEqual(DB.BuiltInCategory.OST_Walls, bicat)
