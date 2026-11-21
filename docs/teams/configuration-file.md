# Configuration file

See the guide below to configure pyRevit in Revit UI

- [Configure pyRevit](../get-started/configure.md)

See the guide below to configure pyRevit using the CLI tool

- [Configure pyRevit](../cli/configure.md)

## Configuration File

!!! warning ""

    Preferably use the [pyRevit CLI](../cli/index.md) to make configuration changes to this file.

pyRevit configuration file is a standards INI file that contains various sections for each pyRevit component or tool.

The config file can be in one location only and that is `%APPDATA%/pyRevit`

## Seed Config File

A Seed configuration file can be provided at `%PROGRAMDATA%/pyRevit`. pyRevit will use this seed file to configure pyRevit:

- If the seed config file is Read-Only for the user, pyRevit will use this config file without recreating a new one under `%APPDATA%/pyRevit  
  `No other configuration changes are allowed to the config file since the file is Read-Only.
- If the seed config file is writable, then pyRevit will copy the seed into `%APPDATA%/pyRevit` and will start with this config file.  
  All the future changes to the configs are written to the main config file and not the seed. The seed is used only to bootstrap the main config.

### Core Configs

The most important section is the `[core]` that has all the runtime configurations.

```text
[core]
checkupdates = false
autoupdate = false
verbose = true
debug = false
filelogging = false
startuplogtimeout = 0
bincache = true
userextensions = []
loadbeta = false
rocketmode = true
requiredhostbuild = ""
cpyengine = 372
minhostdrivefreespace = 0
outputstylesheet = "C:\\Users\\eirannejad\\Desktop\\gits\\pyRevitDev\\pyrevitlib\\pyrevit\\output\\outputstyles.css"
user_locale = "en_us"
```

The settings below control the availability of the **Update**, **Extension Manager** and **Settings** tools (UI buttons) in pyRevit. If set to `false` the tool will be removed from the UI and won’t be availabe to the user:

```text
[core]
usercanupdate = true
usercanextend = true
usercanconfig = true
```

### Environment Configs

!!! warning ""

    This section is exclusively for the CLI tool that manages the environment. DO NOT CHANGE SETTINGS MANUALLY

```text
[environment]
clones = {}
```

### Routes Configs

These configs options are for the [pyRevit Routes (HTTP API)](routes.md)  

```text
[routes]
enabled = true
core_api = true
port = 48884
```

### Telemetery Configs

These configs options are for the  [Telemetry System](telemetry.md)

```text
[telemetry]
active = true
telemetry_file_dir = ""
telemetry_server_url = "http://data.tvapdx.com:8080/api/v2/scripts/"
active_app = true
apptelemetry_server_url = "http://data.tvapdx.com:8080/api/v2/events/"
apptelemetry_event_flags = "0x1d17e7f7ff59"
utc_timestamps = falsel
```

### Tab Coloring Configs

```text
[tabcoloring]
sort_colorize_docs = false
tabstyle_index = 8
family_tabstyle_index = 7
tab_colors = ["#FFF39C12","#FF2C3E50","#FF0000FF","#FF8B4513","#FFFFD700","#FF00CED1","#FFFF4500","#FF00FFFF","#FF9ACD32","#FFFF1493"]
tab_filtercolors = {}
```

### Minify UI Configs

```text
[MinifyUIconfig]
hidden_tabs = ["Tabname1","Tabname2","Tabname3"]
```
