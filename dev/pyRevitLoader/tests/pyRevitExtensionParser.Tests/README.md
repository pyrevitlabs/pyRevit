# pyRevitExtensionParser.Tests

Extension parsing, metadata, localization, icons, and parser configuration. Runtime and assembly-builder behaviors belong to their own suites.

Owner: the owning module maintainers; unassigned failures and quarantines belong to the change author. Quarantines require an issue and review within 14 days.

The NUnit suite targets `net48` and `net8.0-windows`. Tests are discovered from source globs; add literal Environment and Level categories to every test class. Revit API use requires the Revit category and local host setup. No test outputs deploy into a clone.

Run the full CI selection from the repository root:

```powershell
python dev/scripts/run_tests.py --language dotnet
```

For focused debugging:

```powershell
dotnet test dev/pyRevitLoader/tests/pyRevitExtensionParser.Tests/pyRevitExtensionParser.Tests.csproj -c Release -f net48 -p:SkipPyRevitDeploy=true --filter "(Environment=HostFree|TestCategory=HostFree)&Environment!=Revit&TestCategory!=Revit"
```

Temporary files and process-wide state must be reset after each test. Shared loader fixture builders stay in `pyRevitLoader/tests/TestSupport`; repository-root lookup is a small linked test helper under `dev/tests/TestSupport`. These helpers are not production dependencies.

See `docs/testing.md` for classification, coverage floors, reporting, and local Revit evidence.
