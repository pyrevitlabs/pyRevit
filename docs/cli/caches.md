# Caches

Cache files are stored under `%APPDATA%/pyRevit/<revit-version>`. You can clear all or specific Revit version caches. Revit needs to be closed for this operaton since it keeps the files locked if it is open:

```powershell
pyrevit caches [bim360] clear (--all | <revit_year>) [--log=<log_file>]

$ pyrevit caches clear --all    # clear all caches for all Revits
$ pyrevit caches clear 2018     # clear all caches for Revit 2018
```

### Clearing BIM360 Caches

You can also use the pyRevit CLI to clear local BIM360 caches for the installed Revit versions

```powershell
pyrevit caches bim360 clear (--all | <revit_year>) [--log=<log_file>]

$ pyrevit caches bim360 clear --all    # clear all bim360 caches for all Revits
$ pyrevit caches bim360 clear 2018     # clear all bim360 caches for Revit 2018
```
