# Coverage and reporting policy

Owner: repository testing maintainers; suite owners review changes to their module baselines.

`coverage-baselines.json` records measured line and branch floors per Python source module or C# assembly/framework. The shared runner merges exact line hits and branch identities across suites, excludes test/vendor/generated source, and distinguishes linked production source from deployed assemblies. Missing established modules, regressions, and new measured modules without a baseline fail normal runs.

From the repository root, use `python dev/scripts/run_tests.py --update-baselines` only after reviewing the reports. This explicit update can lower a floor; include a reason and follow-up for every reduction. It does not grant an automatic exception to the policy. Scope and denominator changes require review as well as percentage changes. Reports and inventory live in a unique `.test-results/<run>/` directory, so old reports cannot satisfy a new run.

Python reporting scope is declared in `pyproject.toml`. C# collectors include instrumented first-party code; assemblies never loaded by tests need dedicated suites and do not have measured coverage yet. No repository-wide percentage or performance budget is implied. See `docs/testing.md` for full rules.
