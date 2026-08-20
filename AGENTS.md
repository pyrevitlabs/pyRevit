# Agent Instructions

Agent rules for the pyRevit repository.

---

## Repository organization

See [`docs/repo-organization.md`](docs/repo-organization.md).

## Project overview

pyRevit is a Rapid Application Development (RAD) environment for Autodesk Revit. It lets users write automation tools in Python (IronPython 2.7.12 default, CPython 3.12.3, or IronPython 3.4.0), C#, or VB.NET. The project also ships a CLI utility for deployment and a telemetry server for usage tracking.

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

See [`docs/architecture.md`](docs/architecture.md).

## Supported Revit versions

- Revit 2021–2024: .NET Framework 4.8.
- Revit 2025–2026: .NET 8.0 /.NET 10
- Revit 2027+: .NET 10.0

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

- [Developer Docs (Notion)](https://pyrevitlabs.notion.site/Developer-Docs-2c88f3ecccde422d9504e20b6b9e04f8)
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

- `develop` branch: active development — branch from here, PR back into it.
- `master` branch: release material only.
- `docs` branch: documentation website, published by CI — don't push to it directly.

1. Branch from `develop`.
2. Initialize submodules: `git submodule update --init --recursive` (also after switching branches).
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

Don't write inline comments. Ever. Code must be self-explanatory — if it isn't, improve names or extract a well-named function instead of explaining it in a comment. Keep pre-existing comments unless they're clearly outdated.

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
