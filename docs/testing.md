# Testing

This page maps every test surface in the repository: where it lives, how it is triggered, whether CI runs it, and what is still uncovered. It exists because the surfaces are spread across four languages and three runtimes, and it is easy to add a test that nothing executes.

To run a change locally, see the workflow in [`dev-guide.md`](dev-guide.md). For how CI/CD is wired, see [`ci-cd.md`](ci-cd.md).

## Repository testing policy

CI must discover and execute every first-party automated test that does not use the Revit API or require installed or running Revit. Every test that uses the Revit API runs locally outside CI, even if it could execute without launching Revit. This includes API use through a fixture or dependency. Parser, version-metadata, and source-contract tests remain eligible for CI only when they do not use the Revit API. A module's name or architectural role does not determine eligibility.

The inventory below describes existing wiring, including gaps against this policy. Discovery, tags and coverage gates are not implemented. In particular, the `revit-integration.yml` workflow launches Revit on pushes to `develop`, which the policy does not allow.

### Ownership and placement

C# test projects may live beside their owning module, for example `dev/<area>/<Module>.Tests/`. Existing test projects do not need to move. Keep tests in separate test assemblies so test dependencies and fixtures are not shipped with the product. `build/tests/` stays beside the build pipeline.

Centralize discovery conventions, metadata vocabulary, reporting, and coverage policy. Keep module-specific fixtures, helpers, and framework choices with their owners. Do not introduce a mandatory common test base class or convert existing NUnit, MSTest, and xUnit suites solely for uniformity.

Host-free Python tooling tests currently live in `dev/scripts/test_*.py`. Keep a documented discovery root for each Python suite and shared fixtures within the owning suite. Hosted tests stay importable through `pyrevit.unittests` until their launchers are decoupled. Do not recursively collect arbitrary Python files across the repository: importing hosted tests requires Revit, and vendored tests are outside this policy.

### Test levels and regression coverage

| Level | Contract | Execution |
|---|---|---|
| Unit | Isolated behavior without external services or user configuration | CI when API-free; local when using the Revit API |
| Integration | Real boundaries such as files, configuration backends, subprocesses, or interpreter interoperability | CI when API-free; local when using the Revit API |
| E2E | Built product completes a user workflow with objective assertions | CI for API-free workflows, such as an isolated CLI workflow; local for Revit workflows |
| Performance | Repeatable workload with explicit measurements and a comparison baseline | CI when API-free; local when using the Revit API |

Regression describes a test's purpose and can apply at any level. A bug fix must include a reproducer at the lowest effective level, with the issue reference recorded in test metadata or its contract documentation. A source-inspection assertion may guard a structural contract but does not replace execution of changed behavior.

### Discovery and classification

The following metadata contract is required policy. Current projects do not implement it consistently, and no enforcement exists yet. In this policy, `HostFree` means both free of Revit API use and independent of installed or running Revit.

- Discover C# projects under first-party `dev/` and `build/` roots by evaluated `IsTestProject=true`, regardless of directory or project name. Normalize existing projects to declare that property explicitly. Do not discover vendored projects under `dev/modules/`.
- Within discovered projects, use the test framework's native discovery. Remove class-name and method-name allowlists after excluded tests have been triaged.
- Discover Python tests using `test_*.py` within documented roots. All host-free roots participate in CI, including checker tests beside repository scripts.
- Prefer class/module defaults for test metadata and explicit method overrides. A discovery validator must resolve effective metadata consistently for each framework before applying CI filters.
- Every automated test must declare effective `Level=Unit|Integration|E2E|Performance` and `Environment=HostFree|Revit` metadata. Class/module defaults are allowed. Optional capability metadata includes network and elevation requirements. Any Revit API use or requirement for installed/running Revit mandates `Environment=Revit`, even without an application launch. Method overrides must not downgrade an actual Revit dependency to `HostFree`.
- Map this vocabulary to xUnit traits, NUnit properties/categories, and MSTest properties/categories without requiring a new framework. A Python runner adapter must preserve equivalent metadata for hosted `unittest` tests without introducing incompatible pytest imports.
- CI must fail on unclassified tests once metadata enforcement is enabled, an undiscovered first-party suite, or an expected suite/framework selecting zero tests. A Revit-only project is an explicit local selection, not an empty CI success.
- Capability tags describe provisioning requirements; they must not silently exempt host-free tests from CI. Provision isolated dependencies or redesign nondeterministic external dependencies.

