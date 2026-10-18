# pyRevitLabs.PyRevit.Runtime.Agent.Tests

Owner: the owning module maintainers; the change author owns unassigned fixes and quarantines until reassigned. Quarantines require an issue and review within 14 days.

Frameworks: `net10.0-windows`.

Fixtures and helpers are owned by this suite. Temporary configuration and output must be cleaned up after each test. Agent production files are linked into this assembly against local doubles; no Revit API assembly is used. Coverage is reported separately as dotnet-linked.

From the repository root, run all API-free C# suites with shared discovery and coverage gates:

```powershell
python dev/testing/run_tests.py --language dotnet
```

For a focused debugging run, using one of the frameworks above:

```powershell
dotnet test dev/pyRevitLabs/tests/pyRevitLabs.PyRevit.Runtime.Agent.Tests/pyRevitLabs.PyRevit.Runtime.Agent.Tests.csproj -c Release -f net10.0-windows -p:SkipPyRevitDeploy=true --filter "(Environment=HostFree|TestCategory=HostFree)&Environment!=Revit&TestCategory!=Revit"
```

Declare literal Environment and Level tags on each test class using this project's existing framework. Method overrides can mark individual local Revit cases; no override can downgrade a Revit fixture to HostFree. Keep fixtures safe during discovery. New tests participate automatically; do not add a class-name allowlist or deploy test outputs into a clone. The shared runner writes TRX, coverage, and inventory artifacts below `.test-results/`.

See `docs/testing.md` at the repository root for the metadata vocabulary, per-module baselines, and local Revit procedure. An ordinary test host cannot execute live Revit document/UI tests without explicit host setup.
