# Hosted Python library tests

Owner: the owning pyRevit library maintainers; the change author owns unassigned fixes until reassigned.

All modules declare `TEST_ENVIRONMENT = "Revit"` and remain compatible with the attached IronPython or CPython engine. They are inventoried without import and never executed in CI.

Attach the development clone locally, start Revit, and run DevTools Debug > Unit Tests > Run All Tests, or a focused module command. Supply the required open project/model elements/family fixtures. IronPython 3 requires a separate clone attachment. Record the exact commit, Revit year, engine, fixtures, command, pass/fail/skip counts, and any missing prerequisites.

Set `PYREVIT_TEST_JUNIT_PATH` before launching Revit for XML evidence. Use a fresh path per year/engine/run. Distinct module suites aggregate in that file and a repeated module replaces its previous result. Requested report-write failures propagate; unexpected successes fail the command even under IronPython 2.7. Local hosted evidence is separate from CI coverage.

See `docs/testing.md` for the full local procedure and classification rules.
