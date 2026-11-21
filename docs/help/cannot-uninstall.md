# Cannot uninstall

When the uninstaller fails, or a new version refuses to install because it still sees an old one, remove the leftovers with the doctor tool.

Close Revit, then run:

```powershell
pyrevit doctor purge-installs --dryrun     # report the old installation records
pyrevit doctor purge-installs              # remove them from the registry
```

`pyrevit doctor purge-all` also deletes the install and data folders, the Revit add-in manifests and the PATH entries. It backs up `pyRevit_config.ini` and the Extensions folder to Documents first.

If the `pyrevit` command itself does not work, download `pyrevit-doctor.exe` from the [releases page](https://github.com/pyrevitlabs/pyRevit/releases) and run it with the same commands. It needs the .NET 8 runtime or newer.

See [Doctor, launch and update](../cli/doctor-launch-update.md) for every command and option.