Adding an ordinary test or an adjacent test project must not require editing a central list of test names. Local and CI commands must use the same discovery and selection rules. Document each suite's owner, supported frameworks/engines, fixtures, and local invocation in its nearby README; central documentation records conventions rather than duplicating those lists.

| Effective metadata | Selection |
|---|---|
| `Level=Unit`, `Environment=HostFree` | CI and local host-free runs |
| `Level=Integration`, `Environment=HostFree` | CI and local host-free runs |
| `Level=Integration`, `Environment=Revit` | Local Revit integration tests only |
| `Level=E2E`, `Environment=Revit` | Local Revit E2E tests only |

Discovery must classify tests before executing fixtures or importing Revit-dependent modules. Split mixed Python modules or C# fixtures where API-dependent initialization would otherwise execute during CI collection. CI eligibility must not be inferred solely from whether `revit.exe` is launched.

### Isolation and trustworthy outcomes

Tests must restore environment variables, module imports, process-wide caches, and configuration they change. Use temporary files and dedicated fixtures rather than a developer's active clone or mutable DevTools layout. Test builds must not deploy into a running clone.

Use bounded synchronization for concurrency tests. Sleeps must not be the sole evidence that a competing operation occurred, and waits must have timeouts. Parallelize only suites whose shared state and output paths are isolated.

An automated test must assert its result and propagate failure to the runner. Interactive dialogs, debugger launchers, printed comparisons, and demonstrations are manual checks, with documented expected outcomes. Required missing fixtures fail the selected run; expected environment exclusions are reported separately.

Temporary exclusions and quarantines require an owner, issue, reason, and review deadline. The default owner is the owning module's maintainer; if none is designated, the change author owns the quarantine until a maintainer accepts reassignment. The default review deadline is 14 calendar days after quarantine. Expiry requires resolution or an explicitly reviewed extension recorded in the issue. Report quarantines visibly. Retrying a failure for diagnosis must preserve the original outcome rather than silently passing an unstable suite.

### Reporting and coverage rules

Publish test results with passed, failed, and skipped counts for each project/module and framework/engine. Reports must have unique paths so parallel runs and hosted modules cannot overwrite one another. CI must fail when a required report is absent or cannot be written. Local Revit evidence must record the commit, Revit year, engine, fixtures, command, and result; it is not CI coverage.

Measure host-free C# and Python line and branch coverage per owning component. Include eligible unexecuted production files in the denominator. Exclude vendored dependencies, generated code, and test fixtures through reviewed configuration; every additional exclusion needs a justification. Keep source-contract checks and tests of linked source distinguishable from execution of deployed assemblies. Do not combine language percentages or claim Revit coverage from host-free runs.

Coverage gates use per-module baselines rather than a repository-wide percentage. First publish reproducible line and branch baselines for each eligible module, recording its production-source scope, tool configuration, and framework. Then enforce that subsequent changes do not decrease either baseline without a reviewed exception explaining the uncovered behavior and follow-up. Modules without a baseline must establish one on their first measured run; adding a module must not evade reporting. Raise baselines as coverage improves, and review denominator changes so deleting covered code cannot conceal newly untested behavior. Do not invent a numeric target before measurement. Critical failure, cleanup, rollback, and concurrency scenarios require explicit tests regardless of the percentage. Collection and baseline enforcement are not implemented.

