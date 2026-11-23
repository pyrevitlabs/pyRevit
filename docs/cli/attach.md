# Attach to Revit

`pyrevit` can detect the exact installed Revit versions on your machine. You can use the commands below to attach any pyRevit clone to any or all installed Revits. Make sure to specify the clone to be attached and the desired engine version:

```powershell
pyrevit attach <clone_name> (default | <engine_version>) (<revit_year> | --installed | --attached) [--allusers] [--log=<log_file>]

$ pyrevit attach dev default --installed    # attach `dev` clone to all installed Revits using the default engine
$ pyrevit attach dev 342 --installed        # attach `dev` clone to all installed Revits using the IronPython 3.4.2 engine
$ pyrevit attach dev default 2026           # attach `dev` clone to Revit 2026 using the default engine
```

- `<engine_version>`: the id of a runtime engine, see [Engines](../runtime/engines.md)
- `--allusers`: attach for all users. The manifest is written to the all-users add-ins folder instead of `%APPDATA%\Autodesk\Revit\Addins`. See [Where Revit loads add-ins from](../help/installation-issues.md#where-revit-loads-add-ins-from)
- `--attached`: This option is helpful when updating existing attachments e.g. specifying a new engine but keeping the same attachments as before

List all the attachments:

```powershell
$ pyrevit attached

==> Attachments
dev | Product: "<Revit product name>" | Engine: IPY2712PR (2712) | Path: "C:\pyRevit\dev"
```

An attachment for all users ends with `| AllUsers`.

You can also switch between the attached clones using the switch command:

```powershell
pyrevit switch <clone_name>

$ pyrevit switch main
```

The switch command will detect all the existing attachments and will remap them to the new clone using the same engine.

Detaching pyRevit from a specific Revit version or all installed:

```powershell
pyrevit detach (--all | <revit_year>) [--log=<log_file>]

$ pyrevit detach --all
$ pyrevit detach 2019
```
