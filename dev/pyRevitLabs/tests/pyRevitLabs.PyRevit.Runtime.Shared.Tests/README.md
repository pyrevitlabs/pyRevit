# Runtime.Shared tests

Owner: runtime interop maintainers. MSTest; `net48` and `net8.0-windows`.

Dynamo graph preparation, command-overload selection, model lifecycle and add-in lookup use temporary graphs/manifests and local Dynamo type doubles. No Revit API or Dynamo installation is required. The `Dynamo.Applications` names are intentional: production reflection resolves those exact type names. These doubles belong only to this suite. Fixtures run nonparallel, reset fake static state, and delete their temporary files after each case.

```powershell
dotnet test dev/pyRevitLabs/tests/pyRevitLabs.PyRevit.Runtime.Shared.Tests/pyRevitLabs.PyRevit.Runtime.Shared.Tests.csproj -c Release -f net48 -p:SkipPyRevitDeploy=true --filter "(Environment=HostFree|TestCategory=HostFree)&Environment!=Revit&TestCategory!=Revit"
```

Use `python dev/tests/run_tests.py --language dotnet` for shared discovery, coverage gates, and reports. See `docs/testing.md` for classification and regression rules.
