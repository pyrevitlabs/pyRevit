`Install_addin.bat`
`uninstall_addin.bat`

Use these scripts to manually add or remove pyRevit from installed Revit versions.

`upgrade.bat`

Use this script to manually update pyRevit. This is especially helpful when pyRevit core needs to be updated outside of Revit and when Revit is closed

**pyRevitCloner**

This directory contains the source code (Visual studio solution) for a simple git cloner app that is part of
the pyRevit installer.
 
**pyRevitCoreUpdater**

When Revit is loaded, `pyRevitLoader.dll` is open by Revit instance and `git` can not overwrite this core dll to the newest version. This command is a generic tool to update any git repository to its tracked branch head. In case of pyRevit, it will update the pyRevit repository to the newest version.
 
**setupmaker**

This folder contains the InnoSetupMaker script to create the pyRevit installer 
