**Want to see how pyRevit is built?**

Congratulations! This is where you start :D

pyRevit is an IronPython module, and lives in `pyrevitlib/pyrevit` folder.
Here is a quick introduction on how this module is setup and the role of its sub-modules. For more information, open
the entry file in each sub-module (python file mentioned here) and read the documentation in the file. All modules,
classes, methods, properties, functions, etc are heavily documented.


#### `pyrevit/__init__.py`

This is pyRevit module entry point. It has the most basic configuration for all sub-modules to use. It also contains
 the custom exceptions, parameters defined by the IronPython engine, and also contains the version information.

Examples:

``` python
from pyrevit import PyRevitException
from pyrevit import HOSTAPP, EXECPARAMS, USER_ROAMING_DIR
```


#### `pyrevit/coreutils`

`coreutils` contains the most generic tools that are shared between all sub-modules. For example the logging system is
under coreutils, and same as the libgit library. All other sub-modules use these components to do their job and
sometimes inherit to make more custom components. As an example, `user_config.py` sub-module, inherits
the `coreutils.configparser` sub-module to build a more custom user configuration handler.

Examples:

``` python
from pyrevit.coreutils import verify_directory
from pyrevit.coreutils import get_revit_instance_count

from pyrevit.coreutils.logger import get_logger

from pyrevit.coreutils import git
from pyrevit.coreutils import dotnetcompiler
from pyrevit.coreutils.ribbon import get_current_ui

```

#### `pyrevit/extensions`

The sole purpose of this module is to handle parsing and caching of extension folders. This module will provide
information about the active extensions to other modules. The `pyrevit.loader` module will receive the extension
list from `pyrevit.extensions` and will create assemblies for them.

Entry point: `extensionmgr.py`

``` python
from pyrevit.extensions.extensionmgr import get_installed_ui_extensions
```


#### `pyrevit/loader`

The heart of pyrevit really lives in this sub-module. It has 3 critical components:

- The `pyrevit.loader.sessionmgr` module receives the extension list from `pyrevit.extensions` and will create assemblies for them.
It uses `.asmmaker` and `.uimaker` to create assemblies and user interface for each extension.
- The `bin` and `bin\engines` directory which includes all the Revit addin dlls and also the `PyRevitLoader.dll` that is responsible
 for loading pyRevit.
- and the `pyrevit.loader.basetypes`. This is a complex module. Its job is to compile the command executor csharp files
 into an assembly at runtime so other commands can inherit these base types.

Entry point: `sessionmgr.py`

``` python
from pyrevit.loader.sessionmgr import load_session
load_session()
```

#### `pyrevit/versionmgr`

This module is responsible for providing version information (on the pyRevit git repo) to other modules and also
includes the `pyrevit.versionmgr.updater` that keeps the pyrevit git repo and all other extension packages repos up
 to date.

#### `pyrevit/plugins`

This module handles the addition/removal of pyrevit plugins. Extension packages are one kind of pyrevit plugins that
are handled by the `pyrevit.plugins.extpackages` sub-module.

#### `pyrevit/userconfig.py`

This module handles the configurations set by the user. pyrevit sub-modules use this module to check for their
user customizable properties.

``` python
from pyrevit.userconfig import user_config
```
