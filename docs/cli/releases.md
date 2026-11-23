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
==> Releases
pyRevit v<version> | Tag: v<version> | Version: <version> | Url: "https://github.com/pyrevitlabs/pyRevit/releases/tag/v<version>"
```

Add `--notes` to print the release notes under each release, and a search pattern to filter by version:

```powershell
$ pyrevit releases <search_pattern> --notes
```

```powershell
# opens the latest release web page
$ pyrevit releases open latest
```

```powershell
# download the archive
$ pyrevit releases download archive <search_pattern> --dest="%USERPROFILE%\Downloads"

# or the installer
$ pyrevit releases download installer <search_pattern> --dest="%USERPROFILE%\Downloads"
```
