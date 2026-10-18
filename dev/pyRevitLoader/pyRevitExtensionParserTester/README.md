# pyRevitExtensionParserTest

Owner: the owning module maintainers; the change author owns unassigned fixes and quarantines until reassigned. Quarantines require an issue and review within 14 days.

Frameworks: `net48`, `net8.0-windows`.

Fixtures and helpers are owned by this suite. Temporary configuration and output must be cleaned up after each test. Parser fixtures create temporary extension trees and an isolated configuration with script metadata enabled. Focused DevTools smoke tests read the tracked extension; update their expectations when its metadata changes. Revit API fixtures remain tagged Revit and require local host setup.

From the repository root, run all API-free C# suites with shared discovery and coverage gates:

```powershell
python dev/scripts/run_tests.py --language dotnet
```

For a focused debugging run, using one of the frameworks above:

```powershell
dotnet test dev/pyRevitLoader/pyRevitExtensionParserTester/pyRevitExtensionParserTest.csproj -c Release -f net48 -p:SkipPyRevitDeploy=true --filter "(Environment=HostFree|TestCategory=HostFree)&Environment!=Revit&TestCategory!=Revit"
```

Declare literal Environment and Level tags on each test class using this project's existing framework. Method overrides can mark individual local Revit cases; no override can downgrade a Revit fixture to HostFree. Keep fixtures safe during discovery. New tests participate automatically; do not add a class-name allowlist or deploy test outputs into a clone. The shared runner writes TRX, coverage, and inventory artifacts below `.test-results/`.

See `docs/testing.md` at the repository root for the metadata vocabulary, per-module baselines, and local Revit procedure. An ordinary test host cannot execute live Revit document/UI tests without explicit host setup.
