# Testing

This page maps every test surface in the repository: where it lives, how it is triggered, whether CI runs it, and what is still uncovered. It exists because the surfaces are spread across four languages and three runtimes, and it is easy to add a test that nothing executes.

To run a change locally, see the workflow in [`dev-guide.md`](dev-guide.md). For how CI/CD is wired, see [`ci-cd.md`](ci-cd.md).

## Repository testing policy

CI must discover and execute every first-party automated test that does not use the Revit API or require installed or running Revit. Every test that uses the Revit API runs locally outside CI, even if it could execute without launching Revit. This includes API use through a fixture or dependency. Parser, version-metadata, and source-contract tests remain eligible for CI only when they do not use the Revit API. A module's name or architectural role does not determine eligibility.

The shared entry point is `dev/scripts/run_tests.py`. It validates classification before executing tests, discovers adjacent C# projects, selects API-free tests, publishes reports, and checks per-module coverage baselines. Product builds and test execution are separate steps; `dotnet run -- ci` builds the product and the shared runner executes tests afterward. Revit testing has no GitHub Actions workflow.

### Ownership and placement

C# test projects live beside their owning area, normally `dev/<area>/tests/<Module>.Tests/`. Keep tests in separate test assemblies so test dependencies and fixtures are not shipped with the product. `build/tests/` stays beside the build pipeline. Place tests according to the production behavior they exercise; a convenient existing test project is not a reason to put runtime or assembly-generation tests in the parser suite. Cross-component fixtures have an explicit integration suite and documented boundaries.

| Owning behavior | C# test location |
|---|---|
| Extension parsing and parser configuration | `dev/pyRevitLoader/tests/pyRevitExtensionParser.Tests/` |
| Assembly generation, session services, hooks, ribbon builders and themes | `dev/pyRevitLoader/tests/pyRevitAssemblyBuilder.Tests/` |
| Parsed bundles flowing into command generation | `dev/pyRevitLoader/tests/pyRevitLoader.Integration.Tests/` |
| Shared scripting runtime, output, logging, environment and engine compatibility | `dev/pyRevitLabs.PyRevit.Runtime/tests/pyRevitLabs.PyRevit.Runtime.Tests/` |
| Common helpers, emoji rendering and configuration facade | Separate `pyRevitLabs.Common.Tests`, `pyRevitLabs.Emojis.Tests`, and `pyRevitLabs.PyRevit.Tests` projects under `dev/pyRevitLabs/tests/` |
| CLI, configuration backends, agent and CPython adapters | Their named projects under `dev/pyRevitLabs/tests/` |
| Existing MSTest contracts across Labs libraries | `dev/pyRevitLabs/pyRevitLabs.UnitTests/`; add new component suites beside their owners |
| Build pipeline | `build/tests/` |

Small repository-path helpers live in `dev/tests/TestSupport/`; loader fixture builders live in `dev/pyRevitLoader/tests/TestSupport/`. Neither is a test project or a production dependency. Runtime fixtures own their temporary scripts without depending on parser fixtures. Per-suite READMEs document focused commands and local Revit requirements.

The reorganized suites appear in their area's solution for IDE navigation, with Debug/Release mappings but no default solution-build selection. The shared runner builds their projects explicitly. Adding a test project to a product solution must not make the product pipeline build it for every interpreter configuration.

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

Mark reproducers with pytest's `regression` marker, NUnit/MSTest's `Regression` category, or xUnit's `Purpose=Regression` trait. These supplement the required level/environment tags. Focused debugging can use `pytest -m regression` or the framework's native category/trait filter; CI still executes every API-free level.

### Discovery and classification

The following metadata contract is enforced by the shared runner. In this policy, `HostFree` means both free of Revit API use and independent of installed or running Revit.

- Discover C# projects under first-party `dev/` and `build/` roots by evaluated `IsTestProject=true`, regardless of directory or project name. Normalize existing projects to declare that property explicitly. Do not discover vendored projects under `dev/modules/`.
- Within discovered projects, use the test framework's native discovery. Remove class-name and method-name allowlists after excluded tests have been triaged.
- Discover Python tests using `test_*.py` within documented roots. All host-free roots participate in CI, including checker tests beside repository scripts.
- Prefer class/module defaults for test metadata and explicit method overrides. A discovery validator must resolve effective metadata consistently for each framework before applying CI filters.
- Every automated test must declare effective `Level=Unit|Integration|E2E|Performance` and `Environment=HostFree|Revit` metadata. Class/module defaults are allowed. Optional capability metadata includes network and elevation requirements. Any Revit API use or requirement for installed/running Revit mandates `Environment=Revit`, even without an application launch. Method overrides must not downgrade an actual Revit dependency to `HostFree`.
- Map this vocabulary to xUnit traits, NUnit properties/categories, and MSTest properties/categories without requiring a new framework. A Python runner adapter must preserve equivalent metadata for hosted `unittest` tests without introducing incompatible pytest imports.
- CI must fail on unclassified tests an undiscovered first-party suite, or an expected suite/framework selecting zero tests. A Revit-only project is an explicit local selection, not an empty CI success.
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

