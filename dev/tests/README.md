# Testing infrastructure

`run_tests.py` owns shared C#/Python discovery and CI selection. `python/tooling/` verifies developer tools and the runner; `python/library/` verifies API-free Python library contracts. The separate `dev/checks/` and `dev/hooks/` directories own validators and formatting hooks.

From the repository root:

```powershell
python dev/tests/run_tests.py --list
python dev/tests/run_tests.py
```

See `docs/testing.md` for policy and `python/README.md` for Python fixture boundaries.

## Coverage and reporting policy

Owner: repository testing maintainers; suite owners review changes to their module baselines.

`coverage-baselines.json` records measured line and branch floors per Python source module or C# assembly/framework. The shared runner merges exact line hits and branch identities across suites, excludes test/vendor/generated source, and distinguishes linked production source from deployed assemblies. Missing established modules, regressions, and new measured modules without a baseline fail normal runs.

From the repository root, use `python dev/tests/run_tests.py --update-baselines` only after reviewing the reports. This explicit update can lower a floor; include a reason and follow-up for every reduction. It does not grant an automatic exception to the policy. Scope and denominator changes require review as well as percentage changes. Reports and inventory live in a unique `.test-results/<run>/` directory, so old reports cannot satisfy a new run.

Python reporting scope is declared in `pyproject.toml`. C# collectors include instrumented first-party code; assemblies never loaded by tests need dedicated suites and do not have measured coverage yet. No repository-wide percentage or performance budget is implied. See `docs/testing.md` for full rules.

## Initial baseline calibration

The initial floors use the lower measured line and branch coverage from the complete local run and [the clean Windows CI run](https://github.com/pyrevitlabs/pyRevit/actions/runs/39161623577). Both passed 138 Python and 1,882 C# tests without skips. Production-source denominators matched across environments; no source was excluded to make the gate pass.

The clean runner exercises fewer installed-product, extension-root, and configuration-discovery paths. For example, `ExtensionParser.GetExtensionRoots` traverses additional roots on a configured developer machine. Those differences also affect instrumented Common, Configurations, Configurations.Ini, PyRevit, and TargetApps.Revit dependencies. This calibration replaces machine-specific initial expectations with observed floors; it is not permission to lower established floors on future failures. The baseline calibration commit diff preserves the higher local measurements for review. Add controlled fixtures for the remaining machine-discovery paths before raising their floors; tests requiring the Revit API remain outside CI.

The C# suite layout cleanup also corrected Windows document identity in coverage aggregation. Differently cased MSBuild references to the same source file must contribute one denominator, not two. The `pyRevitLabs.PyRevit` baselines were recomputed from those same initial local/CI reports with normalized Windows paths: 2,046 lines per framework, replacing the duplicated 4,092-line denominator. No production source was removed. An explicit engine-version fixture and script-extension contracts preserve paths previously covered incidentally by the combined parser/runtime project.
