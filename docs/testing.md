# Testing

This page maps every test surface in the repository: where it lives, how it is triggered, whether CI runs it, and what is still uncovered. It exists because the surfaces are spread across four languages and three runtimes, and it is easy to add a test that nothing executes.

To run a change locally, see the workflow in [`dev-guide.md`](dev-guide.md). For how CI/CD is wired, see [`ci-cd.md`](ci-cd.md).

## Test surfaces at a glance

| Surface | Location | How it runs | In CI |
|---|---|---|---|
| In-Revit Python unit tests | `pyrevitlib/pyrevit/unittests/` | DevTools `Debug > Unit Tests` buttons, inside Revit | No |
| Standalone Python tests | `dev/scripts/test_standalone_*.py` | `python -m unittest discover -s dev/scripts -p 'test_standalone_*.py'` | Yes — `ci.yml` |
| C# unit tests | `dev/pyRevitLabs/tests/`, `dev/pyRevitLoader/pyRevitExtensionParserTester/`, `dev/pyRevitLabs/pyRevitLabs.UnitTests/` | `build/` pipeline (`dotnet run -- ci`) | Yes — `ci.yml`, two projects filtered |
| Build pipeline tests | `build/tests/Build.Tests.csproj` | `dotnet test build/tests/Build.Tests.csproj` | Yes — `ci.yml` |
| Revit integration | [`.github/workflows/revit-integration.yml`](https://github.com/pyrevitlabs/pyRevit/blob/develop/.github/workflows/revit-integration.yml) | Self-hosted Revit runner, journal inspection | Yes — self-hosted runner |
| DevTools end-to-end buttons | `extensions/pyRevitDevTools.extension/` | Manual, inside Revit | No |

## In-Revit Python unit tests

`pyrevitlib/pyrevit/unittests/` holds the hosted suite: 16 `test_*.py` modules plus `runner.py` and `junit.py`. `runner.py` is the shared entry point; module buttons call `run_module_tests` (report only) or `assert_module_tests_successful` (raise on failure, so the button fails visibly).

The suite only runs inside a Revit session, through the DevTools **Unit Tests** pulldown. Those buttons come in two kinds, and the naming does not distinguish them:

| Buttons backed by `pyrevit.unittests` | Buttons that are standalone assertions |
|---|---|
| Run All Tests, Config Module Tests, Credentials Module Tests, Output Window Tests, Query get_name Tests, Revit Module Tests, Routes Module Tests, Script Module Tests, Py3 Compat Tests, Py3 Compat Tests (CPython) | CoreUtils Module Tests (increment/decrement parsing), pyRevitLabs Module Tests, Appdata Module Tests, Forms Module Tests |

`Run All Tests` discovers every `test_` module in the package, so modules without a dedicated button (`test_keynote_locks`, `test_revit_handle_contract`, `test_sys_path`, `test_versionmgr`) are only reached through it.

`Py3 Compat Tests` runs `test_py3_compat` on whichever IronPython engine the clone is attached with; `Py3 Compat Tests (CPython)` runs it on the CPython engine. A bundle cannot select an engine *version* — engine identity is only `ironpython` or `cpython` — so the `IRONPY3`-gated cases in `test_py3_compat.py` are only reachable by attaching the clone with the IronPython 3 engine.

Nothing in CI runs this suite; it needs an installed Revit.

## Standalone Python tests

`dev/scripts/test_standalone_*.py` are plain `unittest` modules that do not need Revit. CI runs them with:

```bash
python -m unittest discover -s dev/scripts -p 'test_standalone_*.py' -v
```

## C# test suites

The `build/` pipeline runs these after the build outputs exist. The runner is [`build/Modules/TestConfigurationsModule.cs`](https://github.com/pyrevitlabs/pyRevit/blob/develop/build/Modules/TestConfigurationsModule.cs), reached through `dotnet run -- ci`, which `ci.yml` and `revit-integration.yml` invoke.

| Project | Scope run in CI |
|---|---|
| `pyRevitLabs.Configurations.Tests` | all |
| `pyRevitLabs.Configurations.Ini.Tests` | all |
| `pyRevitLabs.PyRevit.Runtime.CPython.Tests` | all |
| `pyRevitLabs.PyRevit.Runtime.Agent.Tests` | all |
| `pyRevitCLI.Tests` | all |
| `pyRevitLabs.UnitTests` | filtered (net48 and net8.0-windows) |
| `pyRevitExtensionParserTester` | filtered (net8.0-windows) |

The two filtered projects carry the filters inline in `TestConfigurationsModule.cs`. Test classes outside a filter compile and can be run by hand, but CI never executes them.

## Build pipeline tests

`build/tests/Build.Tests.csproj` tests the pipeline itself and is run separately from the pipeline:

```bash
dotnet test build/tests/Build.Tests.csproj -c Release
```

## Revit integration tests

[`revit-integration.yml`](ci-cd.md#revit-integration-tests) signs `bin/` with a throwaway certificate, launches every supported Revit year on a self-hosted runner, and fails if any session shows the unsigned add-in dialog. It answers whether Revit loads the build cleanly; it does not run the Python unit tests.

## DevTools end-to-end buttons

`extensions/pyRevitDevTools.extension/pyRevitDev.tab/` is not a test suite. It mixes runnable assertions with demos, interactive probes, and debugger launchers — roughly 127 command bundles across five panels. Only the `Debug` panel buttons participate in testing, and only the module tests have an objective pass/fail; the rest are judged per button, and several block on user input by design (input stream, XAML forms, progress bars, debugger attach).

## Known issues and things to address

1. **The hosted Python suite never runs in CI.** It needs an installed Revit, so it requires a self-hosted runner or a documented local procedure.
2. **Two C# projects run only a filtered subset.** `pyRevitExtensionParserTester` has far more test classes than the filter selects, including the parser, layout, and bundle-metadata tests. Widening the filter is the cheapest coverage win in the repository.
3. **`IRONPY3` coverage is unreachable from the ribbon.** Engine identity is `ironpython` / `cpython` only, so no bundle can select IronPython 3.
4. **The Python and C# component-tree parsers disagree on layout.** The Python path (`pyrevit.extensions.genericcomps`) drops components not listed in `layout`; the C# path (`pyRevitExtensionParser`) appends them. The ribbon uses C#, so the Python rule only shows up in other consumers.
5. **Some test bundles depend on a CDN at runtime.** `Test Vue` and `Test D3` load their JavaScript from `unpkg.com`, so they fail without network access.
6. **Some tests are skipped on a .NET 8+ host.** A few cases need interop assemblies not shipped for .NET 8+, sit behind an opt-in flag, or rely on fixtures that a single button injects.
