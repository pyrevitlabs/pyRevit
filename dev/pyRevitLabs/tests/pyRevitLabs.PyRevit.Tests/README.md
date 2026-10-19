# pyRevitLabs.PyRevit.Tests

The Labs configuration facade, script-file classification, deployed version lookup, and attachment filtering. Values written through PyRevitConfigs must persist through the shared backend; script classification needs no installed interpreter. Fake product executables make attachment-filter contracts deterministic; installed-product attachment fixtures remain tagged `Revit` and run locally. Clone deployment and install-scope/config integration belong to `pyRevitLabs.PyRevit.Integration.Tests`.

Owner: the owning module maintainers; unassigned failures and quarantines belong to the change author. Quarantines require an issue and review within 14 days.

NUnit cases target `net48` and `net8.0-windows`. Tests are discovered from source globs; add literal Environment and Level categories to every test class. Revit API use requires the Revit category and local host setup. No test outputs deploy into a clone.

Converted fixtures use `FixtureLifeCycle(LifeCycle.InstancePerTestCase)` to keep objects isolated between cases.

Run the full CI selection from the repository root:

```powershell
python dev/tests/run_tests.py --language dotnet
```

For focused debugging:

```powershell
dotnet test dev/pyRevitLabs/tests/pyRevitLabs.PyRevit.Tests/pyRevitLabs.PyRevit.Tests.csproj -c Release -f net48 -p:SkipPyRevitDeploy=true --filter "(Environment=HostFree|TestCategory=HostFree)&Environment!=Revit&TestCategory!=Revit"
```

Temporary files and process-wide state must be reset after each test. Keep fixture helpers with this suite.

See `docs/testing.md` for classification, coverage floors, reporting, and local Revit evidence.
