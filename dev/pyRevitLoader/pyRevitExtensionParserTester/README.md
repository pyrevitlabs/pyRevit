# pyRevitExtensionParserTester

NUnit tests for the extension parser (`dev/pyRevitLoader/pyRevitExtensionParser`) and the assembly builder (`dev/pyRevitLoader/pyRevitAssemblyBuilder`).

- **Owner:** pyRevit loader maintainers.
- **Framework:** NUnit on `net48` and `net8.0-windows`.
- **Tags:** NUnit categories on the fixture class carry the level (`Unit`, `Integration`) and the environment (`HostFree`, `Revit`). Older fixtures are not tagged yet.
- **CI:** `build/Modules/TestConfigurationsModule.cs` runs `net8.0-windows` with a filter that selects `TestCategory=HostFree` plus a list of older fixtures by name. A new host-free fixture only needs the `HostFree` category.

Run the host-free tests from the repository root:

```powershell
dotnet test dev/pyRevitLoader/pyRevitExtensionParserTester/pyRevitExtensionParserTest.csproj -f net8.0-windows --filter TestCategory=HostFree
```

## Tests that need a local Revit

CI never runs fixtures tagged `Revit`.

| Fixture | Needs | Covers |
|---|---|---|
| `CheckBoxBuilderAdWindowsTests` | `AdWindows.dll` from an installed Revit; Revit does not run | `.checkbox` controls and stacks: ids returned to the UI manager, reuse on reload, row breaks, rows past the third and removed rows hidden |

`CheckBoxBuilderAdWindowsTests` loads `AdWindows.dll` from the newest `C:\Program Files\Autodesk\Revit 20xx` folder whose AdWindows targets the runtime the tests run on: Revit 2021 to 2024 for `net48`, Revit 2025 or later for `net8.0-windows`. When no installed Revit fits, the fixture is reported as skipped with the reason. Each test writes the `AdWindows.dll` path and the runtime to its output; add `--logger trx` to keep them with the results.

```powershell
dotnet test dev/pyRevitLoader/pyRevitExtensionParserTester/pyRevitExtensionParserTest.csproj -f net48 --filter TestCategory=Revit
```

If the installed Revit builds AdWindows for a newer .NET than the test host, for example .NET 10, roll the host forward:

```powershell
$env:DOTNET_ROLL_FORWARD = 'LatestMajor'
dotnet test dev/pyRevitLoader/pyRevitExtensionParserTester/pyRevitExtensionParserTest.csproj -f net8.0-windows --filter TestCategory=Revit
```

The rules these fixtures rely on also run host-free in CI: `CheckBoxControlIdsTests` for the control ids, `StackItemSplitTests` for mixed stacks and the keys the UI manager marks, and `RibbonScannerTests` for the keys the ribbon scanner reads back.
