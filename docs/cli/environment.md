# Environment info

Use `env` command to get info about the current `pyrevit` environment:

```powershell
pyrevit env
```

#### Registered Clones

The command shows a list of registered clones (deployed or full git repositories). `dev` is the name of the registered clone in the example below.

```text
==> Registered Clones (full git repos)
dev | Branch: "develop/newexec" | Version: "4.7-beta:0ed38ee" | Path: "C:\pyRevit"

==> Registered Clones (deployed from archive/image)
```

#### Attachments

The command shows pyRevit attachments to installed Revits. `dev` is the name of the attached clone in the example below.

```text
==> Attachments
dev | Product: "2020.1 Update" | Engine: 277 | Path: "C:\pyRevit" | Manifest: "C:\Users\pyrevitlabs\AppData\Roaming\Autodesk\Revit\Addins\2020\pyRevit.addin"
dev | Product: "2019.2.2 Hotfix" | Engine: 277 | Path: "C:\pyRevit" | Manifest: "C:\Users\pyrevitlabs\AppData\Roaming\Autodesk\Revit\Addins\2019\pyRevit.addin"
dev | Product: "2018.3.3 Security Fix" | Engine: 277 | Path: "C:\pyRevit" | Manifest: "C:\Users\pyrevitlabs\AppData\Roaming\Autodesk\Revit\Addins\2018\pyRevit.addin"
dev | Product: "2017.2.5 Security Fix" | Engine: 277 | Path: "C:\pyRevit" | Manifest: "C:\Users\pyrevitlabs\AppData\Roaming\Autodesk\Revit\Addins\2017\pyRevit.addin"
dev | Product: "2016.1.9 Security Fix" | Engine: 277 | Path: "C:\pyRevit" | Manifest: "C:\Users\pyrevitlabs\AppData\Roaming\Autodesk\Revit\Addins\2016\pyRevit.addin"
dev | Product: "2014 First Customer Ship" | Engine: 277 | Path: "C:\pyRevit" | Manifest: "C:\Users\pyrevitlabs\AppData\Roaming\Autodesk\Revit\Addins\2014\pyRevit.addin"
```

#### Extensions

The command shows a list of installed extensions, search paths, and lookup sources.

```text
==> Installed Extensions

==> Default Extension Search Path
C:\Users\pyrevitlabs\AppData\Roaming\pyRevit\Extensions

==> Extension Search Paths

==> Extension Sources - Default
https://github.com/pyrevitlabs/pyRevit/raw/master/extensions/extensions.json

==> Extension Sources - Additional
```

#### Installed Revit

The command shows a list of installed Revit versions and running Revit instances

```text
==> Installed Revits
2020.1 Update | Version: 20.1.0.81 | Build: 20190725_1135(x64) | Language: 1033 | Path: "C:\Program Files\Autodesk\Revit 2020"
2019.2.2 Hotfix | Version: 19.2.20.24 | Build: 20190808_0900(x64) | Language: 1033 | Path: "C:\Program Files\Autodesk\Revit 2019"
2018.3.3 Security Fix | Version: 18.3.3.18 | Build: 20190510_1515(x64) | Language: 1033 | Path: "C:\Program Files\Autodesk\Revit 2018"
2017.2.5 Security Fix | Version: 17.0.1169.0 | Build: 20190508_0315(x64) | Language: 1033 | Path: "C:\Program Files\Autodesk\Revit 2017"
2016.1.9 Security Fix | Version: 16.0.1218.0 | Build: 20190508_0715(x64) | Language: 1033 | Path: "C:\Program Files\Autodesk\Revit 2016"
2014 First Customer Ship | Version: 13.3.8151 | Build: 20130308_1515(x64) | Language: 1033 | Path: "C:\Program Files\Autodesk\Revit 2014"

==> Running Revit Instances
PID: 27532 | 2019.2.2 Hotfix | Version: 19.2.20.24 | Build: 20190808_0900(x64) | Language: 0 | Path: "C:\Program Files\Autodesk\Revit 2019"
```

#### User Environment

The command shows a series of useful information about the user environment

```text
==> User Environment
Microsoft Windows 10 [Version 10.0.18362]
Executing User: **\pyrevitlabs
Active User: **\pyrevitlabs
Adming Access: Yes
%APPDATA%: "C:\Users\pyrevitlabs\AppData\Roaming"
Latest Installed .Net Framework: 4.8
Installed .Net Target Packs: v3.5 v4.0 v4.5 v4.5.1 v4.5.2 v4.6 v4.6.1 v4.7.1 v4.7.2 v4.X
Installed .Net-Core Target Packs: v2.1.401 v2.1.402 v2.1.403 v2.1.500 v2.1.502 v2.1.503 v2.1.504 v2.1.505 v2.1.507 v2.1.508
pyRevit CLI 0.14.0.0
```

## Environment Data

The environment information can also be exported into JSON

```powershell
pyrevit env --json
```

