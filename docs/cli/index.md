# CLI

`pyrevit` is the command-line tool, developed specifically to install and configure pyRevit in your production/development environment. There is a lot of commands and options available in the CLI tool. This document will guide you in using these commands and options based on what you’re trying to achieve. Each section below showcases a specific set of functionality of the command-line tool.

## Environment Management

- [Get Environment Info](environment.md)
- [Manage pyRevit clones](clones.md)
- [Manage pyRevit extensions](extensions.md)
- [Configure pyRevit](configure.md)
- [Attach pyRevit to Installed Revits](attach.md)
- [Clear pyRevit Cache Files](caches.md)

## Misc Functions

- [Batch Process Revit Models](run.md)
- [Manage Installed Revit](revits.md)
- [Get Release Info](releases.md)

List the help for each command,  
by adding the `--help` flag

```powershell
$ pyrevit --help        # will print help to console (-h shorthand)
```

Every command has its own help: add `--help` after the command name, for example `pyrevit clones --help`.

To determine the version of your installed CLI tool

```powershell
$ pyrevit --version     # -V shorthand
```

To access a variety of online resource, use these commands

```powershell
$ pyrevit wiki      # pyRevit wiki page
$ pyrevit docs      # pyRevit documentation
$ pyrevit source    # pyRevit source code
$ pyrevit youtube   # pyRevit YouTube channel
$ pyrevit support   # pyRevit suppport page for pyRevit patrons
```

With most commands you can log the complete results to a log file using the `--log=` option

```powershell
$ pyrevit clones update --all --log="C:\logfile.txt"
```

## Pages in this section

- [Clones](clones.md)
- [Attach to Revit](attach.md)
- [Configure](configure.md)
- [Extensions](extensions.md)
- [Environment info](environment.md)
- [Caches](caches.md)
- [Run scripts on models](run.md)
- [Revit installs and file info](revits.md)
- [Releases](releases.md)
- [Doctor, launch and update](doctor-launch-update.md)
- [Command reference](reference.md)
