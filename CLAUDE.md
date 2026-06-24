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


 
## Commenting guidelines
 
When writing or suggesting code comments, document **what** the code does and **why**, never **how**.
 
Implementation details are already visible in the code itself. Restating them in a comment adds noise and creates drift: when the implementation changes, comments that describe it become misleading if not updated at the same time.
 
**Avoid comments that:**
- Restate what the next line of code literally does (`# increment counter`, `# call the loader`, `# return the list`).
- Name specific internal functions, classes, or modules that the code depends on.
- Describe the sequence of steps the implementation follows.
- Reference implementation choices that could change (e.g. which engine, which data structure, which library).
**Prefer comments that:**
- Explain the purpose or intent of a block (`# ensure the session is clean before loading extensions`).
- Capture non-obvious **why** reasoning that cannot be inferred from the code (`# Revit does not allow re-entrant API calls during this event`).
- Warn about known constraints or side effects that a future editor needs to be aware of.
- Describe what a function or class is responsible for, not how it achieves it.
**Example — what to avoid:**
```python
# Call get_ext_root_dirs to retrieve the list of extension paths from user config,
# then pass each path to extensionmgr to scan for UI extension manifests.
extensions = get_all_extensions()
```
 
**Example — what to write instead:**
```python
# Collect all installed extensions visible to the current user before building the UI.
extensions = get_all_extensions()
```
 
The same rule applies to docstrings, inline comments, and any documentation generated alongside code.

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
