# CLAUDE.md

This file provides guidance for AI assistants working with the pyRevit codebase.

## Project Overview

pyRevit is a Rapid Application Development (RAD) environment for Autodesk Revit. It allows users to create automation tools and add-ins using Python (IronPython 2.7.12 default, CPython 3.12.3, or IronPython 3.4.0), C#, or VB.NET. The project includes a CLI utility for deployment and a telemetry server for usage tracking.

## Repository Structure

- `bin/` - Generated product binaries (DLLs, engines, CLI). Built locally via `dotnet run -- ci` or downloaded anonymously from public CI Release assets by `pyrevit clone`. Not tracked in git. Static sources: `release/bin-assets/`, `release/cengines/`, `release/pyrevit-hosts.json`.
- `dev/` - C# source code, build scripts, and solution files
- `docs/` - Documentation source for the website (mkdocs)
- `extensions/` - pyRevit extensions (tools visible in Revit ribbon)
- `extras/` - Additional resources (icons, dark mode generator)
- `licenses/` - Third-party library licenses
- `pyrevitlib/` - Python libraries for Revit API development
- `release/` - Build artifacts and installer configurations
- `site-packages/` - Third-party Python packages (must be IronPython 2.7.12 compatible)

## Languages and Technologies

- **Python**: IronPython 2.7.12 (default), CPython 3.12.3, IronPython 3.4.0
- **C#**: .NET Framework 4.8 (Revit 2017-2024), .NET 8.0 (Revit 2025+)
- **Go**: pyRevit autocomplete application (`dev/pyRevitLabs/pyRevitCLIAutoComplete`)
- **Build Tools**: .NET 10, ModularPipelines, Visual Studio 2022, MSBuild, Inno Setup

## Build Commands

The build is driven by the C# ModularPipelines project under [`build/`](build/). Run from `build/`:

```powershell
# Default unsigned local build (Channel=none)
dotnet run -c Release -- ci

# Debug build (attach the Visual Studio debugger to revit.exe)
dotnet run -c Debug -- ci

# WIP-style stamping + product build (mirrors develop push on the main repo)
$env:Build__Channel = 'wip'
dotnet run -c Release -- ci

# Release-style stamping + product build (mirrors master / tag CI on the main repo)
$env:Build__Channel = 'release'
$env:DOTNET_ENVIRONMENT = 'Production'
dotnet run -c Release -- ci
```

Other pipeline modes: `pack`, `sign`, `publish`, `winget`, `notify`. See [`build/README.md`](build/README.md) for the full list, `Build__Channel` semantics, and CI gating.

## Documentation

- Main website: https://pyrevitlabs.io/
- Technical docs: https://docs.pyrevitlabs.io/ (mkdocs, built from `docs/` folder)

```bash
pipenv run docs                       # Build documentation (mkdocs)
pipenv run check-docstrings           # Lint docstrings with ruff
```

## Testing

To test in Revit:
```bash
pyrevit clones add dev <path-to-repo>
pyrevit attach dev default --installed
```

## Development Workflow

1. Fork and clone the repository
2. Checkout `develop` branch (active development)
3. Initialize submodules: `git submodule update --init --recursive`
4. Install dependencies: `pipenv install`
5. Build: `cd build && dotnet run -c Debug -- ci && cd ..`
6. Test in Revit by attaching the clone

For debugging C# code:
1. Build in Debug mode
2. Open the appropriate `.sln` file in Visual Studio
3. Attach debugger to `revit.exe` process

## Architecture Overview

### Loading Sequence
1. Revit reads `.addin` manifest from Addins folder
2. Manifest points to `pyRevitLoader.dll` (C#)
3. `PyRevitLoaderApplication.OnStartup` calls the C# session manager directly (no IronPython bootstrap)
4. `SessionManagerService.LoadSession` runs `session_preload.py`, builds extension assemblies and UI in C#, then runs `session_postload.py`
5. The preload/postload scripts drive the residual Python session services (telemetry, routes, output window, hooks framework) through the runtime engine

Reload re-enters the same C# orchestrator via `PyRevitLoaderApplication.LoadSession`. The legacy pure-Python loader has been removed; the C# loader requires Revit 2021+.

### Key Components
- **pyRevitLoader** (`dev/pyRevitLoader/`): Revit add-in entry point
- **PyRevit.Runtime** (`dev/pyRevitLabs/pyRevitLabs.PyRevit.Runtime/`): Command execution
- **pyrevitlib** (`pyrevitlib/pyrevit/`): Python API for scripts
- **CLI** (`dev/pyRevitLabs/pyRevitLabs.PyRevit/`): Command-line management

### Script Engines
Located in `dev/pyRevitLabs/pyRevitLabs.PyRevit.Runtime/`:
- `IronPythonEngine.cs` - Default Python engine
- `CPythonEngine.cs` - Modern Python (3.12)
- `CLREngine.cs` - C#/VB.NET execution
- `DynamoBIMEngine.cs` - Dynamo graphs
- `GrasshopperEngine.cs` - Grasshopper definitions

## Extension Bundle Structure

Extensions follow this hierarchy:
```
MyExtension.extension/
  MyTab.tab/
    MyPanel.panel/
      MyButton.pushbutton/
        bundle.yaml      # Button configuration
        script.py        # Python script
        icon.png         # Button icon
```

Supported bundle types: pushbutton, smartbutton, pulldown, splitbutton, panelbutton

## Key Configuration Files

- `Pipfile` - Python dependencies (requires Python 3.10)
- `pyRevitfile` - Engine definitions and deployment profiles
- `pyproject.toml` - Ruff linting config (Google docstring convention)
- `mkdocs.yml` - Documentation generation
- `.gitmodules` - Git submodules for dependencies

## Code Style

- Python: Google docstring convention, formatted with black, linted with ruff
- C#: Standard .NET conventions

 
   
## Commenting and documentation rules

See [`.github/copilot-instructions.md`](.github/copilot-instructions.md) for the inline-comment allow-list and the docstring / XML-doc requirements. These apply to all changes in this codebase, including both Python and C# files.

## Supported Revit Versions

2017-2027, with separate builds per version:
- Revit 2017-2024: .NET Framework 4.7.2/4.8
- Revit 2025-2026: .NET 8.0
- Revit 2027+: .NET 10.0

## Git Workflow

- `develop` branch: Active development (always start here)
- `master` branch: Release material only
- `docs` branch: Documentation website
- Feature branches from `develop`, PRs back to `develop`
- Run `git submodule update` after switching branches