Coverage gates use per-module baselines rather than a repository-wide percentage. First publish reproducible line and branch baselines for each eligible module, recording its production-source scope, tool configuration, and framework. Then enforce that subsequent changes do not decrease either baseline without a reviewed exception explaining the uncovered behavior and follow-up. Modules without a baseline must establish one on their first measured run; adding a module must not evade reporting. Raise baselines as coverage improves, and review denominator changes so deleting covered code cannot conceal newly untested behavior. Do not invent a numeric target before measurement. Critical failure, cleanup, rollback, and concurrency scenarios require explicit tests regardless of the percentage. Baselines are versioned in `dev/testing/coverage-baselines.json` and checked on every selected run.

## Running API-free tests

Run from the repository root on Windows with the SDKs used by the product build:

```powershell
python dev/scripts/run_tests.py --install-dependencies
python dev/scripts/run_tests.py --list
python dev/scripts/run_tests.py
```

The install command reads the pinned pytest, pytest-cov, and coverage versions from `Pipfile.lock`. An existing Pipenv development environment can use `pipenv run test` instead. Revit execution is never enabled by these commands. `--list` records local Revit suites without importing them or executing their fixtures.

For focused development:

```powershell
python dev/scripts/run_tests.py --language python
python dev/scripts/run_tests.py --language dotnet
```

CI runs Python before the product build and C# afterward, using these same selections. Each invocation writes a unique directory under `.test-results/` with an inventory, results, coverage, and summary files. CI uploads these artifacts even on failure and publishes coverage tables in the job summary. Skipped or empty selected suites fail validation; Revit cases are explicitly excluded rather than recorded as successful skips.

### C# discovery and tags

Discovery evaluates `IsTestProject`, frameworks, and `Compile` items through MSBuild for projects under `dev/` and `build/`, excluding vendored dependencies and build outputs. All declared frameworks participate. The SDK's `AddImplicitDefineConstants` target resolves each framework's compiler symbols without compiling or executing fixtures. A Roslyn syntax reader uses those symbols to validate literal classification attributes, including conditional fixtures. Framework adapters discover actual cases and select tags; no central list of project names, test classes, or methods is maintained.

| Framework | Class defaults or method overrides |
|---|---|
| xUnit | `[Trait("Environment", "HostFree")]`, `[Trait("Level", "Integration")]` |
| NUnit | `[Category("HostFree")]`, `[Category("Integration")]` |
| MSTest | `[TestCategory("HostFree")]`, `[TestCategory("Integration")]` |

Use `Revit` instead of `HostFree` for any API use or installed-Revit dependency. Apply defaults directly to the test class using literal values. A method may add `Revit` to an otherwise API-free class; the runner excludes every case carrying that category even when the adapter also inherits `HostFree`. A Revit fixture cannot be downgraded to `HostFree`. Keep API-dependent fixture initialization in separate classes.

The common adapter filter is:

```text
(Environment=HostFree|TestCategory=HostFree)&Environment!=Revit&TestCategory!=Revit
```

The C# pre-commit formatting hook runs serially so it can group all staged files once per solution. The test runner bounds MSBuild to one node and disables node reuse to avoid accumulating worker processes across project/framework runs.

Tests that use only local doubles, without loading or calling actual Revit API assemblies, can be `HostFree`. Classification does not automatically prove a dependency is API-free; reviewers must check new fixtures and production calls. Shared libraries may contain both API-free helpers and API-dependent entry points: exercising the latter requires `Revit` classification.

### Python discovery and tags

The runner reads literal `TEST_ENVIRONMENT` and `TEST_LEVEL` module assignments through Python's AST before imports. It discovers `test_*.py` under first-party `dev/`, `pyrevitlib/pyrevit/unittests/`, and `extensions/`, plus hosted `*_tests.py` helpers under `extensions/`. Vendored trees and build outputs are excluded. Unknown or missing defaults fail discovery.

```python
TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"
```

Existing `unittest` cases run through pytest without conversion. `conftest.py` resolves optional class defaults with the same names and method overrides using `@pytest.mark.environment("Revit")` or `@pytest.mark.level("Integration")`. It records effective classification in JUnit results and excludes Revit cases before fixture setup. A HostFree module must remain safe to import; put API-dependent imports in a separate Revit module. Hosted IronPython suites retain plain assignments and `unittest`, without importing pytest.

