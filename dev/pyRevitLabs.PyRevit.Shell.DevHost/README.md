# pyRevit Shell Dev Host

Use this development-only application to work on the interactive shell without starting Revit.

## Prerequisites

Build the shell before launching the host:

```powershell
dotnet build dev/pyRevitLabs.PyRevit.Shell/pyRevitLabs.PyRevit.Shell.csproj -c "Release IPY2712PR"
```

## Build & run

From the repository root:

```powershell
dotnet run --project dev/pyRevitLabs.PyRevit.Shell.DevHost -c Debug
```

To rebuild the shell before running:

```powershell
dotnet run --project dev/pyRevitLabs.PyRevit.Shell.DevHost -c Debug -p:BuildShellBeforeHost=true
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
```
