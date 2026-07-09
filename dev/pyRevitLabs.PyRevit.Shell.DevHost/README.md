# pyRevit Shell — Dev Host (NOT shipped)

`pyRevitShellDevHost` is a **development-only** executable that launches the interactive Python
Shell (REPL + AvalonEdit editor) **outside of Revit**, so you can iterate on the shell UI/REPL
without starting Revit.

- It is **not** referenced by `pyRevitLabs.sln`, the runtime solution, or the product build
  pipeline (`build/` / `pyRevit.Build.exe`), so it is never built in CI and never ships to end
  users. Its `bin/`/`obj/` are gitignored.
- It references the already-built shell + IronPython/AvalonEdit DLLs from the deployed engine
  folder (`bin/netcore/engines/IPY2712PR/`), so the shell must be built first (once).
- It mirrors `ShellLauncher`'s modal path but drops the Revit-specific pieces (`UIApplication`,
  `ExternalEvent`, runtime-builtin injection). Statements run on the UI dispatcher and the
  engine gets a plain IronPython environment with pyRevit's library paths on `sys.path`.

## Prerequisites

The IronPython engine DLLs must be present in `bin/netcore/engines/IPY2712PR/` (they get there
after a product build). If `bin/` is empty, run the build once:

```powershell
cd build
dotnet run -c Release -- ci
```

…or just build the shell (which also deploys it to the engine folder):

```powershell
dotnet build dev/pyRevitLabs.PyRevit.Shell/pyRevitLabs.PyRevit.Shell.csproj -c "Release IPY2712PR"
```

## Build & run

From the repository root (the shell must be built first — see Prerequisites):

```powershell
dotnet run --project dev/pyRevitLabs.PyRevit.Shell.DevHost -c Debug
```

This compiles the host against the already-deployed shell DLL and runs it. After you change
shell sources, rebuild the shell first:

```powershell
dotnet build dev/pyRevitLabs.PyRevit.Shell/pyRevitLabs.PyRevit.Shell.csproj -c "Debug IPY2712PR"
```

Or do it in one step by enabling the `BuildShellBeforeHost` target (it rebuilds the shell and
deploys the fresh DLL before compiling the host; needs a NuGet restore, so it requires network
or a warm package cache):

```powershell
dotnet run --project dev/pyRevitLabs.PyRevit.Shell.DevHost -c Debug -p:BuildShellBeforeHost=true
```

To build a runnable `.exe` instead of `dotnet run`:

```powershell
dotnet build dev/pyRevitLabs.PyRevit.Shell.DevHost -c Debug -p:BuildShellBeforeHost=false
# then run:
dev\pyRevitLabs.PyRevit.Shell.DevHost\bin\Debug\net8.0-windows\pyRevitShellDevHost.exe
```

## Options

| Arg | Effect |
|-----|--------|
| *(default)* | Open the editor + REPL window (`InteractiveEditorWindow`) |
| `--console` | Open the REPL-only window (`InteractiveShellWindow`) |
| `--dark` | Render with the dark theme (light by default) |

App arguments go after `--` so `dotnet run` does not consume them:

```powershell
# editor + REPL, dark theme
dotnet run --project dev/pyRevitLabs.PyRevit.Shell.DevHost -c Debug -- --dark

# REPL-only window, dark theme
dotnet run --project dev/pyRevitLabs.PyRevit.Shell.DevHost -c Debug -- --dark --console

# from the built exe
dev\pyRevitLabs.PyRevit.Shell.DevHost\bin\Debug\net8.0-windows\pyRevitShellDevHost.exe --dark
```

## Notes

- This host exercises the same `IronPythonConsoleControl` / `PythonConsoleHost` /
  `InteractiveShellWindow` / `InteractiveEditorWindow` types the real shell uses, so it is a
  faithful smoke test for the shell surface — just without a Revit API context. Anything that
  needs `__revit__` / the pyRevit runtime will not work here (by design).
- Close Revit before rebuilding the shell (engine DLLs in `bin/netfx|netcore/engines/` are
  locked while Revit runs — same constraint as the normal product build).

