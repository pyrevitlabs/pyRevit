# pyRevit NUKE Build

This folder contains the NUKE-based build for pyRevit. It replaces `pipenv run pyrevit build products` so you can build all C# and Go artifacts without Python or pipenv.

---

## Prerequisites

- **.NET SDK** (8.0 or later; 10.x works). Include workloads for .NET Framework 4.8 and .NET 8.0 (e.g. `net8.0-windows`).
- **Go** (for the telemetry server). On PATH.
- **Windows** (build is designed for Windows; Revit add-in and engine paths are Windows-specific).

Check that tools are available:

```powershell
.\build.ps1 Check
```

---

## Quick start

From the **repository root** (parent of `build/`):

```powershell
# Full build (default when you run with no target)
.\build.ps1 BuildProducts

# Or simply (default target is BuildProducts)
.\build.ps1
```

This runs, in order: **BuildDeps** → **BuildLabs** → **BuildLoaders** → **BuildRuntime** → **DeployLibsToEngines** → **BuildTelem** → **BuildAutocmp**.

---

## How to run the build

### Option 1: PowerShell script (recommended)

From the repo root:

```powershell
.\build.ps1 [TargetName] [--Parameter value]
```

- **TargetName** – Any target below (e.g. `BuildProducts`, `BuildTelem`, `Clean`). If omitted, the default target **BuildProducts** runs.
- The script builds the `build` project once, then runs the requested target.

### Option 2: DotNet run

From the repo root:

```powershell
dotnet run --project build -- BuildProducts
dotnet run --project build -- BuildTelem --configuration Debug
```

---

## Build targets

You can run any target by name. Dependencies run automatically (e.g. `BuildRuntime` runs BuildDeps → BuildLabs → BuildLoaders → BuildRuntime). Targets with **no** C# dependencies (Go only) are **BuildTelem** and **BuildAutocmp**.

| Target | Description | When to use |
|--------|-------------|-------------|
| **BuildProducts** | Full build: deps → labs → loaders → runtime → deploy libs → telem. Default target. | One-shot build, CI, or “build everything.” |
| **BuildDeps** | Build dependencies: MahApps.Metro, Newtonsoft.Json, NLog, IronPython2, Python.Net. Outputs to `dev/libs/netfx`, `dev/libs/netcore`, and engine folders (`bin/netfx/engines/IPY2712PR`, `bin/netcore/engines/IPY2712PR`). | After a clean, or when you change a dependency. |
| **BuildLabs** | Build pyRevitLabs.sln and publish CLI + Doctor to `bin/`. Depends on BuildDeps. | When you change Labs, CLI, or Doctor. |
| **BuildLoaders** | Build pyRevitLoader.sln (loaders + AssemblyBuilder + ExtensionParser). Depends on BuildLabs. | When you change loader or engine tooling. |
| **BuildRuntime** | Build PyRevit.Runtime for IPY2712PR and IPY342. Depends on BuildLoaders. | When you change Runtime (e.g. ScriptConsole, engines). |
| **DeployLibsToEngines** | Copy `dev/libs/netcore` (MahApps, NLog, etc.) into `bin/netcore/engines/IPY2712PR` and `IPY342`. Depends on BuildRuntime. | Ensures engine folders have theme/lib DLLs so pack URIs resolve in Revit. |
| **BuildTelem** | Build the Go telemetry server to `bin/pyrevit-telemetryserver.exe`. **No project dependencies** – safe to run alone. | When you change `dev/pyRevitTelemetryServer` only. |
| **BuildAutocmp** | Build CLI shell autocomplete to `bin/pyrevit-autocomplete.exe`. Uses the checked-in `dev/pyRevitLabs/pyRevitCLIAutoComplete/pyrevit-autocomplete.go`. **No project dependencies.** To regenerate the .go from `UsagePatterns.txt` (when CLI usage changes), run `pipenv run pyrevit build autocmp` and commit the updated file. | When you want Tab-completion for `pyrevit` in the shell, or as part of a full build. |
| **Clean** | Delete `dev/**/bin`, `dev/**/obj`, `dev/**/.vs`, `dev/**/TestResults`. Does **not** delete repo root `bin/`. | Before a clean full build or to free disk space. |
| **Check** | Verify `dotnet` and `go` are on PATH. | After installing tools or setting up a new machine. |

### Examples

