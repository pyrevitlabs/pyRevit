# Agent Instructions

Unified agent rules for the pyRevit repository. Every AI assistant touching this repo (GitHub Copilot, Claude Code, opencode, Cursor, Aider, etc.) must follow this file.

The vendor-specific files (`.github/copilot-instructions.md`, `CLAUDE.md`) are thin pointers to this file; they exist only so each tool discovers the rules at its expected filename.

---

## Project overview

pyRevit is a Rapid Application Development (RAD) environment for Autodesk Revit. It lets users write automation tools and add-ins in Python (IronPython 2.7.12 default, CPython 3.12.3, or IronPython 3.4.0), C#, or VB.NET. The project also ships a CLI utility for deployment and a telemetry server for usage tracking.

## Repository organization

- **bin** — Generated product binaries (DLLs, engines, CLI). Built locally via `dotnet run -- ci` or downloaded anonymously from public CI Release assets by `pyrevit clone`. Not tracked in git. Static sources: `release/bin-assets/`, `release/cengines/`, `release/pyrevit-hosts.json`. The CPython DLLs and core packages also live here.
- **dev** — C# source code, build scripts, and solution files.
- **docs** — Documentation source for the website (mkdocs).
- **extensions** — pyRevit extensions (tools visible in the Revit ribbon). `pyRevitCore.extension` builds the pyRevit ribbon tab; the rest are enabled via the Extensions button. `pyRevitDevTools` is handy for running tests and checking that pyRevit (and your changes) is working.
- **extras** — Extra files that come in handy (icons, dark-mode generator).
- **licenses** — Licenses of the included third-party projects.
- **pyrevitlib** — pyRevit and related Python libraries; imported by user scripts to ease Revit API development.
- **release** — Static assets needed to build the final product (pyRevit and pyRevit CLI installers) plus build artifacts and installer configurations.
- **site-packages** — Third-party Python packages made available by pyRevit to the user. Given that the main Python engine is IronPython 2.7.12, packages here must be compatible with it.
- **static** — Assets for the website and YouTube channels. You can ignore it.

## Architecture overview

This section explains how pyRevit fits together so new contributors (human or AI) understand the moving parts.

### Components

1. **pyRevit Add-In (pyRevitLoader)** — A small C# plugin that starts pyRevit inside Revit when Revit itself starts.
2. **pyRevit Python Libraries (pyrevitlib)** — Python packages that simplify working with the Revit API; abstractions for creating ribbon buttons, running scripts, and interacting with Revit data.
3. **Extensions** — The tools and features users see inside Revit. Mostly Python, but also C#/VB.NET scripts, Dynamo projects, etc. Bundled extensions appear in the "pyRevit" tab; users can add more by enabling listed extensions via the Extensions button or by adding custom extension paths to the configuration.
4. **pyRevit Command-Line Interface (CLI)** — Tool for managing configurations, running scripts in bulk, and troubleshooting. Useful for corporate setups and advanced users.
5. **Telemetry Server** — Small server that tracks usage data of pyRevit tools and stores it for business-intelligence purposes.

### Key components

- **pyRevitLoader** (`dev/pyRevitLoader/`) — Revit add-in entry point.
- **PyRevit.Runtime** (`dev/pyRevitLabs.PyRevit.Runtime/`) — Command execution.
- **pyrevitlib** (`pyrevitlib/pyrevit/`) — Python API for scripts.
- **CLI** (`dev/pyRevitLabs/pyRevitCLI/`) — Command-line management.

### Loading sequence

