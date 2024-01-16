# Adding submodules from pyRevitLabs

1. Add fork to pyRevitLabs github <https://github.com/pyrevitlabs>
2. Make sure you have a pyrevit-main branch
3. From pyRevit root folder run the git commands accordingly. Here are 3 examples

```git
    git submodule add -b pyrevit-main https://github.com/pyrevitlabs/Newtonsoft.Json.git dev/modules/pyRevitLabs.Newtonsoft.Json
    git submodule add -b pyrevit-main https://github.com/pyrevitlabs/NLog.git dev/modules/pyRevitLabs.NLog
    git submodule add -b pyrevit-main https://github.com/pyrevitlabs/MahApps.Metro.git dev/modules/pyRevitLabs.MahApps.Metro
```
