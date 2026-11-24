# Extension structure

!!! tip ""

    Start with the short introduction to extension bundles at [Create Your First Command](../tutorials/first-command.md)   
    This document provides detailed information about Extension bundles and their functionality

## UI Extension Bundle

UI extension bundles are a set of tools grouped to be easily accessible through the user interface.

See  [Extension Metadata](metadata.md) for more information about UI Extension metadata files

See [Extension Startup Script](startup-script.md)  for more information about UI Extension startup scripts

See [Bundle Lib & bin](../bundles/lib-and-bin.md)  for more info on the bundle `lib/` and `bin/` directories

See [Extension Hooks/](hooks.md) for more information about hook scripts inside `hooks/` directory

```yaml
extension: .extension
requires:
    - extension.json      # includes extension metadata e.g. author

optional:
    - *startup.*          # can include a startup script that runs when Revit is launched
    - bin/                # can include a bin/ directory that hosts binaries required by the child bundles
    - lib/                # can include a lib/ directory that hosts modules required by the child bundles
    - hooks/              # can include a hooks/ directory that hosts the hook scripts
```

## Other Extension Bundle Types

The extension bundle discussed above, is the most important type of extension bundles. There are however more extension types that are designed for specific purposes.

### Library Extensions

Library extensions are created to share IronPython modules between all extensions. They’re in essence IronPython module packages. Some users might decide to develop an IronPython library (e.g. [RevitPythonWrapper Library](https://revitpythonwrapper.readthedocs.io/)) that other users can use in their tools and benefit from.

```yaml
extension: .lib
requires:
    - bundle.yaml         # includes extension metadata e.g. author
```

### Run Extensions

Run extensions are designed to be used with the pyRevit CLI. See [Batch Process Revit Models](../../cli/run.md)  

```yaml
extension: .run
requires:
    - bundle.yaml         # includes extension metadata e.g. author
    - <name>_command.py   # one or more Run commands. <name> is name of the command.
                          # e.g. "make3dview" is the name of "make3dview_command.py"
                          # these named commands can be used with pyRevit CLI for batch processing models
```
