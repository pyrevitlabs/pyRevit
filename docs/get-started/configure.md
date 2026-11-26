# Configure pyRevit

pyRevit ships with a decent set of configuration defaults. To change them, open **Settings** in the **pyRevit** panel of the **pyRevit** tab. Shift-click the button to show the configuration file in Explorer instead.

The window is a list of sections, described below. **Just Save Settings** saves without reloading, **Save Settings and Reload** saves and reloads pyRevit. Some options need a reload or a Revit restart, and the window says so next to them.

When an administrator has locked the configuration, the window shows *pyRevit settings are set by your admin* and the settings cannot be changed. See [Configuration file](../teams/configuration-file.md).

## Core Settings

### General

**Rocket Mode** lets pyRevit keep one engine per extension that supports it, which makes tools start faster.

**Check updates at startup** checks every installed extension for updates when Revit starts.

![General settings: Rocket Mode and Check updates at startup](../assets/get-started/configure/settings-general.png)

### Engines

**Active Engine** is the IronPython engine pyRevit is attached with, and **Active CPython Engine** is the engine used by scripts that ask for CPython. Restart Revit after changing either one. [Engines](../runtime/engines.md) lists the engines shipped with pyRevit.

![Engines settings](../assets/get-started/configure/settings-engines.png)

### Development

**Load Beta Tools** loads the tools marked as beta.

**Close other open consoles** closes the output windows that are already open when a new script runs, either those of the same command or all of them.

![Development settings: Load Beta Tools and Close other open consoles](../assets/get-started/configure/settings-development.png)

### Loader

**Read script metadata** makes pyRevit read `__title__`, `__author__`, `__doc__` and the other in-script variables from Python scripts. Turning it off speeds up loading, but commands lose the metadata defined in their scripts. Values from `bundle.yaml` are used either way.

![Loader settings](../assets/get-started/configure/settings-loader.png)

### Caching

Select the type of extension cache pyRevit creates on startup.

![Caching settings](../assets/get-started/configure/settings-caching.png)

## Environment Variables

Lists the pyRevit environment variables of the current session and their values. Right-click a variable to copy its name or its value.

![Environment Variables section](../assets/get-started/configure/settings-environment-variables.png)

## Reporting Levels

pyRevit has a logging system that reports its activity on several levels. Select how much pyRevit shows, especially at load time, and after how many seconds the startup window closes when there is no error.

**File debug logging** writes all the runtime logs to a file. This slows pyRevit down, so only activate it to debug a problem. See [Reporting issues](../help/reporting-issues.md).

![Reporting Levels section](../assets/get-started/configure/settings-reporting-levels.png)

## Startup Checks

Set a required Revit build number and a minimum free space on the host drive. pyRevit shows a warning at startup when the running Revit does not match.

![Startup Checks section](../assets/get-started/configure/settings-startup-checks.png)

Example of the warning in the output window:

```text
WARNING: [pyrevit.loader.systemdiag] You are not using the required host build: 20190508_0315
```

## Routes

Turns the Routes server on and off, and its built-in REST API. See [Routes (HTTP API)](../teams/routes.md).

![Routes section](../assets/get-started/configure/settings-routes.png)

## Agent Runtime (MCP)

Lets MCP coding agents read and change the open model through pyRevit. It is off by default. See [Agent runtime](../agent-runtime.md).

![Agent Runtime section](../assets/get-started/configure/settings-agent-runtime.png)

## Telemetry

Sets where pyRevit sends script and application telemetry. Both are off by default. See [Telemetry](../teams/telemetry.md).

## Supported Revit Versions

Select the installed Revit versions pyRevit is attached to. pyRevit loads in the versions that are checked.

![Supported Revit Versions section](../assets/get-started/configure/settings-supported-revit-versions.png)

## UI / UX

- **Region Settings**: the language of the pyRevit user interface. pyRevit is not yet translated to all the listed languages, see [Translate pyRevit](../contribute/translate.md).
- **Ribbon**: whether the pyRevit ribbon tabs show an icon.
- **Tab Coloring**: colors the Revit document tabs by document. See [Tab Coloring](../tools/tab-coloring.md).
- **Output Window**: a CSS file to style the output window. Use the default as a starting point.

![UI / UX section: Region Settings and Ribbon](../assets/get-started/configure/settings-ui-ux.png)

## Custom Extension Directories

Manage the extra folders pyRevit searches for extensions. See [Install extensions](install-extensions.md).

![Custom Extension Directories section](../assets/get-started/configure/settings-custom-extension-directories.png)
