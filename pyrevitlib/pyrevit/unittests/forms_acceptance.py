"""Run live forms acceptance against temporary Revit fixture elements.

The outer transaction group always rolls back. The runner is suitable for a
pyRevit MCP dry run or a DevTools command and never saves the project.
"""

import sys
import unittest

from pyrevit import DB, coreutils, revit
from pyrevit.revit.db import create, query
from pyrevit.unittests import test_forms_parity


def run(doc=None):
    """Drive the shared forms suite with real views, sheets and parameters.

    Temporary fixtures are committed only inside a transaction group which is
    rolled back even on failure. An open, writable project is required.

    Returns:
        dict: Engine version, test counts, failures and errors.
    """
    doc = doc or revit.doc
    suffix = coreutils.new_uuid()[:8]
    group = DB.TransactionGroup(doc, "Forms acceptance fixtures")
    group.Start()
    try:
        with revit.Transaction("Create forms acceptance fixtures", doc=doc):
            sheet = create.create_sheet("FORMS-" + suffix, "Forms parity", doc=doc)
            revision = create.create_revision(description="Forms parity", doc=doc)
            schedule = create.create_schedule(
                DB.BuiltInCategory.OST_Walls,
                [],
                view_name="Forms parity " + suffix,
                doc=doc,
            )
            view = doc.ActiveView
            template = view.CreateViewTemplate()
            template.Name = "Forms parity template " + suffix
        test_forms_parity.FIXTURE.update(
            {
                "doc": doc,
                "view": view,
                "sheet": sheet,
                "revision": revision,
                "schedule": schedule,
                "template": template,
                "level": query.find_level(doc=doc),
            }
        )
        suite = unittest.defaultTestLoader.loadTestsFromModule(test_forms_parity)
        report = unittest.TextTestRunner(verbosity=2).run(suite)
        return {
            "python": sys.version,
            "passed": report.wasSuccessful(),
            "run": report.testsRun,
            "skipped": [(str(test), reason) for test, reason in report.skipped],
            "failures": [(str(test), error) for test, error in report.failures],
            "errors": [(str(test), error) for test, error in report.errors],
        }
    finally:
        test_forms_parity.FIXTURE.clear()
        group.RollBack()