## Test surfaces at a glance

| Surface | Location | How it runs | In CI |
|---|---|---|---|
| In-Revit Python unit tests | `pyrevitlib/pyrevit/unittests/` | DevTools `Debug > Unit Tests` buttons, inside Revit | No |
| Standalone Python tests | `dev/scripts/test_standalone_*.py` | `python -m unittest discover -s dev/scripts -p 'test_standalone_*.py'` | Yes — `ci.yml` |
| C# unit tests | `dev/pyRevitLabs/tests/`, `dev/pyRevitLoader/pyRevitExtensionParserTester/`, `dev/pyRevitLabs/pyRevitLabs.UnitTests/` | `build/` pipeline (`dotnet run -- ci`) | Yes — `ci.yml`; two projects run a filtered subset |
| Build pipeline tests | `build/tests/Build.Tests.csproj` | `dotnet test build/tests/Build.Tests.csproj` | Yes — `ci.yml` |
| Revit integration | [`.github/workflows/revit-integration.yml`](https://github.com/pyrevitlabs/pyRevit/blob/develop/.github/workflows/revit-integration.yml) | Self-hosted Revit runner, journal inspection | Yes — self-hosted runner |
| DevTools end-to-end buttons | `extensions/pyRevitDevTools.extension/` | Manual, inside Revit | No |

## In-Revit Python unit tests

### Dynamo execution check

Use **DevTools > Debug > Unit Tests > Dynamo Module Tests** in a disposable project. The test starts Dynamo headlessly and requires a newly generated DesignScript token from the engine's evaluated output. A successful command return is insufficient. The graph has no Python nodes, external packages, or model geometry, and the test rolls back Dynamo's startup preview materials. An existing user Dynamo workspace is never replaced.

For a reproducible local matrix, use an absolute script path:

```powershell
pyrevit run C:/path/to/pyRevit/dev/tests/revit/run_dynamo.py --revit=2026 --purge
```

The journal launches a separate Revit process, creates a disposable project, checks cold and repeat execution with different tokens, and exits. Evidence is written to `.test-results/dynamo/<year>/<run-id>/result.json`, including actual Revit/Dynamo versions and a test-source hash. Each invocation preserves earlier results. Project filenames also include the run ID. The project lives in the journal's working directory; `--purge` deletes that directory after Revit exits and releases file locks. Omit `--purge` only to retain the journal and model for diagnosis. These tests stay outside CI. The test exercises the Dynamo bundled with the Revit host it runs in; independently installed Dynamo packages and patch versions are not covered.

Invoke this entry point once per journal process; its cold/repeat checks share one project. Use a fresh `pyrevit run` process for retries. Invoking it twice in one Revit process is not supported: the second invocation can fail graph-output verification after a new document is activated.

`pyrevitlib/pyrevit/unittests/` holds the hosted suite. `runner.py` is the shared entry point; module buttons call `run_module_tests` (report only) or `assert_module_tests_successful` (raise on failure, so the button fails visibly).

The suite only runs inside a Revit session, through the DevTools **Unit Tests** pulldown. Those buttons come in two kinds, and the naming does not distinguish them:

| Buttons backed by `pyrevit.unittests` | Other module buttons (assertions or manual probes) |
|---|---|
| Run All Tests, Config Module Tests, Credentials Module Tests, Dynamo Module Tests, Output Window Tests, Query get_name Tests, Revit API Catalog Tests, Revit Module Tests, Routes Module Tests, Script Module Tests, Py3 Compat Tests, Py3 Compat Tests (CPython) | CoreUtils Module Tests (increment/decrement parsing), pyRevitLabs Module Tests, Appdata Module Tests, Forms Module Tests |

`Run All Tests` discovers every `test_` module in the package except the opt-in `test_revit_api_catalog` (it resolves hundreds of types; run it with its own **Revit API Catalog Tests** button). Modules without a dedicated button (`test_context_conditions`, `test_coreutils_escape`, `test_keynote_locks`, `test_revit_handle_contract`, `test_sys_path`, `test_versionmgr`) are only reached through `Run All Tests`.

An open project does not guarantee that every case runs. Some cases require particular model content or family fixtures injected by the individual compatibility buttons. CoreUtils prints comparisons without failing the command on a mismatch, and Forms opens interactive dialogs; neither provides an automated suite result.

`Py3 Compat Tests` runs `test_py3_compat` on whichever IronPython engine the clone is attached with; `Py3 Compat Tests (CPython)` runs it on the CPython engine. A bundle cannot select an engine *version* — engine identity is only `ironpython` or `cpython` — so the `IRONPY3`-gated cases in `test_py3_compat.py` are only reachable by attaching the clone with the IronPython 3 engine.

Nothing in CI runs this suite; it needs an installed Revit.

## Standalone Python tests

`dev/scripts/test_standalone_*.py` are plain `unittest` modules that do not need Revit. CI runs them with:

```bash
python -m unittest discover -s dev/scripts -p 'test_standalone_*.py' -v
```

Two other host-free modules live beside them: `test_check_config_api.py` and `test_check_py3_compat.py`. They have separate `Pipfile` commands (`pipenv run test-config-api`, `pipenv run test-py3-compat`), and the CI discovery pattern above excludes them. To run every module in the folder locally:

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
| `pyRevitLabs.PyRevit.Runtime.EnvVars.Tests` | all |
| `pyRevitLabs.PyRevit.Runtime.Agent.Tests` | all |
| `pyRevitCLI.Tests` | all |
| `pyRevitDoctor.Tests` | all |
| `pyRevitLabs.PyRevit.Renderer.Tests` | all |
| `pyRevitLabs.PyRevit.Shell.Tests` | all, once per IronPython engine (`IPY2712PR`, `IPY342`) |
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

`extensions/pyRevitDevTools.extension/pyRevitDev.tab/` is not a test suite. It mixes runnable assertions with demos, interactive probes, and debugger launchers — about 140 command bundles across five panels. Only the `Debug` panel buttons participate in testing, and only the module tests have an objective pass/fail; the rest are judged per button, and several block on user input by design (input stream, XAML forms, progress bars, debugger attach).

## Known issues and things to address

1. **Hosted Python execution needs a documented local procedure.** Its exclusion from CI is intentional. Record fixtures, Revit year, engine, and outcomes for local runs.
2. **Two C# projects run only a filtered subset.** `pyRevitExtensionParserTester` has far more test classes than the filter selects, including the parser, layout, and bundle-metadata tests. Excluded tests need triage before expanding CI: some expectations track mutable DevTools layouts and titles, while others require Revit assemblies. New classes are excluded unless someone updates the allowlist.
3. **`IRONPY3` coverage requires a separate attachment.** Engine identity is `ironpython` / `cpython` only, so no bundle can select IronPython 3 directly. Attach the clone with that engine before running its ribbon tests.
4. **The Python and C# component-tree parsers disagree on layout.** The Python path (`pyrevit.extensions.genericcomps`) drops components not listed in `layout`; the C# path (`pyRevitExtensionParser`) appends them. The ribbon uses C#, so the Python rule only shows up in other consumers.
5. **Some test bundles depend on a CDN at runtime.** `Test Vue` and `Test D3` load their JavaScript from `unpkg.com`, so they fail without network access.
6. **Some tests are skipped on a .NET 8+ host.** A few cases need interop assemblies not shipped for .NET 8+, sit behind an opt-in flag, or rely on fixtures that a single button injects.
7. **Host-free Python discovery is incomplete.** CI omits the two checker test modules listed above.
8. **Test builds can deploy into the active clone.** Shared build targets copy assemblies into `bin/`; a running Revit session can lock these files and prevent a test build from completing.

