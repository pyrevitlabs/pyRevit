# Understanding pyRevit Architecture

This guide provides an overview of pyRevit’s architecture to help new contributors understand how the software works.

Whether you want to create tools, troubleshoot issues, or contribute code, understanding these components will help you navigate the project.

## Components of pyRevit

1. **pyRevit Add-In (pyRevitLoader)**
    - A small piece of C# code that starts pyRevit inside Revit.
    - It loads a Python script using the IronPython engine, which handles the rest of pyRevit’s functionality.

2. **pyRevit python Libraries (pyrevitlibs)**
    - Python packages that simplify working with the .NET Revit API.
    - Provide tools to create ribbon buttons, run scripts, and more.

3. **Extensions**
    - These are the tools and features users see inside Revit.
    - They are mostly written in python, but can also be C#/VB.NET scripts, dynamo projects, and so on
    - Bundled extensions appear in the "pyRevit" tab, offering many tools.
    - Users can add extensions by:
        - Enabling listed extensions in `dev/extensions/extensions.json` via the “Extensions” button in pyRevit.
        - Creating custom extensions and adding their paths to the configuration.

4. **pyRevit Command-Line Interface (CLI)**
    - A tool for managing configurations, running scripts in bulk, and troubleshooting.
    - Useful for corporate setups and advanced users.
    - The `pyrevit env` report includes the configured CPython engine version (`activeCpythonEngineVersion` in JSON).

5. **Telemetry Server**
    - A small server (written in Go) that tracks usage data of pyRevit tools.
    - Stores data in MongoDB or PostgreSQL for business intelligence.

## How pyRevit Loads in Revit

!!! tip "TL;DR:"

    - Revit reads the `.addin` manifest in the Addins folders
    - The `.addin` manifest points to `pyRevitLoader.dll`
    - `pyRevitLoader.dll` launches `pyrevitloader.py` inside an IronPython environment
    - `pyrevitloader.py` calls functions from the `pyrevit` python package to build the UI and the buttons commands.

### .addin Manifest

- The installer creates a file with `.addin` extension, called manifest, in the Revit Addins folder, instructing Revit to load pyRevit when it starts.
- The Addins folder can be located in one of these paths, depending on pyRevit installation:
    - `C:\ProgramData\Autodesk\Revit\Addins` (for all users)
    - `%APPDATA%\Autodesk\Revit\Addins` (for the current user only)
- The manifest points to `pyRevitLoader.dll`, which acts as the entry point for pyRevit.

### pyRevitLoader.dll

The `pyRevitLoader.dll` file is a small C# program that:

- Ensures required .NET assemblies are loaded.
- Loads the IronPython engine and runs pyRevit’s Python startup script (`pyrevitloader.py`).

???+ info

    the source code is in `PyRevitLoaderApplication.cs` and it is an implementation of the Revit API `IExternalApplication` _interface_ (the standard way to create a plugin for Revit).

There are multiple versions of `pyRevitLoader.dll` to support:

- different Revit versions:
    - One for Revit 2025 and newer, built with .NET 8.
    - Another for older Revit versions, built with the .NET Framework.
- different IronPython versions; to this date:
    - version 2.7.12, the default one
    - version 3.4.0, more recent but not fully tested.

They share the same source code, but are _compiled against_ the different .net runtimes and IronPython versions.

!!! note

    Since we cannot have multiple IronPython engines running at the same time, if the user switches the engine in the configuration, pyRevit will change the `.addin` manifest mentioned above to point to the correct dll path.
    It may be that sometimes the addin is not created correctly or points to the wrong path, and this is why most of the times the `pyrevit attach` command solves the installation issues.

### Startup Script: `pyrevitloader.py`

This Python script is the first code executed by pyRevit inside Revit. It:

- Sets up environment variables.
- Initializes the logging system and prepares the script console
- Checks for updates if enabled, pulling changes for pyRevit and extensions.
- Loads extensions and creates UI elements like ribbons and buttons (see [below](#extensions-discovery)).
- Activates hooks, which enable features like event-driven scripts.
- Initializes API routes and Telemetry, if enabled

???+ info

    `pyrevitloader.py` is a small script that just calls the [pyrevit.loader.sessionmgr.load_session][] function.
    That function is responsible to do all the things mentioned above.

### Extensions discovery

- pyRevit scans known paths and user defined folders to find extensions.
- For each extension, it builds a .net assembly to create buttons, tabs, and other UI elements.

???+ info

    Extensions directories are detected by [pyrevit.userconfig.PyRevitConfig.get_ext_root_dirs][].
    Extension components discovery is performed by [pyrevit.extensions.extensionmgr.get_installed_ui_extensions][].
    Assemblies are generated by [pyrevit.loader.asmmaker][] with types from [pyrevit.runtime.create_type][].

## How pyRevit Commands run

!!! tip "TL;DR:"

    Command execution is handled by the c# project `pyRevitLabs.Pyrevit.Runtime`

Each button generated by the [Extension discovery](#extensions-discovery) is bound to a command derived by the `ScriptCommand.cs` source code.

This code deals with:

- detecting the modifier keys hold while clicking the button, and change the behavior accordingly
- calling `ScriptExcecutor.ExcecuteScript` passing the python script (or any other supportesd script) for the command

???+ info

    The `ScriptCommand` class implements Revit’s `IExternalCommand` interface.
    The `Execute` method is the one called when you click the Ribbon button.

In turn, the code in `ScriptExecutor.cs` calls the appropriate script engine based on the type of (IronPython, CPython, .NET, and so on).

???+ info

    You can find the code of the engines in the files that end `Engine.cs`.
