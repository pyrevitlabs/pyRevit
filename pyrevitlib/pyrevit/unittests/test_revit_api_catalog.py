# -*- coding: utf-8 -*-
"""Revit-hosted check that the Revit API change catalog matches the live API.

The static linter ``dev/scripts/check_revit_api_compat.py`` trusts
``dev/scripts/revit_api_catalog/catalog.json``, which is generated offline
from each Revit year's RevitAPI/RevitAPIUI assemblies. Running this suite in
a given Revit confirms that every cataloged type and member exists exactly
when the catalog says it does for that year, catching extraction mistakes and
update-release drift that no offline step can see. Run it from the pyRevit
DevTools "Revit API Catalog Tests" button in each Revit version you have.

The lint itself runs in CI without Revit; this suite only validates its data.
It is opt-in: the "Run All Tests" button leaves it out, because it resolves
hundreds of types against whichever Revit build is installed.

Note:
    Years that only some update releases have an entry in (``partial``) are
    not checked, since the result depends on which update is installed.
    Skips when the catalog is absent (installed builds ship without ``dev/``)
    or when the running Revit year is outside the cataloged years.
"""

import io
import json
import os
import unittest

from pyrevit import HOME_DIR, HOST_APP

CATALOG_PATH = os.path.join(
    HOME_DIR, "dev", "scripts", "revit_api_catalog", "catalog.json"
)
MAX_REPORTED = 40
REVIT_NAMESPACES = ("Autodesk.Revit.DB", "Autodesk.Revit.UI")


def _ranges_to_years(ranges):
    """Expand inclusive [first, last] runs into a year set."""
    years = set()
    for first, last in ranges or []:
        years.update(range(first, last + 1))
    return years


def _expected(entry, year, all_years):
    """True/False if the year must have/lack the entry; None if either is fine.

    ``partial`` years are those only some update releases of have the entry,
    so whether this Revit has it depends on its update.
    """
    if year in _ranges_to_years(entry.get("partial")):
        return None
    if "avail" not in entry:
        return year in all_years
    return year in _ranges_to_years(entry["avail"])


def _resolve(full_name):
    """Import a dotted .NET type name; raises if any part is missing."""
    parts = full_name.split(".")
    for cut in range(len(parts) - 1, 0, -1):
        try:
            obj = __import__(".".join(parts[:cut]), fromlist=["*"])
        except ImportError:
            continue
        for part in parts[cut:]:
            obj = getattr(obj, part)
        return obj
    raise ImportError(full_name)


def _mismatch_report(problems):
    """Readable, length-capped list of mismatches."""
    shown = sorted(problems)[:MAX_REPORTED]
    more = len(problems) - len(shown)
    return "\n".join(shown) + ("\n... and {} more".format(more) if more > 0 else "")


class RevitApiCatalogTests(unittest.TestCase):
    """Cataloged availability agrees with the running Revit's API."""

    @classmethod
    def setUpClass(cls):
        """Load the catalog, or skip when absent or out of range."""
        if not os.path.exists(CATALOG_PATH):
            raise unittest.SkipTest("catalog not found: {}".format(CATALOG_PATH))
        with io.open(CATALOG_PATH, encoding="utf-8") as handle:
            cls.catalog = json.load(handle)
        try:
            cls.year = int(HOST_APP.version)
        except (TypeError, ValueError):
            raise unittest.SkipTest(
                "cannot read the Revit year from {!r}".format(HOST_APP.version)
            )
        cls.label = "Revit {}".format(HOST_APP.subversion or cls.year)
        if cls.year not in cls.catalog["years"]:
            raise unittest.SkipTest(
                "Revit {} is outside the catalog ({}-{})".format(
                    cls.year, cls.catalog["years"][0], cls.catalog["years"][-1]
                )
            )

    def _live_types(self):
        """Map each cataloged type to its live class, or None if absent.

        Only a missing name counts as absent. A Revit namespace that cannot be
        imported, or any other error while resolving, fails the test as an
        environment problem instead of blaming the catalog.
        """
        for namespace in REVIT_NAMESPACES:
            try:
                __import__(namespace, fromlist=["*"])
            except ImportError as err:
                self.fail("cannot import {}: {!r}".format(namespace, err))
        live = {}
        unresolved = []
        for type_name in self.catalog["types"]:
            try:
                live[type_name] = _resolve(type_name)
            except (AttributeError, ImportError):
                live[type_name] = None
            except Exception as err:
                unresolved.append("{}: {!r}".format(type_name, err))
        self.assertFalse(
            unresolved,
            "could not inspect these types (not a catalog mismatch):\n"
            + _mismatch_report(unresolved),
        )
        return live

    def test_types_exist_when_cataloged(self):
        """A cataloged type is importable exactly in its available years."""
        problems = []
        all_years = self.catalog["years"]
        for type_name, cls_obj in self._live_types().items():
            entry = self.catalog["types"][type_name]
            expected = _expected(entry, self.year, all_years)
            if expected is not None and expected != (cls_obj is not None):
                problems.append(
                    "{}: expected {} in {}".format(
                        type_name, "present" if expected else "absent", self.label
                    )
                )
        self.assertFalse(problems, _mismatch_report(problems))

    def test_members_exist_when_cataloged(self):
        """A cataloged member is reachable exactly in its available years."""
        problems = []
        all_years = self.catalog["years"]
        for type_name, cls_obj in self._live_types().items():
            if cls_obj is None:
                continue
            type_entry = self.catalog["types"][type_name]
            for member, entry in type_entry.get("members", {}).items():
                if member.startswith("."):
                    continue
                expected = _expected(entry, self.year, all_years)
                if expected is not None and expected != hasattr(cls_obj, member):
                    problems.append(
                        "{}.{}: expected {} in {}".format(
                            type_name,
                            member,
                            "present" if expected else "absent",
                            self.label,
                        )
                    )
        self.assertFalse(problems, _mismatch_report(problems))
