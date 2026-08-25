# -*- coding: utf-8 -*-
"""Revit-hosted tests for pyrevit.revit.db.query.get_name.

Run from Revit via the pyRevit DevTools "Query get_name Tests" button
(doc-project context). Validates workset support and IronPython 2 Name fallback.
"""

import unittest

from Autodesk.Revit.DB import Element  # pylint: disable=E0401

from pyrevit import DB, revit
from pyrevit.compat import IRONPY2
from pyrevit.revit.db import query

try:
    basestring  # noqa: B018 pylint: disable=used-before-assignment
except NameError:
    basestring = str  # Python 3

_TEXT_TYPES = (basestring,)


def _is_text(value):
    """Return True if value is a text type for the active Python version."""
    return isinstance(value, _TEXT_TYPES)


def _first_workset(doc):
    """Return the first workset in the document, or None."""
    for workset in DB.FilteredWorksetCollector(doc).ToWorksets():
        return workset
    return None


def _first_of_class(doc, element_class):
    """Return the first element of the given class, or None.

    Iterates the collector directly so IronPython can index .NET IList from
    ToElements() unreliably with ``[0]``.
    """
    collector = DB.FilteredElementCollector(doc).OfClass(element_class)
    for element in collector:
        return element
    return None


def _first_placed_room(doc):
    """Return the first placed Room (Area > 0), or None.

    FilteredElementCollector.OfClass(DB.Architecture.Room) is invalid on current
    Revit builds; collect ``DB.SpatialElement`` and keep ``DB.Architecture.Room``.
    """
    for room in DB.FilteredElementCollector(doc).OfClass(DB.SpatialElement):
        if not isinstance(room, DB.Architecture.Room):
            continue
        if query.is_placed(room):
            return room
    return None


class GetNameQueryTests(unittest.TestCase):
    """Tests for query.get_name with Workset and Element types."""

    def setUp(self):
        if revit.doc.IsFamilyDocument:
            self.skipTest("Requires model document, not family document")

    def test_get_name_workset(self):
        """get_name returns workset.Name for DB.Workset."""
        workset = _first_workset(revit.doc)
        if workset is None:
            self.skipTest("No worksets in document")
        name = query.get_name(workset)
        self.assertTrue(_is_text(name))
        self.assertEqual(name, workset.Name)

    def test_get_name_wall_type_string(self):
        """get_name returns a string for WallType; IPY2 matches GetValue."""
        wall_type = _first_of_class(revit.doc, DB.WallType)
        if wall_type is None:
            self.skipTest("No WallType in document")
        name = query.get_name(wall_type)
        self.assertTrue(
            _is_text(name),
            "get_name(WallType) must be text, got {0!r}".format(type(name)),
        )
        if IRONPY2:
            self.assertEqual(name, Element.Name.GetValue(wall_type))

    def test_get_name_family_symbol_string(self):
        """get_name returns a string for FamilySymbol; IPY2 matches GetValue."""
        symbol = _first_of_class(revit.doc, DB.FamilySymbol)
        if symbol is None:
            self.skipTest("No FamilySymbol in document")
        name = query.get_name(symbol)
        self.assertTrue(
            _is_text(name),
            "get_name(FamilySymbol) must be text, got {0!r}".format(type(name)),
        )
        if IRONPY2:
            self.assertEqual(name, Element.Name.GetValue(symbol))

    def test_get_name_room_string(self):
        """get_name returns a string for Room when rooms exist; IPY2 matches GetValue."""
        room = _first_placed_room(revit.doc)
        if room is None:
            self.skipTest("No placed Room in document")
        name = query.get_name(room)
        self.assertTrue(
            _is_text(name),
            "get_name(Room) must be text, got {0!r}".format(type(name)),
        )
        if IRONPY2:
            self.assertEqual(name, Element.Name.GetValue(room))