1. Revit reads the `.addin` manifest from the Addins folder.
2. The manifest points to `pyRevitLoader.dll` (C#).
3. `PyRevitLoaderApplication.OnStartup` calls the C# session manager directly (no IronPython bootstrap).
4. `SessionManagerService.LoadSession` runs `session_preload.py`, builds extension assemblies and UI in C#, then runs `session_postload.py`.
5. The preload/postload scripts drive the residual Python session services (telemetry, routes, output window, hooks framework) through the runtime engine.

Reload re-enters the same C# orchestrator via `PyRevitLoaderApplication.LoadSession`. The legacy pure-Python loader has been removed; the C# loader requires Revit 2021+.

### .addin manifest

The installer places a `.addin` manifest file in the Revit Addins folder, instructing Revit to load pyRevit on startup. Depending on the installation type:

- `C:\ProgramData\Autodesk\Revit\Addins` (all users)
- `%APPDATA%\Autodesk\Revit\Addins` (current user only)

### pyRevitLoader.dll

The loader dll is the C# entry point for pyRevit inside Revit. Multiple versions support different Revit versions (one for Revit 2025+, another for Revit 2021–2024) and different IronPython versions (2.7.12 default, 3.4.0 available but not fully tested). Since only one IronPython engine can be active at a time, pyRevit updates the `.addin` manifest to point to the correct loader when the user switches engines. If installation issues arise, running `pyrevit attach` usually resolves them by regenerating the manifest correctly.

### Script engines

Located in `dev/pyRevitLabs.PyRevit.Runtime/`:

- `IronPythonEngine.cs` — Default Python engine.
- `CPythonEngine.cs` — Modern Python (3.12).
- `CLREngine.cs` — C#/VB.NET execution.
- `DynamoBIMEngine.cs` — Dynamo graphs.
- `GrasshopperEngine.cs` — Grasshopper definitions.

### Extension discovery

pyRevit scans known paths and user-defined folders to find installed extensions. For each extension it generates the UI elements (ribbon tabs, panels, buttons).

### How pyRevit commands run

Each ribbon button is backed by a command that:

- Detects any modifier keys held at click time and adjusts behavior accordingly.
- Runs the appropriate script (Python, C#, Dynamo, etc.) based on the button's configuration.

The appropriate script engine is selected automatically based on the script type.

## Languages and technologies

- **Python**: IronPython 2.7.12 (default), CPython 3.12.3, IronPython 3.4.2.
- **C#**: .NET Framework 4.8 (Revit 2021–2024), .NET 8.0 (Revit 2025–2026), .NET 10.0 (Revit 2027+).
- **Go**: pyRevit autocomplete application (`dev/pyRevitLabs/pyRevitCLIAutoComplete`).
- **Build tools**: .NET 10, ModularPipelines, Visual Studio 2022, MSBuild, Inno Setup.

## Build commands

The build is driven by the C# ModularPipelines project under `build/`. Run from `build/`:

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

Other pipeline modes: `pack`, `sign`, `publish`, `winget`, `notify`. See `build/README.md` for the full list, `Build__Channel` semantics, and CI gating.

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

## Development workflow

1. Fork and clone the repository.
2. Checkout `develop` (active development).
3. Initialize submodules: `git submodule update --init --recursive`.
4. Install dependencies: `pipenv install`.
5. Build: `cd build && dotnet run -c Debug -- ci && cd ..`.
6. Test in Revit by attaching the clone.

For debugging C# code:

1. Build in Debug mode.
2. Open the appropriate `.sln` file in Visual Studio.
3. Attach the debugger to `revit.exe`.

## Extension bundle structure

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

Supported bundle types: `pushbutton`, `smartbutton`, `pulldown`, `splitbutton`, `panelbutton`.

## Key configuration files

- `Pipfile` — Python dependencies (requires Python 3.14).
- `pyRevitfile` — Engine definitions and deployment profiles.
- `pyproject.toml` — Ruff linting config (Google docstring convention).
- `mkdocs.yml` — Documentation generation.
- `.gitmodules` — Git submodules for dependencies.

## Code style

- Python: Google docstring convention, formatted with black, linted with ruff.
- C#: Standard .NET conventions.

## Commenting guidelines

Code, names, types, and docstrings carry meaning. Inline comments are the exception, not the rule. When in doubt, delete the comment and see if the code still reads correctly.

The default for inline comments is: do not add them. The contract below is exhaustive — every inline comment must fall into exactly one of the listed special cases; if it does not, delete it.

### Inline comments

Allowed only in the following cases. Anything else is removed.

- Non-obvious **why** that cannot live in a docstring (Revit API quirk, threading constraint, perf tradeoff, historical reason).
- Warnings about side effects, ordering, or invariants a future editor must preserve.
- Pragmas required by tooling or the language: `# noqa`, `# type: ignore`, `# pylint: disable=…`, `# coding: utf-8`, shebang lines, encoding markers, license headers.
- `TODO` / `FIXME` / `XXX` with an owner and ticket reference.

Do not write inline comments that:

- Restate what the next line of code literally does (`# increment counter`, `# call the loader`, `# return the list`).
- Name specific internal functions, classes, or modules that the code depends on.
- Describe the sequence of steps the implementation follows.
- Reference implementation choices that could change (e.g. which engine, which data structure, which library).
- Act as section banners or decorative headers (`# ----- helpers -----`).

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

## Documentation requirements

**Principle:** document information that is expensive to rediscover from code. Do not document information that is obvious from the name, types, or one line of code. Sparse, high-value docstrings beat padded ones — duplicated information goes stale and misleads the next refactor.

Code tells the agent **how**. Docstrings tell it **what, why, and what must remain true**.

### Scope hierarchy

Information lives in the narrowest scope that carries it:

| Scope | Carries |
|---|---|
| `AGENTS.md` | Architecture, conventions, commands every agent needs |
| Module docstring | Why this subsystem exists; its boundaries |
| Class docstring | Responsibilities, lifecycle, invariants |
| Function / method docstring | Contract, side effects, exceptions, non-obvious constraints |
| Inline comment | Why this particular implementation is unusual |

### What belongs in docstrings

When applicable, capture:

- **Purpose** — what abstraction or business operation this represents.
- **Contract** — inputs, outputs, important guarantees.
- **Side effects** — DB writes, network calls, filesystem changes, emitted events.
- **Exceptions** — especially domain-specific ones and what they mean here.
- **Invariants** — conditions that must remain true after refactoring.
- **Non-obvious constraints** — ordering, idempotency, thread safety, transaction boundaries, compatibility requirements.
- **Why something unusual exists** — historical or architectural reason.
- **Architectural role** — how this symbol relates to the rest of the system (e.g. "Payment providers must not modify subscriptions directly").

Mark dangerous-to-break constraints explicitly with Google-style sections: `Important:`, `Note:`, `Warning:`, `Invariant:`. Treat them as red lines for the next editor.

### What does not belong

- Restating the signature, name, or types.
- Narrating the implementation (`"""Loop through items and add item.price to total."""`).
- Padding trivial functions — if behaviour is obvious from the code, omit the docstring entirely.
- Implementation details an agent can inspect (`"""Uses Redis sorted set keyed by timestamp."""` when the call is right there).

### Language rules

- **Python**: Google-style docstrings on **public** symbols (non-underscored). Match `pyproject.toml` (`select = ["D"]`, `convention = "google"`), enforced by `pipenv run check-docstrings`.
- **C#**: XML `///` doc comments on **public** classes and methods. `<summary>` carries purpose; `<param>` / `<returns>` / `<exception>` cover non-obvious details only.
- Private (underscored Python, `private` / `internal` C#) members are exempt — same carve-out as `D107` and `D105`.

When behaviour changes, update the docstring / XML doc in the same change.

## Self-check before finalising

Before finishing a task, audit the diff:

1. Scan for inline comments. For each one, name the special case it falls under. If you cannot, delete it.
2. Scan for new or changed public symbols. Confirm each one has a docstring (Python) or XML `///` doc (C#) only if it carries information that cannot be read off the code — purpose, contract, side effects, invariants. Strip anything that just restates the signature or narrates the implementation.

## Supported Revit versions

2021–2027, with separate builds per version. The C# loader requires Revit 2021+; the legacy pure-Python loader (which supported older versions) has been removed.

- Revit 2021–2024: .NET Framework 4.8.
- Revit 2025–2026: .NET 8.0 (Windows).
- Revit 2027+: .NET 10.0 (Windows).

## Git workflow

- `develop` branch: Active development (always start here).
- `master` branch: Release material only.
- `docs` branch: Documentation website.
- Feature branches from `develop`, PRs back to `develop`.
- Run `git submodule update` after switching branches.
