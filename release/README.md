`Install_addin.bat`
`uninstall_addin.bat`

Use these scripts to manually add or remove pyRevit from installed Revit versions. These scripts add or remove the addin manifest files inside `%ProgramData%/Autodesk/Revit/Addins` (for all users) and `%AppData%/Autodesk/Revit/Addins` for current user.

### setupmaker/

This folder contains the **InnoSetupMaker** script to create the pyRevit installer executive. It depends on the `../bin/pyrevit.exe` tool that handles all pyRevit installation activities and configurations. The path of this tool will be added to the system `%path%` and you can use it to configure pyRevit remotely. See pyRevit docs for full documentation on this tool.
