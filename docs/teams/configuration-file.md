# Configuration file

See the guide below to configure pyRevit in Revit UI

- [Configure pyRevit](../get-started/configure.md)

See the guide below to configure pyRevit using the CLI tool

- [Configure pyRevit](../cli/configure.md)

## Configuration File

!!! warning ""

    Preferably use the [pyRevit CLI](../cli/index.md) to make configuration changes to this file.

pyRevit configuration file is a standard INI file that contains various sections for each pyRevit component or tool.

## Which file pyRevit uses

- **Installed for the current user**: `%APPDATA%\pyRevit\pyRevit_config.ini`.
- **Installed for all users**: a standard user still gets a file under `%APPDATA%\pyRevit`, seeded from the machine-wide file when one exists. An elevated process, such as the admin installer or the CLI run as administrator, reads and writes the machine-wide file in `%PROGRAMDATA%\pyRevit` directly.
- **Locked machine-wide file**: when the file in `%PROGRAMDATA%\pyRevit` has the Windows read-only attribute, every user and every install scope uses it as is, and no setting can be changed.

## Seed Config File

`pyrevit configs seed` copies the current configuration to `%PROGRAMDATA%\pyRevit`. Each user's pyRevit then starts from that file the first time it loads.

`pyrevit configs seed --lock` also sets the read-only attribute on the seeded file. That locks the configuration for every user of the machine. Only the read-only attribute locks the file; removing write permissions does not.

### Core Configs

The most important section is the `[core]` that has all the runtime configurations.

```text
[core]
checkupdates = false
autoupdate = false
verbose = true
debug = false
filelogging = false
startuplogtimeout = 10
bincache = true
userextensions = []
loadbeta = false
rocketmode = true
requiredhostbuild = ""
cpyengine = 3123
minhostdrivefreespace = 0
closeotheroutputs = false
closeoutputmode = "currentcommand"
outputstylesheet = "C:\\Standards\\pyRevit\\outputstyles.css"
user_locale = "en_us"
colorize_docs = false
tooltip_debug_info = false
```

`cpyengine` is the id of the CPython engine, see [Engines](../runtime/engines.md).

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
host = "127.0.0.1"
core_api = true
port = 48884
```

`host` is the address the server listens on. When it is empty or missing, the server listens on every network interface. The server does not authenticate callers, so only open it to the network on purpose.

### Telemetry Configs

These configs options are for the  [Telemetry System](telemetry.md)

```text
[telemetry]
active = false
telemetry_file_dir = ""
telemetry_server_url = ""
active_app = false
apptelemetry_server_url = ""
apptelemetry_event_flags = "0x1d17e7f7ff59"
utc_timestamps = true
include_hooks = false
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
