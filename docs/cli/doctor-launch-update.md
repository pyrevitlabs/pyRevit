# Doctor, launch and update

## Repair an installation with `doctor`

`pyrevit doctor` removes what a broken or half-removed installation leaves behind. Close Revit first: without `--dryrun` the command stops when `Revit.exe` is running.

```powershell
pyrevit doctor --list                    # list the doctor commands
pyrevit doctor purge-all --dryrun        # report what would be removed, change nothing
pyrevit doctor purge-all                 # remove it
```

| Command | What it does |
|---|---|
| `purge-installs` | Cleans up records of old installations from the registry |
| `purge-files` | Deletes install and data folders, Revit add-in manifests and PATH entries |
| `purge-all` | Runs `purge-files` and `purge-installs` and removes MCP registrations |

| Option | Effect |
|---|---|
| `--dryrun` | Reports what would be removed without changing anything |
| `--force` | Also purges uninstall entries whose install is still present (`purge-installs`, `purge-all`) |
| `--keep-config` | Keeps `pyRevit_config.ini`. Without it the file is backed up to Documents and deleted (`purge-files`, `purge-all`) |
| `--keep-extensions` | Keeps the Extensions folder in the pyRevit data folders. Without it the folder is backed up to a zip in Documents and deleted (`purge-files`, `purge-all`) |

When pyRevit is broken or not installed, download `pyrevit-doctor.exe` from the [releases page](https://github.com/pyrevitlabs/pyRevit/releases) and run it on its own. It takes the same commands and options and needs the .NET 8 runtime or newer.

## Start Revit on a clone with `launch`

`pyrevit launch` starts Revit on a pyRevit clone and engine without changing the attachment. The command stays running while Revit runs and removes its temporary files when Revit exits.

```powershell
pyrevit launch <clone_name_or_path> (default | <engine_version>) <revit_year> [<model_file>] [--isolated] [--language=<code>]

pyrevit launch dev default 2026                    # the dev clone on the default engine
pyrevit launch dev 342 2026 --isolated             # IronPython 3, with its own config folder
pyrevit launch "C:\pyRevit\dev" default 2026 "C:\Models\Test.rvt"
```

| Argument | Meaning |
|---|---|
| `<clone_name_or_path>` | Name of a registered clone, or the path of a clone |
| `default` or `<engine_version>` | The default engine, or an engine id from [Engines](../runtime/engines.md) |
| `<model_file>` | Model file Revit opens once it has started |
| `--isolated` | Gives the session its own pyRevit config folder, seeded with a copy of the current config |
| `--language=<code>` | Revit UI language code, for example `ENU` |

## Refresh CLI data with `update`

`pyrevit update` updates the remote resources the CLI uses, such as the Revit product information. It does not update pyRevit itself: use [`pyrevit clones update`](clones.md) and [`pyrevit extensions update`](extensions.md) for that.
