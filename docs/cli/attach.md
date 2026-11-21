# Attach to Revit

`pyrevit` can detect the exact installed Revit versions on your machine. You can use the commands below to attach any pyRevit clone to any or all installed Revits. Make sure to specify the clone to be attached and the desired engine version:

```powershell
pyrevit attach <clone_name> (DEFAULT | <engine_version>) (<revit_year> | --installed | --attached) [--allusers] [--log=<log_file>]

$ pyrevit attach dev DEFAULT --installed    # attach `dev` clone to all installed Revits using defaultengine
$ pyrevit attach dev 2712 --installed       # attach `dev` clone to all installed Revits using 277 engine
$ pyrevit attach dev DEFAULT 2018       # attach `dev` clone to Revit 2018 using an engine that has no conflicts with Dynamo BIM
```

- `--``allusers`: Use this switch to attach for all users. It creates the manifest files inside the `%PROGRAMDATA%/Autodesk/Revit/Addons` instead of `%APPDATA%/Autodesk/Revit/Addons`
- `--attached`: This options is helpful when updating existing attachments e.g. specifying a new engine but keeping the same attachments as before

List all the attachments:

```powershell
$ pyrevit attached

==> Attachments
dev | Product: "Autodesk Revit 2020.0.1" | Engine: 277 | Path: "C:\pyRevitDev" | Manifest: "C:\..\2020\pyRevit.addin"
dev | Product: "Autodesk Revit 2019.2.1" | Engine: 277 | Path: "C:\pyRevitDev" | Manifest: "C:\..\2019\pyRevit.addin"
dev | Product: "Autodesk Revit 2018.3.3 Security Fix" | Engine: 277 | Path: "C:\pyRevitDev" | Manifest: "C:\..\2018\pyRevit.addin"
dev | Product: "Autodesk Revit 2017.2.5 Security Fix" | Engine: 277 | Path: "C:\pyRevitDev" | Manifest: "C:\..\2017\pyRevit.addin"
dev | Product: "Autodesk Revit 2016 Update 7 for R2" | Engine: 277 | Path: "C:\pyRevitDev" | Manifest: "C:\..\2016\pyRevit.addin"
dev | Product: "Autodesk Revit 2014 First Customer Ship" | Engine: 277 | Path: "C:\pyRevitDev" | Manifest: "C:\..\2014\pyRevit.addin"
```

You can also switch between the attached clones using the switch command:

```powershell
pyrevit switch <clone_name>

$ pyrevit switch main

==> Attachments
main | Product: "Autodesk Revit 2020.0.1" | Engine: 277 | Path: "C:\pyRevitMain" | Manifest: "C:\..\2020\pyRevit.addin"
```

The switch command with detect all the existing attachments and will remap them to the new clone using the same engine.

Detaching pyRevit from a specific Revit version or all installed:

```powershell
pyrevit detach (--all | <revit_year>) [--log=<log_file>]

$ pyrevit detach --all
$ pyrevit detach 2019
```
