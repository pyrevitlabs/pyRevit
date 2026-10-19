# PyRevit integration tests

Owner: PyRevit deployment and configuration maintainers. MSTest; `net48` and `net8.0-windows`.

These API-free integration cases exercise clone deployment, config seeding, install-scope resolution, and parser/config interoperability. Archives and Git repositories are local fixtures; no downloads or installed Revit are needed. Configuration roots and elevation detection are isolated. Fixtures that change process-wide state use `DoNotParallelize` and restore environment variables, cached scope, and configuration state during cleanup. Temporary-file cleanup failures fail the test.

```powershell
dotnet test dev/pyRevitLabs/tests/pyRevitLabs.PyRevit.Integration.Tests/pyRevitLabs.PyRevit.Integration.Tests.csproj -c Release -f net48 -p:SkipPyRevitDeploy=true --filter "(Environment=HostFree|TestCategory=HostFree)&Environment!=Revit&TestCategory!=Revit"
```

Use `python dev/tests/run_tests.py --language dotnet` for shared discovery, coverage gates, and reports. See `docs/testing.md` for classification and regression rules.
