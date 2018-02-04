`Install_addin.bat`
`uninstall_addin.bat`

Use these scripts to manually add or remove pyRevit from installed Revit versions.

`upgrade.bat`

Use this script to manually update pyRevit. This is especially helpful when pyRevit core needs to be updated outside of Revit and when Revit is closed. This script call `uninstall_addin.bat` and `Install_addin.bat` after update.

**pyrevitgitservices**

This directory contains the source code (Visual studio solution) for a general purpose tool to support the git commands necessary to keep pyrevit updated or set to a specific version.

``` batch
REM Cloning pyRevit into a directory:
pyrevitgitservices.exe clone <destination_path_to_clone_pyrevit_into>

REM Updating an installed version of pyRevit to most recent:
pyrevitgitservices.exe update <pyrevit_installed_path>

REM Setting an installed version of pyRevit to a specific commit
REM Techinically this is HARD rebasing the git repo to that commit
pyrevitgitservices.exe setversion <pyrevit_installed_path> <target_commit_hash>
```

**setupmaker**

This folder contains the InnoSetupMaker script to create the pyRevit installer
