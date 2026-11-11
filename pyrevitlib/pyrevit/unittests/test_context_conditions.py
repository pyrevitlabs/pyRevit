# -*- coding: utf-8 -*-
"""Hosted unit tests for compiling bundle ``context`` strings.

Run from Revit via the DevTools "Run All Tests" button, which discovers every
``test_*`` module in this package. Regression tests for pyRevit #3988: a context
with several ``(...)`` groups used to keep only the last group, so a button could
be enabled where an earlier group said it must not be.

The tests call ``ScriptCommandExtendedAvail.FromContextDefinition`` on the
runtime assembly loaded into the host and evaluate against the active document,
so they need a document open; the evaluation tests skip without one.
"""

import unittest

from System import Object

from pyrevit import HOST_APP
from pyrevit.framework import AppDomain, Array

TEST_ENVIRONMENT = "Revit"
TEST_LEVEL = "Integration"

RUNTIME_ASSEMBLY_PREFIX = "pyRevitLabs.PyRevit.Runtime."
AVAIL_TYPE_NAME = "PyRevitLabs.PyRevit.Runtime.ScriptCommandExtendedAvail"


def _compile(context):
    for asm in AppDomain.CurrentDomain.GetAssemblies():
        name = asm.GetName().Name
        if (
            name.startswith(RUNTIME_ASSEMBLY_PREFIX)
            and name[len(RUNTIME_ASSEMBLY_PREFIX) :].isdigit()
        ):
            avail_type = asm.GetType(AVAIL_TYPE_NAME)
            if avail_type is not None:
                method = avail_type.GetMethod("FromContextDefinition")
                return method.Invoke(None, Array[Object]([context]))
    return None


def _group_strings(context):
    return sorted(str(group) for group in _compile(context).Condition.Conditions)


class ContextGroupCompilationTests(unittest.TestCase):
    """Every parenthesised group compiles to its own condition."""

    def setUp(self):
        """Skip when the runtime assembly is not loaded."""
        if _compile("(zero-doc)") is None:
            self.skipTest("pyRevit runtime assembly is not loaded")

    def test_all_groups_are_kept(self):
        """Both groups survive compilation."""
        self.assertEqual(
            _group_strings("(doc-project)&(doc-family)"),
            ["(Family)", "(Project)"],
        )

    def test_group_order_does_not_change_the_groups(self):
        """Group order does not change which groups are compiled."""
        self.assertEqual(
            _group_strings("(doc-family)&(doc-project)"),
            _group_strings("(doc-project)&(doc-family)"),
        )

    def test_three_groups_are_kept(self):
        """More than two groups are all kept."""
        self.assertEqual(
            _group_strings("(doc-project)&(doc-family)&(zero-doc)"),
            ["(Family)", "(Project)", "(zero-doc)"],
        )

    def test_group_separators_do_not_leak_into_later_groups(self):
        """A group's own separator stays with that group."""
        self.assertEqual(
            _group_strings("(doc-project|doc-family)&(zero-doc)"),
            ["(Project|Family)", "(zero-doc)"],
        )

    def test_negation_applies_to_its_own_group_only(self):
        """A leading ! negates the next group and no other."""
        self.assertEqual(
            _group_strings("!(doc-project)&(doc-family)"),
            ["!(Project)", "(Family)"],
        )


class ContextGroupEvaluationTests(unittest.TestCase):
    """Every group takes part in the result, whatever its position."""

    def setUp(self):
        """Skip without an active document or runtime assembly."""
        if HOST_APP.uiapp is None or HOST_APP.uiapp.ActiveUIDocument is None:
            self.skipTest("needs an active document")
        if _compile("(zero-doc)") is None:
            self.skipTest("pyRevit runtime assembly is not loaded")
        self.categories = HOST_APP.app.Create.NewCategorySet()

    def _matches(self, context):
        return _compile(context).Condition.IsMatch(HOST_APP.uiapp, self.categories)

    def test_contradicting_groups_never_match_in_either_order(self):
        """Groups that exclude each other never match, whatever the order."""
        self.assertFalse(self._matches("(doc-project)&(doc-family)"))
        self.assertFalse(self._matches("(doc-family)&(doc-project)"))

    def test_alternative_groups_match_in_either_order(self):
        """Any matching group is enough for an any-condition."""
        self.assertTrue(self._matches("(doc-project)|(doc-family)"))
        self.assertTrue(self._matches("(doc-family)|(doc-project)"))
