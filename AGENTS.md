# Agent Instructions

Agent rules for the pyRevit repository.

---

## Project overview

pyRevit is a Rapid Application Development (RAD) environment for Autodesk Revit. It lets users write automation tools in Python (IronPython 2.7.12 default, CPython 3.12.3, or IronPython 3.4.0), C#, or VB.NET. The project also ships a CLI utility for deployment and a telemetry server for usage tracking.

## Repository organization

See [`docs/repo-organization.md`](docs/repo-organization.md).

## Extension bundle structure

Extensions follow this hierarchy:

```text
MyExtension.extension/
  MyTab.tab/
    MyPanel.panel/
      MyButton.pushbutton/
        bundle.yaml      # Button configuration
        script.py        # Python script
        icon.png         # Button icon
```

Supported bundle types: `pushbutton`, `smartbutton`, `pulldown`, `splitbutton`, `panelbutton`.

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
- **C#**: .NET Framework 4.8, .NET 8.0, or .NET 10.0, depending on Revit version — see [Supported Revit versions](#supported-revit-versions).
- **Go**: pyRevit autocomplete application (`dev/pyRevitLabs/pyRevitCLIAutoComplete`).
- **Build tools**: .NET 10, ModularPipelines, Visual Studio 2022, MSBuild, Inno Setup.

## Build commands

The build is driven by the C# ModularPipelines project under `build/`. To verify a change builds, run from `build/`:

```powershell
# Default unsigned local build (Channel=none)
dotnet run -c Release -- ci

# Debug build (attach the Visual Studio debugger to revit.exe)
dotnet run -c Debug -- ci
```

The `wip`/`release` channel stamping (`Build__Channel` env var) and the other pipeline modes (`pack`, `sign`, `publish`, `winget`, `notify`) are CI-owned — don't invoke them locally. See `build/README.md` for details.

## Documentation

- Main website: https://pyrevitlabs.io/
- Technical docs source: [`docs/`](docs) (mkdocs). Reference API is generated from source docstrings.

Build and validate before finishing doc changes:

```bash
mkdocs build --strict                 # Build docs, fail on warnings
pipenv run check-docstrings           # Lint docstrings with ruff
```

## Testing

To test in Revit:

```bash
pyrevit clones add dev <path-to-repo>
pyrevit attach dev default --installed
```

## Development workflow

1. Branch from `develop` — see [Git workflow](#git-workflow).
2. Initialize submodules: `git submodule update --init --recursive`.
3. Install dependencies: `pipenv install`.
4. Build: `cd build && dotnet run -c Debug -- ci && cd ..`.
5. Test in Revit by attaching the clone — see [Testing](#testing).

## Key configuration files

- `Pipfile` — Python dependencies (requires Python 3.14).
- `pyRevitfile` — Engine definitions and deployment profiles.

## Code style

- Python: Google docstring convention. Run `pipenv run black <path>` to format and `pipenv run ruff check --fix <path>` to lint — these are not enforced by pre-commit hooks, so you must run them before finishing.
- C#: Standard .NET conventions.

## Commenting guidelines

Don't write inline comments. Ever. Code must be self-explanatory — if it isn't, improve names or extract a well-named function instead of explaining it in a comment. Keep pre-existing comments made by a human unless they're clearly outdated.

Exceptions:

- Pragmas required by tooling or the language: `# noqa`, `# type: ignore`, `# pylint: disable=…`, `# coding: utf-8`, shebang lines, encoding markers, license headers.
- `TODO` / `FIXME` / `XXX` with an owner and ticket reference.

## Documentation requirements

**Principle:** document information that is expensive to rediscover from code. Do not document information that is obvious from the name, types, or one line of code. Sparse, high-value docstrings beat padded ones — duplicated information goes stale and misleads the next refactor.

Code tells the agent **how**. Docstrings tell it **what, why, and what must remain true**.

### Scope hierarchy

Information lives in the narrowest scope that carries it:

| Scope | Carries |
|---|---|
| `AGENTS.md` | Conventions, commands every agent needs |
| Module docstring | Why this subsystem exists; its boundaries |
| Class docstring | Responsibilities, lifecycle, invariants |
| Function / method docstring | Contract, side effects, exceptions, non-obvious constraints |
| Inline comment | Pragmas and `TODO`/`FIXME`/`XXX` only — see [Commenting guidelines](#commenting-guidelines) |

### What belongs in docstrings

When applicable, capture:

- **Purpose** — what abstraction or business operation this represents.
- **Contract** — inputs, outputs, important guarantees.
- **Side effects** — DB writes, network calls, filesystem changes, emitted events.
- **Exceptions** — especially domain-specific ones and what they mean here.
- **Invariants** — conditions that must remain true after refactoring.
- **Non-obvious constraints** — ordering, idempotency, thread safety, transaction boundaries, compatibility requirements.
- **Architectural role** — how this symbol relates to the rest of the system (e.g. "Payment providers must not modify subscriptions directly").

Mark dangerous-to-break constraints explicitly with Google-style sections: `Important:`, `Note:`, `Warning:`, `Invariant:`. Treat them as red lines for the next editor.

### What does not belong

- Restating the signature, name, or types.
- Narrating the implementation (`"""Loop through items and add item.price to total."""`).
- Padding trivial functions — if behaviour is obvious from the code, omit the docstring entirely.

### Language rules

- **Python**: Google-style docstrings on **public** symbols (non-underscored).
- **C#**: XML `///` doc comments on **public** classes and methods. `<summary>` carries purpose; `<param>` / `<returns>` / `<exception>` cover non-obvious details only.
- Private (underscored Python, `private` / `internal` C#) members are exempt.

When behaviour changes, update the docstring / XML doc in the same change.

## Self-check before finalising

Before finishing, audit the diff: remove any inline comment that isn't a pragma or `TODO`/`FIXME`/`XXX`, and strip any docstring that just restates the signature or narrates the implementation.

## Supported Revit versions

2021–2027, with separate builds per version. The C# loader requires Revit 2021+; the legacy pure-Python loader (which supported older versions) has been removed.

- Revit 2021–2024: .NET Framework 4.8.
- Revit 2025–2026: .NET 8.0 (Windows).
- Revit 2027+: .NET 10.0 (Windows).

## Git workflow

- `develop` branch: active development — branch from here, PR back into it.
- `master` branch: release material only.
- `docs` branch: documentation website, published by CI — don't push to it directly.
- Run `git submodule update` after switching branches.
