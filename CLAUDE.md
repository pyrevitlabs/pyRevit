# CLAUDE.md

This file provides guidance for AI assistants working with the pyRevit codebase.

## Project Overview

pyRevit is a Rapid Application Development (RAD) environment for Autodesk Revit. It allows users to create automation tools and add-ins using Python (IronPython 2.7.12 default, CPython 3.12.3, or IronPython 3.4.0), C#, or VB.NET. The project includes a CLI utility for deployment and a telemetry server for usage tracking.

## Repository Structure

- `bin/` - Pre-built binaries (DLLs) and Python engines (IPY2712PR, IPY342, CPY3123)
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
- **Go**: Telemetry server (`dev/pyRevitTelemetryServer/`)
- **Build Tools**: Visual Studio 2022, pipenv, MSBuild, Inno Setup

## Build Commands

All build commands use pipenv. Run from the repository root:

```bash
# Setup environment
pipenv install
pipenv run pyrevit check              # Verify build environment

# Build commands
pipenv run pyrevit build products     # Build all C# DLLs (Release mode)
pipenv run pyrevit build products Debug  # Build in Debug mode
pipenv run pyrevit build labs         # Build main project only
pipenv run pyrevit build engines      # Build Python engines
pipenv run pyrevit build installers   # Create Inno Setup installers
pipenv run pyrevit build telem        # Build telemetry server

# Cleaning
pipenv run pyrevit clean labs         # Clean build artifacts

# Version management
pipenv run pyrevit set version <ver>  # Set version number
pipenv run pyrevit set build wip      # Set as work-in-progress
pipenv run pyrevit set build release  # Set as release build
```

## Documentation

- Main website: https://pyrevitlabs.io/
- Technical docs: https://docs.pyrevitlabs.io/ (mkdocs, built from `docs/` folder)

```bash
pipenv run docs                       # Build documentation (mkdocs)
pipenv run check-docstrings           # Lint docstrings with ruff
```

## Testing

```bash
# Test telemetry server (requires Docker)
pipenv run pyrevit test telem

# Python unit tests are in pyrevitlib/pyrevit/unittests/
# C# unit tests are in dev/pyRevitLabs/pyRevitLabs.UnitTests/
```

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
5. Build: `pipenv run pyrevit build products Debug`
6. Test in Revit by attaching the clone

For debugging C# code:
1. Build in Debug mode
2. Open the appropriate `.sln` file in Visual Studio
3. Attach debugger to `revit.exe` process

## Architecture Overview

### Loading Sequence
1. Revit reads `.addin` manifest from Addins folder
2. Manifest points to `pyRevitLoader.dll` (C#)
3. Loader launches `pyrevitloader.py` in IronPython
4. Python script calls `pyrevit.loader.sessionmgr.load_session()`
5. Extensions are discovered and UI is built

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

## Supported Revit Versions

2017-2027, with separate builds per version:
- Revit 2017-2024: .NET Framework 4.7.2/4.8
- Revit 2025-2026: .NET 8.0
- Revit 202ù: .NET 10.0

## Git Workflow

- `develop` branch: Active development (always start here)
- `master` branch: Release material only
- `docs` branch: Documentation website
- Feature branches from `develop`, PRs back to `develop`
- Run `git submodule update` after switching branches
