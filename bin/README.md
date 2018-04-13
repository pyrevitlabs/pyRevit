**pyrevit manager**

This directory contains the source code (Visual studio solution) for a general purpose tool to support the git commands necessary to keep pyrevit updated or set to a specific version.

``` batch
REM Cloning pyRevit into a directory:
pyrevit install <destination_path_to_clone_pyrevit_into>

REM Updating an installed version of pyRevit to most recent:
pyrevit update <pyrevit_installed_path>

REM Setting an installed version of pyRevit to a specific commit
REM Techinically this is HARD rebasing the git repo to that commit
pyrevit setversion <pyrevit_installed_path> <target_commit_hash>
```
