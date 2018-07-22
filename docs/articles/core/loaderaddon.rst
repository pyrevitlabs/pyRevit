Load Sequence, Step 1: Revit Addon
==================================


The Complex Relationship of a C# Addin and a Python Script
**********************************************************

Let's talk basics:
    * Revit Addons are written in C# and are windows ``.dll`` files.
    * pyRevit is written as an IronPython module. (actually a bit more complex than that)
    * Revit doesn't have an option to run external python scripts.

Thus, we need a way to teach Revit how to run a python script when it's starting up.

The solution was to create a custom C# addin to create a python engine and run a script. We'll call this addin ``pyRevitLoader.dll``. I wanted to keep this addin as simple as possible since it's the only statically-compiled piece of code in this project. The rest of the task of loading pyRevit were assigned to a loader python script that is being run by the loader addin.

So:
    * ``pyRevitLoader.dll`` is a simple C# addin for Revit that runs python scripts
    * ``pyRevitLoader.dll`` loads ``pyRevitLoader.py`` at startup.
    * ``pyRevitLoader.py`` sets up the environment and loads pyRevit.


It's that simple really. See the sources below.

From here on, the documentation page for the `pyrevit.loader` module will take you through all the steps of parsing extensions, making dll assemblies and creating the user interface for the parsed extensions.


pyRevit loader script
*****************************

Here is the full source of ``pyRevitLoader.py``. The docstring explains how it works.

.. literalinclude:: ../../../pyrevitlib/pyrevit/loader/addin/pyRevitLoader.py


pyRevitLoader Addin Source
**********************************

The source code for pyRevitLoader addin is under:
``pyrevitlib/pyrevit/addin/<loader version>/Source``