```powershell
# Full build
.\build.ps1 BuildProducts

# Only telemetry server (no C# build)
.\build.ps1 BuildTelem

# Only CLI autocomplete (no C# build)
.\build.ps1 BuildAutocmp

# Rebuild from deps up (e.g. after pulling)
.\build.ps1 BuildDeps
.\build.ps1 BuildProducts

# Rebuild only from loaders onward (deps and labs already built)
.\build.ps1 BuildLoaders

# Clean then full build
.\build.ps1 Clean
.\build.ps1 BuildProducts

# Debug build
.\build.ps1 BuildProducts --configuration Debug
```

---

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| **Configuration** | `Release` | MSBuild configuration: `Release` or `Debug`. Pass as `--configuration Debug` (or `-c Debug`). |

Example:

```powershell
.\build.ps1 BuildProducts --configuration Debug
```

---

## Output locations

| Output | Path |
|--------|------|
| CLI, Doctor, telemetry server, autocomplete | `bin/` (repo root) |
| .NET Framework engines (IronPython 2) | `bin/netfx/engines/IPY2712PR` |
| .NET Core engines (IronPython 2) | `bin/netcore/engines/IPY2712PR` |
| .NET Core engines (IronPython 3.4) | `bin/netcore/engines/IPY342` |
| Libs (MahApps, NLog, etc.) | `dev/libs/netfx`, `dev/libs/netcore` |

After **DeployLibsToEngines**, `bin/netcore/engines/IPY2712PR` and `IPY342` also contain the lib DLLs so that WPF theme resources (e.g. MahApps) resolve when running in Revit.

---

## Clean and Check

- **Clean** – Removes only under `dev/`: all `bin`, `obj`, `.vs`, and `TestResults` directories. The repo root `bin/` (where BuildProducts writes) is **not** removed. Run `.\build.ps1 Clean` before a full rebuild if you hit stale or locked files.
- **Check** – Confirms `dotnet` and `go` are available. Run `.\build.ps1 Check` to validate the environment.

---

## Troubleshooting

### “Process cannot access the file” / MSB3026

Some other process (Revit, Visual Studio, Cursor, etc.) has a lock on files under `dev/pyRevitLoader` or engine folders. Close Revit and any IDE that has the repo open, then run the build again. The loader’s deploy step uses retries; if locks persist, close more processes or reboot.

### BuildLoaders fails with "Process 'dotnet.exe' exited with code 1"

The build now captures MSBuild output on failure — scroll up in the log to see the real error. Typical causes: file locks (close Revit and IDEs) or missing refs (engine folders empty — run `.\build.ps1 BuildProducts` or at least `BuildDeps` first).

### Go / NuGet failing with proxy errors

If you see connection errors to `127.0.0.1:xxxxx` (e.g. a proxy), unset proxy env vars in your session or in your PowerShell profile. The build **unsets proxy only for Go** (BuildTelem); NuGet still uses the process environment. Example in a profile:

```powershell
$proxyVars = @('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY')
foreach ($v in $proxyVars) { Remove-Item Env:$v -ErrorAction SilentlyContinue }
```

### “Metadata file ... could not be found” (e.g. pyRevitLabs.IronPython.dll)

The loader expects DLLs in `bin/netfx/engines/IPY2712PR` or `bin/netcore/engines/...`. That usually means **BuildDeps** did not run or failed. Run a full build from the top:

```powershell
.\build.ps1 BuildProducts
```

If you ran **Clean** and then only **BuildLoaders**, the engine folders may be empty; run **BuildDeps** (or **BuildProducts**) first.

### List all targets and descriptions

Run the build with no arguments or with `--help` to see the default target. To list targets from the solution:

```powershell
dotnet run --project build -- --help
```

(Exact help output depends on your NUKE version.)

---

## Relation to pipenv build

This NUKE build is intended to match the behavior of:

```bash
pipenv run pyrevit build products
```

Rough mapping:

| Pipenv | NUKE |
|--------|------|
| `build products` | `BuildProducts` |
| (deps from _labs.build_deps) | `BuildDeps` |
| (engines / loaders) | `BuildLoaders` (after BuildLabs) |
| (runtime) | `BuildRuntime` |
| (telem) | `BuildTelem` |
| (autocmp) | `BuildAutocmp` |

NUKE adds **DeployLibsToEngines** so that `dev/libs/netcore` is copied into the netcore engine folders; pipenv may rely on assembly load path or other layout. For details and migration notes, see `docs/nuke-build-migration-plan.md`.
