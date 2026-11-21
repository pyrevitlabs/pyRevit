# Releases

You can get information, and download the archive or installer for pyRevit releases using the cli tool.

```powershell
pyrevit releases [--notes]
pyrevit releases <search_pattern> [--notes]
pyrevit releases open latest
pyrevit releases open <search_pattern>
pyrevit releases download (installer | archive) latest --dest=<dest_path>
pyrevit releases download (installer | archive) <search_pattern> --dest=<dest_path>
```

```powershell
$ pyrevit releases
pyRevit v4.7.0-beta (pre-release) | Tag: v4.7.0-beta | Version: 4.7.0 | Url: "https://github.com/pyrevitlabs/pyRevit/releases/tag/v4.7.0-beta"
pyRevit v4.6.15 | Tag: v4.6.15 | Version: 4.6.15 | Url: "https://github.com/pyrevitlabs/pyRevit/releases/tag/v4.6.15"
pyRevit v4.6.14 | Tag: v4.6.14 | Version: 4.6.14 | Url: "https://github.com/pyrevitlabs/pyRevit/releases/tag/v4.6.14"
pyRevit v4.6.13 | Tag: v4.6.13 | Version: 4.6.13 | Url: "https://github.com/pyrevitlabs/pyRevit/releases/tag/v4.6.13"
pyRevit v4.6.12 | Tag: v4.6.12 | Version: 4.6.12 | Url: "https://github.com/pyrevitlabs/pyRevit/releases/tag/v4.6.12"
```

```powershell
$ pyrevit releases 4.7 --notes
==> Releases
pyRevit v4.7.0-beta (pre-release) | Tag: v4.7.0-beta | Version: 4.7.0 | Url: "https://github.com/pyrevitlabs/pyRevit/releases/tag/v4.7.0-beta"
        New features:
        - CPython command execution engine (v3.6.8 and v3.7.2)
        - `.run` Extensions for `pyrevit run` commands
        Updates:
        - Improvements and fixes Re #520 #513
        - Misc fixes
```

```powershell
# opens the latest release web page
$ pyrevit releases open latest
```

```powershell
# download the archive
$ pyrevit releases download archive 4.6.15 --dest="C:\Users\*\Downloads"

# or the installer
$ pyrevit releases download installer 4.6.15 --dest="C:\Users\*\Downloads"
```
