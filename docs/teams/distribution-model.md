# Distribution model

How pyRevit gets onto a machine depends on who installs it and for whom.

| Situation | Use | Installs to | Attached for |
|---|---|---|---|
| You install pyRevit for yourself, without admin rights | `pyRevit_<version>_signed.exe` | `%APPDATA%\pyRevit-Master` | the current user |
| You install pyRevit for every user of a machine | `pyRevit_<version>_admin_signed.exe` (needs admin rights) | `%PROGRAMFILES%\pyRevit-Master` | all users |
| You deploy pyRevit and your own extensions to a team | the [pyRevit CLI](../cli/index.md) in a script | a path you choose | all users, with `--allusers` |

- For a single machine, see [Install pyRevit](../get-started/install.md) and [Installers](../installers.md).
- For a team, see the [Team deployment guide](deployment-guide.md). It installs the CLI, clones pyRevit and your extensions, writes a seed configuration and attaches pyRevit to the installed Revit versions.
- [Deployments](deployments.md) lists the named subsets of pyRevit you can clone, for example the core without the default tools.
