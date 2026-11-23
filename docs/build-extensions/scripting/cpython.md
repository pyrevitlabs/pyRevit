# CPython scripts

!!! note "CPython or IronPython"

    IronPython 2.7.12 is the default engine and the one pyRevit itself loads with. Use CPython when a script needs a C-based package such as `numpy` or `pandas`, or Python 3 syntax.

    The CPython engine runs Python 3.12.3 through pythonnet. `pyrevit.forms` works on both engines; the forms that are not ported raise `PyRevitCPythonNotSupported`. See [Forms across Python engines](../../architecture.md#forms-across-python-engines) for the list.

!!! tip ""

    Start with the short introduction to scripts at [Create Your First Command](../tutorials/first-command.md)  and [Create Your First CPython Command](../tutorials/first-cpython-command.md)  

!!! tip ""

    See [Python Script Facilities](script-facilities.md) for information about the script support module

## Language Safe Code

CPython scripts are always read using UTF-8 encoding. There is no need to provide the `# -*- coding: utf-8 -*-` directive

## Shipped Packages

[Packages listed here](https://github.com/pyrevitlabs/pyRevit/tree/develop/site-packages) are shipped with pyRevit by default for convenience

## Implement Revit API's .NET Interfaces with CPython and pythonnet

**RE**  [https://github.com/pyrevitlabs/pyRevit/issues/686](https://github.com/pyrevitlabs/pyRevit/issues/686)

If you want to use CPython and pythonnet to implement any Revit API's .NET interface (for example: `Autodesk.Revit.DB.ISelectionFilter` in order to use with `Autodesk.Revit.UI.Selection.PickObject`), you must specify `__namespace__` attribute on the derived class

Additionally, your `__namespace__` must be different each time you run your script, otherwise you will get an exception as shown below  
Source [Implement a C# Interface in Python for .NET](https://stackoverflow.com/a/50462691)

```text
CPython Traceback:
TypeError : Duplicate type name within an assembly.
```

 You can use the pyRevit execution id for this purpose since it is unique for every execution.

```python
from pyrevit import EXEC_PARAMS

class CategoriesFilter(Selection.ISelectionFilter):
    __namespace__ = EXEC_PARAMS.exec_id

    def __init__(self, names):
        self.names = names

    def AllowElement(self, element):
        return element.Category.Name in self.names

    def AllowReference(self, refer, point):
        return False
```

## Differences from IronPython

- **One interpreter per Revit session.** The interpreter starts with the first CPython command and stays up until Revit closes. Reloading pyRevit does not restart it, so modules already in `sys.modules` survive a reload, also with `engine: clean`.
- **No named indexers.** pythonnet does not support `element.Parameter[...]` or `element.Geometry[options]`. Call `element.get_Parameter(...)` and `element.get_Geometry(options)`.
- **Interface-typed values.** A property typed as an interface returns the interface, not the concrete class. Read the object's `__implementation__` attribute to get the concrete object.
- **Module search paths.** The engine adds every folder in the `PYTHONPATH` environment variable to `sys.path`.
