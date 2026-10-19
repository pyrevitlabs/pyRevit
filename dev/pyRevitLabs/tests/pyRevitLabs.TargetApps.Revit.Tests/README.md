# TargetApps.Revit tests

Owner: Revit product-discovery maintainers. NUnit; `net48` and `net8.0-windows`.

`FixtureLifeCycle(LifeCycle.InstancePerTestCase)` keeps fixture objects isolated between cases.

CI runs pure product metadata matching, add-on path rules, and cache-file parsing against temporary files. Revit names do not imply a Revit API dependency. `BelowMinimumProductReportingTests` needs installed products and remains tagged `Revit` for local execution; CI never executes it. Fixtures that change environment variables run nonparallel and restore those values. Temporary-file cleanup failures fail the test.

```powershell
dotnet test dev/pyRevitLabs/tests/pyRevitLabs.TargetApps.Revit.Tests/pyRevitLabs.TargetApps.Revit.Tests.csproj -c Release -f net48 -p:SkipPyRevitDeploy=true --filter "(Environment=HostFree|TestCategory=HostFree)&Environment!=Revit&TestCategory!=Revit"
```

Use `python dev/tests/run_tests.py --language dotnet` for shared discovery, coverage gates, and reports. For installed-product reporting, run locally with `--filter TestCategory=Revit` and the required Revit installations. Attachment filtering belongs to the PyRevit suite. See `docs/testing.md` for policy.