Every explicitly selected Python module must collect at least one eligible case after classification and selection. An empty module or a HostFree module containing only Revit cases fails collection even when another module has passing tests.

## Coverage baselines

The baseline key identifies a Python source module, a C# assembly/framework, or a linked-source test assembly/framework. `dotnet-linked/` entries explicitly measure production files compiled into a test assembly and do not claim deployed-assembly coverage. Source-inspection assertions are recorded as tests but do not count the inspected source as executed code.

Coverlet emits JSON and Cobertura; aggregation unions actual line hits and branch identities across suites for each assembly/framework. Test source, generated SDK entry points, vendored code, and duplicate adapter deployment copies are excluded. Baselines cover instrumented first-party assemblies, including their unexecuted instrumentable code. Assemblies never loaded by the test host are outside that measured scope and need dedicated tests; this is not a repository-wide percentage.

Python source roots and the explicit reporting scope live in `pyproject.toml`. Eligible unexecuted files within that scope are included, including zero-coverage modules. Extend the scope when adding a covered subsystem; do not silently remove a file to improve its percentage. AST-extracted Keynote helpers are contract checks and currently have no execution coverage claim.

Refresh baselines deliberately after reviewing the reports:

```powershell
python dev/scripts/run_tests.py --update-baselines
```

The update flag writes measured values and can lower a baseline; the resulting diff requires the exception review described above. Normal runs never rewrite baselines. Missing established modules, decreases in either line or branch coverage, and newly measured modules without a baseline fail normal runs. When a module is intentionally removed or coverage scope changes, review its baseline entry in the same change. Timing and environment-dependent branches can affect coverage; investigate differences rather than accepting unexplained reductions.

## Test surfaces

| Surface | Location | Execution |
|---|---|---|
| Repository Python tooling and API-free library checks | `dev/scripts/test_*.py` | Shared runner, CI |
| C# configuration, CLI, runtime contracts, parser, and build tests | Adjacent `.csproj` test projects under `dev/` and `build/` | All frameworks and HostFree cases through the shared runner, CI |
| Revit API fixtures and installed-product integration | Revit-tagged classes/methods in the same C# projects | Local only |
| Hosted Python library suites | `pyrevitlib/pyrevit/unittests/` | DevTools Unit Tests commands inside Revit |
| Hosted agent checks | DevTools Agent Tests helpers under `extensions/` | Local Revit commands |
| Interactive examples, debugger launchers, visual checks | DevTools command bundles | Manual; not automated pass/fail evidence |

Nearby suite READMEs own fixtures and focused commands. Deterministic parser fixtures use temporary extension trees. Focused DevTools smoke assertions still inspect real ribbon metadata; maintain those expectations when the ribbon changes. The CLI help E2E test runs the built executable in an isolated subprocess. Performance is a supported classification; no general performance budget is established yet.

## Revit integration tests

Every test using the Revit API, including use through a fixture or dependency, runs outside CI. Tests requiring installed products are local even if they do not launch Revit. No CI command launches Revit, attaches a clone, or creates a certificate for Revit testing.

Attach a development clone locally:

```powershell
pyrevit clones add dev <path-to-repo>
pyrevit attach dev default --installed
```

Inside Revit, use DevTools **Debug > Unit Tests > Run All Tests** for hosted library tests, or the specific module/Agent Tests commands for focused validation. Some tests require an open project, model elements, family fixtures, or particular engine capabilities. Record those prerequisites and the actual skipped cases with the result. Commands must propagate assertion failures; printed comparisons and interactive forms remain manual checks.

Set `PYREVIT_TEST_JUNIT_PATH` before launching Revit when XML evidence is required. Give each year/engine/run a fresh destination. Distinct module suites aggregate into that file; repeating a module replaces its previous result. Requested report-write failures propagate. Unexpected successes fail the command even under IronPython 2.7. Record commit, Revit year, engine, fixture, command, and outcome. IronPython 3 cases require a separate clone attachment because a command bundle selects engine identity rather than its version.

The C# inventory identifies API-dependent fixtures for local validation. An ordinary `dotnet test` process does not become a Revit host because Revit is installed: API-dependent fixtures need the appropriate assembly resolution and host setup, and live document/UI scenarios need execution in Revit. This change does not introduce a C# in-Revit test host. Document a validated local invocation with the owning fixture before treating its result as verified.

For signing/load smoke checks, build locally, attach the clone, launch the intended Revit year, and inspect its journal for loader initialization and security/failure dialogs. A successful load is separate from functional suite execution. Never publish locally test-signed binaries. These checks are outside GitHub Actions and do not contribute to CI coverage.
