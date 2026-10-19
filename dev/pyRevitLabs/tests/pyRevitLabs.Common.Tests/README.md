# pyRevitLabs.Common.Tests

Common-library load timelines, identifiers, path/environment handling, build stamps, registry PATH values, and GitHub artifact naming. Deployment integration belongs to `pyRevitLabs.PyRevit.Integration.Tests`.

Owner: the owning module maintainers; unassigned failures and quarantines belong to the change author. Quarantines require an issue and review within 14 days.

NUnit and MSTest cases target `net48` and `net8.0-windows`; each keeps its existing framework. MSTest files alias assertion types explicitly to avoid NUnit global-using ambiguity. Tests are discovered from source globs; add literal Environment and Level categories to every test class. Registry cases use unique test subkeys, never the user's PATH. Environment-changing fixtures run nonparallel and restore previous values. No test outputs deploy into a clone.

Run the full CI selection from the repository root:

```powershell
python dev/tests/run_tests.py --language dotnet
```

For focused debugging:

```powershell
dotnet test dev/pyRevitLabs/tests/pyRevitLabs.Common.Tests/pyRevitLabs.Common.Tests.csproj -c Release -f net48 -p:SkipPyRevitDeploy=true --filter "(Environment=HostFree|TestCategory=HostFree)&Environment!=Revit&TestCategory!=Revit"
```

Temporary files and process-wide state must be reset after each test. Keep fixture helpers with this suite.

See `docs/testing.md` for classification, coverage floors, reporting, and local Revit evidence.
