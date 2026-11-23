# Startup script

!!! tip ""

    See [Extension Bundles](structure.md) for informatiom about the bundle requirements

UI Extension Bundles can define a startup script in their root directory. This script gets executed once when pyRevit is first starting and on every reload. You can use these scripts to set up your development or user environment. The current implementation supports IronPython, CPython, C#, and VB.Net scripts.

!!! warning ""

    For setting up your own event handlers, its suggested to use [Extension Hooks/](hooks.md)  

Here is an example script that sets up an event handler.

```python
from pyrevit import HOST_APP, framework
from pyrevit import DB
from pyrevit import forms

# define event handler
def docopen_eventhandler(sender, args):
    forms.alert('Document Opened: {}'.format(args.PathName))

# add the event handler function
HOST_APP.app.DocumentOpening += \
    framework.EventHandler[DB.Events.DocumentOpeningEventArgs](
        docopen_eventhandler
        )
```

!!! tip ""

    Start with the short introduction to scripts at [Create Your First Command](../tutorials/first-command.md)  

!!! tip ""

    Under current implementation, startup scripts are identical to Python or .NET scripts

See the pages below on startup scripts location and naming convention

- [Extension Bundles](structure.md)

See the pages below on information about the Python and .Net scripts.

- [Anatomy of IronPython Scripts](../scripting/ironpython.md)
- [Anatomy of CPython Scripts](../scripting/cpython.md)
- [Anatomy of .NET (C#, VB) Scripts](../scripting/dotnet.md)
