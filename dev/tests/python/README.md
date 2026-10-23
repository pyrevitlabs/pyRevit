# Repository Python tests

Owner: repository tooling maintainers, or the owning library maintainers for standalone library tests. The change author owns unassigned fixes until reassigned.

- `tooling/`: shared runner, Python compatibility checker, and config API checker contracts.
- `library/`: automation markers, event handlers, logging, Keynote read errors, and hosted test reporting. These use isolated module doubles or source extraction to avoid importing the Revit-dependent `pyrevit` package.

From the repository root:

```powershell
python dev/tests/run_tests.py --install-dependencies
python dev/tests/run_tests.py --language python
pipenv run test-library
```

Discovery includes every `test_*.py` module, including compatibility and automation-marker checkers. Declare literal `TEST_ENVIRONMENT` and `TEST_LEVEL` defaults in each module. HostFree modules must be safe to import without Revit. Existing unittest cases run through pytest; root `conftest.py` applies class defaults and method marker overrides, records tags, and rejects skipped selected cases.

Tests use temporary files, local module doubles, or extracted helpers. Keep fixture cleanup with the owning suite. Contract checks do not claim execution of source merely inspected as text. JUnit and coverage artifacts have unique run paths below `.test-results/`. Python coverage scope is explicit in `pyproject.toml`; extend it when adding a measured module and review its baseline.

See `docs/testing.md` for policy and `dev/tests/README.md` for baseline review.

`pipenv run test-standalone` remains an alias for the library suites. Hosted Python tests remain under `pyrevitlib/pyrevit/unittests/` and are excluded from CI.
