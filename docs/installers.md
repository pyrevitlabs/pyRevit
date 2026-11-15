# Installers

Each release publishes two products, each as a per-user and an all-users (admin) installer:

| Installer | Installs | Scope |
|---|---|---|
| `pyRevit_<version>_signed.exe` | pyRevit and its CLI | Current user, no elevation. Installs to `%APPDATA%\pyRevit-Master` and puts the CLI on the user `PATH`. |
| `pyRevit_<version>_admin_signed.exe` | pyRevit and its CLI | All users. Installs to `Program Files\pyRevit-Master`, puts the CLI on the system `PATH` and attaches pyRevit to Revit for all users. |
| `pyRevit_CLI_<version>_signed.exe` | The CLI only | Current user, no elevation. |
| `pyRevit_CLI_<version>_admin_signed.exe` (also as `.msi`) | The CLI only | All users, system `PATH`. |

## Which installer to use

Install pyRevit with one of the **pyRevit** installers. It already contains the CLI (`pyrevit.exe`), so there is no need to install the CLI installer as well.

The **pyRevit CLI** installers are for administrators who deploy and configure pyRevit themselves with `pyrevit clones` and `pyrevit attach`, for example in a deployment script. They install `pyrevit.exe` and nothing else: no pyRevit clone and no extensions.

## What the CLI installers do to an existing setup

This is by design. Installing, and uninstalling, the CLI starts from a clean slate by running:

```shell
pyrevit caches clear --all
pyrevit detach --all
```

`pyrevit detach --all` removes the pyRevit `.addin` manifests from every Revit version. Running a CLI installer on a machine where pyRevit is already installed therefore leaves Revit without pyRevit until you attach a clone again, for example with `pyrevit attach <clone-name> default --installed`. Uninstalling the CLI runs the same two commands.

The pyRevit installers run the same two commands, then register the installed clone and attach it to Revit again, so Revit has pyRevit when they finish.

If pyRevit disappeared from Revit after you installed the CLI, either run the pyRevit installer again or attach the existing clone with `pyrevit attach`.
