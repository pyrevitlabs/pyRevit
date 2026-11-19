# pyRevitAssemblyBuilder.Tests

Assembly generation, session services, extension authorization, hook/search-path assembly, ribbon builders, and theme coordination. Revit fixtures are classified separately and never selected by CI.

Owner: the owning module maintainers; unassigned failures and quarantines belong to the change author. Quarantines require an issue and review within 14 days.

The NUnit suite targets `net48` and `net8.0-windows`. Tests are discovered from source globs; add literal Environment and Level categories to every test class. Revit API use requires the Revit category and local host setup. No test outputs deploy into a clone.

Run the full CI selection from the repository root:

```powershell
python dev/tests/run_tests.py --language dotnet
```

For focused debugging:

```powershell
dotnet test dev/pyRevitLoader/tests/pyRevitAssemblyBuilder.Tests/pyRevitAssemblyBuilder.Tests.csproj -c Release -f net48 -p:SkipPyRevitDeploy=true --filter "(Environment=HostFree|TestCategory=HostFree)&Environment!=Revit&TestCategory!=Revit"
```

Temporary files and process-wide state must be reset after each test. Shared loader fixture builders stay in `pyRevitLoader/tests/TestSupport`; repository-root lookup is a small linked test helper under `dev/tests/csharp`. These helpers are not production dependencies.

See `docs/testing.md` for classification, coverage floors, reporting, and local Revit evidence.

## Tests that need a local Revit

CI never runs fixtures tagged `Revit`.

| Fixture | Needs | Covers |
|---|---|---|
| `CheckBoxBuilderAdWindowsTests` | `AdWindows.dll` from an installed Revit; Revit does not run | `.checkbox` controls and stacks: ids returned to the UI manager, reuse on reload, row breaks, rows past the third and removed rows hidden |

`CheckBoxBuilderAdWindowsTests` loads `AdWindows.dll` from the newest `C:\Program Files\Autodesk\Revit 20xx` folder whose AdWindows targets the runtime the tests run on: Revit 2021 to 2024 for `net48`, Revit 2025 or later for `net8.0-windows`. When no installed Revit fits, the fixture is reported as skipped with the reason. Each test writes the `AdWindows.dll` path and the runtime to its output; add `--logger trx` to keep them with the results.

```powershell
dotnet test dev/pyRevitLoader/tests/pyRevitAssemblyBuilder.Tests/pyRevitAssemblyBuilder.Tests.csproj -f net48 --filter TestCategory=Revit
```

If the installed Revit builds AdWindows for a newer .NET than the test host, for example .NET 10, roll the host forward:

```powershell
$env:DOTNET_ROLL_FORWARD = 'LatestMajor'
dotnet test dev/pyRevitLoader/tests/pyRevitAssemblyBuilder.Tests/pyRevitAssemblyBuilder.Tests.csproj -f net8.0-windows --filter TestCategory=Revit
```

The rules these fixtures rely on also run host-free in CI: `CheckBoxControlIdsTests` for the control ids, `StackItemSplitTests` for mixed stacks and the keys the UI manager marks, and `RibbonScannerTests` for the keys the ribbon scanner reads back.
