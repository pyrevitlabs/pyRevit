# Environment info

Use the `env` command to get a report about the current pyRevit environment. It is the first thing to attach to a bug report.

```powershell
pyrevit env [--json] [--redact] [--log=<log_file>]
```

The report has one block per topic. Values between `<` and `>` below stand for your own.

#### Registered Clones

The registered clones, full git repositories and deployed copies separately. `dev` and `main` are the clone names in this example.

```text
==> Registered Clones (full git repos)
dev | Branch: "develop" | Version: "<version>" | Path: "C:\pyRevit\dev"

==> Registered Clones (deployed from archive/image)
main | Deploy: "base" | Branch: "master" | Version: "<version>" | Path: "C:\pyRevit\main"
```

#### Attachments

Which clone and engine each installed Revit loads.

```text
==> Attachments
dev | Product: "<Revit product name>" | Engine: IPY2712PR (2712) | Path: "C:\pyRevit\dev"
```

#### Extensions

The installed extensions, the search paths and the lookup sources.

```text
==> Installed Extensions

==> Default Extension Search Path
C:\Users\<user>\AppData\Roaming\pyRevit\Extensions

==> Extension Search Paths

==> Extension Sources - Default
https://github.com/pyrevitlabs/pyRevit/raw/master/extensions/extensions.json

==> Extension Sources - Additional
```

#### Installed Revit

The installed Revit versions and the running Revit instances.

```text
==> Installed Revits
<Revit product name> | Version: <version> | Build: <build>(<target>) | Language: <language code> | Path: "C:\Program Files\Autodesk\Revit <year>"

==> Running Revit Instances
```

#### User Environment

The Windows version, the user, the install scope and configuration file in use, and the installed .NET versions.

```text
==> User Environment
<Windows version>
Executing User: <domain>\<user>
Active User: <domain>\<user>
Admin Access: No
Install Scope: PerUser
Active Config: "<path of pyRevit_config.ini>"
%APPDATA%: "C:\Users\<user>\AppData\Roaming"
Latest Installed .Net Framework: <version>
Installed .Net Target Packs: <versions>
Installed .Net-Core Target Packs: <versions>
Active CPython Engine Version: <engine id>
pyRevit CLI v<version>
```

## Environment data as JSON

```powershell
pyrevit env --json
```

prints the same information as JSON, with these top-level keys: `meta`, `clones`, `attachments`, `extensions`, `searchPaths`, `lookupSources`, `installed`, `running`, `pyrevitDataDir`, `activeCpythonEngineVersion` and `userEnv`.

## Sharing the report

The report contains your user name and local paths. Add `--redact` to mask user names, user profile folders, server names and Git URLs before you post the report in an issue. The masking is best effort: it cannot know that a folder name or a repository path is confidential, so read the result before you share it:

```powershell
pyrevit env --redact
pyrevit env --json --redact
```

## The PATH entry of the CLI

`pyrevit env path` inspects and repairs the `PATH` entry that makes the `pyrevit` command available:

```powershell
pyrevit env path list [--scope=<scope>]             # list the PATH entries
pyrevit env path which                              # show which pyrevit the command prompt runs
pyrevit env path ensure <dir> [--scope=<scope>] [--first]
pyrevit env path remove <dir> [--scope=<scope>]
```

`--scope` is `user` (the default) or `machine`. `--first` makes `<dir>` the first entry of that `PATH`.