#### Example

```json
{
    "meta": {
      "version": "0.1.0"
    },
    "clones": [
      {
        "name": "dev",
        "clonePath": "C:\\Users\\eirannejad\\Desktop\\gits\\pyRevitDev",
        "extensionsPath": "C:\\Users\\eirannejad\\Desktop\\gits\\pyRevitDev\\extensions",
        "isRepoDeploy": true,
        "isValid": true,
        "hasDeployments": true,
        "moduleVersion": "4.7-beta",
        "branch": "develop/newexec",
        "commit": "0ed38ee4e58a3da5c3bf08eaffca58fbd6fcb1a1",
        "shortCommit": "0ed38ee",
        "origin": "https://github.com/pyrevitlabs/pyRevit.git"
      }
    ],
    "attachments": [
      {
        "manifest": {
          "filePath": "C:\\Users\\eirannejad\\AppData\\Roaming\\Autodesk\\Revit\\Addins\\2020\\pyRevit.addin",
          "name": "PyRevitLoader",
          "assembly": "C:\\Users\\eirannejad\\Desktop\\gits\\pyRevitDev\bin\\engines\\277\\pyRevitLoader.dll",
          "addInId": "B39107C3-A1D7-47F4-A5A1-532DDF6EDB5D",
          "fullClassName": "PyRevitLoader.PyRevitLoaderApplication",
          "vendorId": "eirannejad"
        },
        "product": {
          "name": "2020.1 Update",
          "productYear": 2020,
          "version": "20.1.0.81",
          "buildNumber": "20190725_1135",
          "buildTarget": "x64",
          "defaultInstallLocation": "C:\\Program Files",
          "installLocation": "C:\\Program Files\\Autodesk\\Revit 2020",
          "executiveLocation": "C:\\Program Files\\Autodesk\\Revit 2020\\Revit.exe",
          "languageCode": 1033
        },
        "attachmentType": 1,
        "clone": {
          "name": "dev",
          "clonePath": "C:\\Users\\eirannejad\\Desktop\\gits\\pyRevitDev",
          "extensionsPath": "C:\\Users\\eirannejad\\Desktop\\gits\\pyRevitDev\\extensions",
          "isRepoDeploy": true,
          "isValid": true,
          "hasDeployments": true,
          "moduleVersion": "4.7-beta",
          "branch": "develop/newexec",
          "commit": "0ed38ee4e58a3da5c3bf08eaffca58fbd6fcb1a1",
          "shortCommit": "0ed38ee",
          "origin": "https://github.com/pyrevitlabs/pyRevit.git"
        },
        "engine": {
          "version": 277,
          "runtime": true,
          "path": "C:\\Users\\eirannejad\\Desktop\\gits\\pyRevitDev\bin\\engines\\277",
          "assemblyName": "pyRevitLoader.dll",
          "kernelName": "IronPython",
          "assemblyPath": "C:\\Users\\eirannejad\\Desktop\\gits\\pyRevitDev\bin\\engines\\277\\pyRevitLoader.dll",
          "description": "Compatible with RevitPythonShell",
          "compatibleProducts": []
        },
        "allUsers": false
      }
    ],
    "extensions": [],
    "searchPaths": ["C:\\Users\\eirannejad\\AppData\\Roaming\\pyRevit\\Extensions"],
    "lookupSources": ["https://github.com/pyrevitlabs/pyRevit/raw/master/extensions/extensions.json"],
    "installed": [
      {
        "name": "2020.1 Update",
        "productYear": 2020,
        "version": "20.1.0.81",
        "buildNumber": "20190725_1135",
        "buildTarget": "x64",
        "defaultInstallLocation": "C:\\Program Files",
        "installLocation": "C:\\Program Files\\Autodesk\\Revit 2020",
        "executiveLocation": "C:\\Program Files\\Autodesk\\Revit 2020\\Revit.exe",
        "languageCode": 1033
      }
    ],
    "running": [],
    "pyrevitDataDir": "C:\\Users\\eirannejad\\AppData\\Roaming\\pyRevit",
    "userEnv": {
      "osVersion": "Microsoft Windows 10 [Version 10.0.18362]",
      "execUser": "**\\eirannejad",
      "activeUser": "**\\eirannejad",
      "isAdmin": true,
      "userAppdata": "C:\\Users\\eirannejad\\AppData\\Roaming",
      "latestFramework": "4.8",
      "targetPacks": [
        "C:\\Program Files (x86)\\Reference Assemblies\\Microsoft\\Framework\\.NETFramework3.5",
        "C:\\Program Files (x86)\\Reference Assemblies\\Microsoft\\Framework\\.NETFramework4.0",
        "C:\\Program Files (x86)\\Reference Assemblies\\Microsoft\\Framework\\.NETFramework4.7.2",
      ],
      "targetPacksCore": [],
      "cliVersion": "0.14.0.0"
    }
  }
```
