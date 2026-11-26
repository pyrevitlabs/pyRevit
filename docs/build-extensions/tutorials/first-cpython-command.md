# Your first CPython command

!!! note "CPython or IronPython"

    IronPython 2.7.12 is the default engine and the one pyRevit itself loads with. Use CPython when a script needs a C-based package such as `numpy` or `pandas`, or Python 3 syntax.

    The CPython engine runs Python 3.12.3 through pythonnet. `pyrevit.forms` works on both engines; the forms that are not ported raise `PyRevitCPythonNotSupported`. See [Forms across Python engines](../../architecture.md#forms-across-python-engines) for the list.

!!! warning ""

    Take a look at the [Create Your First Command](first-command.md)  for information about setting up your first extension. This article explains how to create a Cpython script in pyRevit. The rest is the same.

!!! tip ""

    pyRevit uses the embedded CPython engine. This engine looks at the PYTHONPATH environment variable for search paths for modules. You can set this variable on your system and pyRevit CPython commands will also find the modules you have installed using python package managers e.g. `pip` or `pipenv`. Install them with the same Python version as the pyRevit CPython engine, see [Engines](../../runtime/engines.md).

!!! warning ""

    Revit is a 64-bit application. Packages with compiled code must be the 64-bit builds.

### Writing The Script

pyRevit CPython scripts are almost identical to IronPython. The benefit is that you can import the CPython modules that are written in C language and therefore are not compatible with IronPython e.g. `numpy` and `scipy`

To create a CPython script, create a python script as described at [Create Your First Command](first-command.md)  and start the first line with the CPython identifier

```python
#! python3
```

The rest is business as usual.

```python
#! python3
import numpy as np
import pandas as pd

from pyrevit import revit, script

output = script.get_output()

print("\n## numpy array:")
print(repr(np.arange(15).reshape(3, 5)))

df_dict = {'key 1': 1, 'key 2': 2, 'key 3': 3}
df = pd.DataFrame([df_dict])

print("\n## pandas DataFrame:")
output.print_html(df.to_html().replace('\n', ''))

for element in revit.get_selection():
    print(element)
```

!!! tip ""

    See [Anatomy of CPython Scripts](../scripting/cpython.md)  
