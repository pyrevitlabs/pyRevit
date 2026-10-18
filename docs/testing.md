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

| Buttons backed by `pyrevit.unittests` | Other module buttons (assertions or manual probes) |
|---|---|
| Run All Tests, Config Module Tests, Credentials Module Tests, Output Window Tests, Query get_name Tests, Revit Module Tests, Routes Module Tests, Script Module Tests, Py3 Compat Tests, Py3 Compat Tests (CPython) | CoreUtils Module Tests (increment/decrement parsing), pyRevitLabs Module Tests, Appdata Module Tests, Forms Module Tests |

`Run All Tests` discovers every `test_` module in the package, so modules without a dedicated button (`test_keynote_locks`, `test_revit_handle_contract`, `test_sys_path`, `test_versionmgr`) are only reached through it.

An open project does not guarantee that every case runs. Some cases require particular model content or family fixtures injected by the individual compatibility buttons. CoreUtils prints comparisons without failing the command on a mismatch, and Forms opens interactive dialogs; neither provides an automated suite result.

`Py3 Compat Tests` runs `test_py3_compat` on whichever IronPython engine the clone is attached with; `Py3 Compat Tests (CPython)` runs it on the CPython engine. A bundle cannot select an engine *version* — engine identity is only `ironpython` or `cpython` — so the `IRONPY3`-gated cases in `test_py3_compat.py` are only reachable by attaching the clone with the IronPython 3 engine.

Nothing in CI runs this suite; it needs an installed Revit.

## Standalone Python tests

`dev/scripts/test_standalone_*.py` are plain `unittest` modules that do not need Revit. CI runs them with:

```bash
python -m unittest discover -s dev/scripts -p 'test_standalone_*.py' -v
```

Three other host-free modules live beside them: `test_automation_marker.py`, `test_check_config_api.py`, and `test_check_py3_compat.py`. They have separate `Pipfile` commands, but the CI discovery pattern above excludes them. To run all seven modules locally:

```bash
python -m unittest discover -s dev/scripts -p 'test_*.py' -v
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

[`revit-integration.yml`](ci-cd.md#revit-integration-tests) signs `bin/` with a throwaway certificate, launches Revit 2022–2027 by default on a self-hosted runner, and fails if any session shows the unsigned add-in dialog. Its accepted year range excludes supported Revit 2021. It answers whether Revit loads the build cleanly; it does not run the Python unit tests.

## DevTools end-to-end buttons

`extensions/pyRevitDevTools.extension/pyRevitDev.tab/` is not a test suite. It mixes runnable assertions with demos, interactive probes, and debugger launchers — roughly 127 command bundles across five panels. Only the `Debug` panel buttons participate in testing, and only the module tests have an objective pass/fail; the rest are judged per button, and several block on user input by design (input stream, XAML forms, progress bars, debugger attach).

## Known issues and things to address

1. **The hosted Python suite never runs in CI.** It needs an installed Revit, so it requires a self-hosted runner or a documented local procedure.
2. **Two C# projects run only a filtered subset.** `pyRevitExtensionParserTester` has far more test classes than the filter selects, including the parser, layout, and bundle-metadata tests. Excluded tests need triage before expanding CI: some expectations track mutable DevTools layouts and titles, while others require Revit assemblies. New classes are excluded unless someone updates the allowlist.
3. **`IRONPY3` coverage requires a separate attachment.** Engine identity is `ironpython` / `cpython` only, so no bundle can select IronPython 3 directly. Attach the clone with that engine before running its ribbon tests.
4. **The Python and C# component-tree parsers disagree on layout.** The Python path (`pyrevit.extensions.genericcomps`) drops components not listed in `layout`; the C# path (`pyRevitExtensionParser`) appends them. The ribbon uses C#, so the Python rule only shows up in other consumers.
5. **Some test bundles depend on a CDN at runtime.** `Test Vue` and `Test D3` load their JavaScript from `unpkg.com`, so they fail without network access.
6. **Some tests are skipped on a .NET 8+ host.** A few cases need interop assemblies not shipped for .NET 8+, sit behind an opt-in flag, or rely on fixtures that a single button injects.
7. **Host-free Python discovery is incomplete.** CI omits the three checker and automation-marker test modules listed above.
8. **Test builds can deploy into the active clone.** Shared build targets copy assemblies into `bin/`; a running Revit session can lock these files and prevent a test build from completing.

## Consolidation roadmap (proposed)

The following is planned follow-up work. The inventory above describes current behavior; these locations, commands, and coverage gates are not implemented yet.

### 1. Unify discovery and execution

Provide one repository test entry point with explicit host-free, Revit-hosted, and manual groups. Local development and CI should use the same suite selection. Start by including all `dev/scripts/test_*.py` modules in the host-free group.

Inventory every first-party test project and module with its command, required runtime, fixtures, and CI status. Add a discovery check that fails when a new suite has no execution group. Keep vendored dependencies out of this inventory.

For C#, replace class-name allowlists with capability categories such as `RequiresRevit`, `RequiresNetwork`, and `RequiresElevation`. Ordinary new tests should run by default. Triage excluded failures first, distinguish stale expectations from product defects and missing dependencies, and record any temporary exclusions with a reason and tracked follow-up.

The long `FullyQualifiedName` expressions in `TestConfigurationsModule` are temporary migration scaffolding. They couple build orchestration to individual test names: renaming a class can silently remove coverage, and adding a regression test requires editing the build pipeline. Splitting the string across lines would improve readability without fixing that dependency.

The target architecture should separate three responsibilities:

- Test projects own capability metadata on their tests, using the category or trait mechanism of their test framework.
- Named execution profiles own project/framework selection and capability filters. Keep these profiles in one version-controlled configuration consumed by both local commands and CI.
- The build runner executes a requested profile and publishes results. It should not enumerate test classes or methods.

Start with a host-free profile that runs ordinary tests by default, then add explicit profiles for Revit, network, and elevated environments. During migration, retain narrowly scoped exclusions for known failures with tracked removal criteria. Validate profile discovery so an expected project or selection returning zero tests fails visibly. Renaming an ordinary test or adding one to an existing project must not require a build-runner change.

Completion means a new host-free test runs locally and in CI without editing an allowlist, and every excluded suite has an explicit execution path.

### 2. Consolidate locations and fixtures

Move suites only after discovery is reliable, in separate changes that update project references, solution membership, build paths, and documentation together.

| Current location | Proposed destination or responsibility |
|---|---|
| `dev/scripts/test_*.py` | `dev/tests/python/`, with shared harnesses and fixtures beside the suites |
| `dev/pyRevitLabs/tests/`, `dev/pyRevitLabs/pyRevitLabs.UnitTests/`, `dev/pyRevitLoader/pyRevitExtensionParserTester/` | `dev/tests/dotnet/`, retaining separate projects for distinct runtime requirements |
| `build/tests/` | Keep beside the build pipeline, registered with the common entry point |
| `pyrevitlib/pyrevit/unittests/` | Keep importable for hosted commands until the runner and package dependencies are decoupled |
| DevTools command scripts | Thin launchers for shared suites, or explicitly labeled manual checks and examples |

Replace parser fixtures that depend on the changing DevTools extension with small dedicated extension fixtures. Retain a focused smoke test for the real DevTools layout, updating its expectations when ribbon metadata changes. Define the intended Python/C# layout contract and test both parsers against shared cases.

Move reusable assertions out of ribbon scripts into the shared suite. Separate automated tests, interactive checks, and examples in the ribbon so a successful command cannot be mistaken for verified assertions. Make test builds independent of deployment into the active clone's `bin/`.

Completion means each suite has one owning location, fixtures are deterministic, ribbon launchers share the automated assertions, and host-free tests can build while Revit is open.

### 3. Restore and measure coverage

Prioritize executing existing excluded tests before adding more tests of the same behavior. Restore parser, layout, metadata, icon, and runtime coverage as their dependencies and failures are resolved.

Extend the self-hosted Revit workflow to execute the hosted Python suite with deterministic project and family fixtures. Share fixture setup between individual buttons and `Run All Tests`. Define a supported Revit-year and engine matrix, including separate IronPython 2, IronPython 3, and CPython runs where supported; explicitly resolve the Revit 2021 integration gap.

Publish JUnit/TRX results with passed, failed, and skipped counts by suite, framework, Revit year, and engine. Aggregate hosted results across modules rather than overwriting a single report, fail on missing or empty expected suites, and distinguish expected capability skips from unavailable required fixtures.

Collect C# and host-free Python line and branch coverage, excluding vendored code and generated files. Establish a baseline before setting thresholds, then guard coverage of changed behavior. The current workflow does not provide a repository-wide measured coverage percentage. Source-inspection tests remain useful contract guards, but hosted lifecycle tests must also verify CPython reload and repeated execution in Revit.

Completion means CI exposes which supported combinations actually ran, unexpected coverage loss is visible, and load/signing smoke tests are reported separately from functional hosted tests.
