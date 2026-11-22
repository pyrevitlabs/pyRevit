# Configure

Use `config` command to configure pyRevit on your machine from an existing template configuration file:

```powershell
pyrevit config --from=<template_config_path> [--log=<log_file>]
$ pyrevit config --from="C:\myPyRevitTemplateConfig.ini"
```

To see all configuration options, run the `pyrevit configs --help` command

#### Configuring Sensitive Tools

You can Enable/Disable a few tools in pyRevit configurations:

```powershell
pyrevit configs usercanupdate [(yes | no)] [--log=<log_file>]
pyrevit configs usercanextend [(yes | no)] [--log=<log_file>]
pyrevit configs usercanconfig [(yes | no)] [--log=<log_file>]
```

- `usercanupdate`: Enable/Disable Update tool in pyRevit main tools
- `usercanextend`: Enable/Disable Extensions tool in pyRevit main tools
- `usercanconfig`: Enable/Disable Settings tool in pyRevit main tools

#### Configuring Your Own Options

Use the `configs` command to configure your custom config options. Specify the option in `section:option` format:

```powershell
pyrevit configs <option_path> (enable | disable) [--log=<log_file>]
pyrevit configs <option_path> [<option_value>] [--log=<log_file>]

$ pyrevit configs mysection:myswitch enable      # set myswitch to True
$ pyrevit configs mysection:myvalue 12           # set myvalue to 12
```

#### Using Config as Seed

Seed the configuration to `%PROGRAMDATA%/pyRevit` to be used as basis for pyRevit configurtions when configuring pyRevit using System account on a user machine

```powershell
pyrevit configs seed [--lock] [--log=<log_file>]
$ pyrevit configs seed
```

- `--lock`: Sets the read-only attribute on the seeded file, which locks the configuration for every user of the machine. See [Configuration file](../teams/configuration-file.md).

#### Resetting Settings

Return settings to their defaults without touching the installation. Reset removes the stored values, so every setting falls back to the default declared in pyRevit itself.

```powershell
pyrevit configs reset [<section>] [--dryrun] [--log=<log_file>]
$ pyrevit configs reset --dryrun
$ pyrevit configs reset core
```

- `<section>`: Resets only that section of the config file, for example `core`, `routes` or `telemetry`. For these, only the settings pyRevit defines are removed; bookkeeping such as the config version stays. Any other section, such as an extension's, is removed whole. Without a section, every section is reset except `environment`, which holds the registered clones and extension sources and is never reset. Shipped extensions that are off by default are switched off again afterwards.
- `--dryrun`: Lists what would be reset and changes nothing.

Before changing anything, `reset` copies the config file to `pyRevit_config.reset.<timestamp>.ini` in your Documents folder. If a seeded config exists in `%PROGRAMDATA%/pyRevit`, it is only copied when the user config is first created, so a reset does not bring it back.
