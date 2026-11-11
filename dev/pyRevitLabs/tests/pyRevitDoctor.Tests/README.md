# pyRevitDoctor.Tests

Host-free xUnit tests for `pyrevit-doctor` (`dev/pyRevitLabs/pyRevitDoctor`).

- **Owner:** pyRevit CLI / doctor maintainers.
- **Framework:** xUnit on `net10.0-windows`. Every test is tagged `Level=Unit`, `Environment=HostFree`.
- **Sources under test:** `ProductCatalog.cs`, `UninstallEntryMatcher.cs`, `PurgeTargets.cs`, `PurgeSession.cs` and `PurgeFiles.cs` from `pyRevitDoctor/`, compiled in through linked `Compile` items so the test assembly does not reference the doctor executable. The file-system tests run against a temporary fake profile; the registry and `PATH` steps are not covered.
- **Fixtures:** `release/pyrevit-products.json`, copied to `Fixtures/pyrevit-products.json` in the output directory.
- **CI:** run by `build/Modules/TestConfigurationsModule.cs` as part of `dotnet run -- ci`.

Run locally from the repository root:

```powershell
dotnet test dev/pyRevitLabs/tests/pyRevitDoctor.Tests/pyRevitDoctor.Tests.csproj
```
