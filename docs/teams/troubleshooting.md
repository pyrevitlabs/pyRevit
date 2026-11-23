# Troubleshoot a deployment

Start with these checks on a machine where pyRevit does not load:

```powershell
pyrevit env          # clones, attachments, extensions and installed Revit versions
pyrevit attached     # which clone and engine each Revit version loads
pyrevit clones       # registered clones
```

- **No attachment listed**: attach the clone again with `pyrevit attach <clone_name> default --installed`, adding `--allusers` when the deployment is for every user of the machine. See [Attach to Revit](../cli/attach.md).
- **Clone not registered**: register it with `pyrevit clones add <clone_name> <clone_path>`. See [Clones](../cli/clones.md).
- **Installed with the admin installer**: run the CLI from a command prompt started as administrator.
- **Leftovers from an older installation**: remove them with [`pyrevit doctor`](../cli/doctor-launch-update.md).

[Installation issues](../help/installation-issues.md) covers the problems that are not specific to a team deployment, such as security software blocking the loader.
