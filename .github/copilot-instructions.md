# Repository organization
The pyRevit repository is organized in the following folders:

- bin contains the binaries (dll and other support files) for pyRevit; usually a source repository doesn't have these, but it was made like this to be able to switch pyRevit versions using clones. This may change in the future and we could get rid of most content of this folder. Note that in this folder there also are the python envrionments (for example the CPython dlls and core packages).
- dev is where the c# code resides.
- docs is for the automatic generation of the documentation website
- extensions holds the various pyRevit extensions; the pyRevitCore.extension is the one that build the pyRevit ribbon tab, the others can be enabled via the Extension button inside pyRevit itself. pyRevitDevTools is quite handy to run tests and check if pyRevit (and the modifications you'll do) is running fine.
- extras are… extra files that can come in handy (icons and the dark mode generator are there to this date).
- licenses contains all the licenses of the included third party projects.
- pyrevitlib contains pyRevit and other related project's python libraries. It is usually the library that gets imported in the user scripts to ease the Revit API development.
- release contains static assets needed to build the final product (pyrevit and pyrevit cli installers).
- site-packages is the collection of third-party python packaces that are made available by pyRevit to the user. Given that the main python engine is IronPython 2.7.12, packages in that folder needs to be compatible with it.
- static are assets for the website, youtube channels and so on, you can ignore it.

# Understanding pyRevit Architecture
This guide provides an overview of pyRevit’s architecture to help new contributors understand how the software works.
Whether you want to create tools, troubleshoot issues, or contribute code, understanding these components will help you navigate the project.
Components of pyRevit
1. pyRevit Add-In (pyRevitLoader)
    ◦ A small piece of C# code that starts pyRevit inside Revit.
    ◦ It loads a Python script using the IronPython engine, which handles the rest of pyRevit’s functionality.
2. pyRevit python Libraries (pyrevitlibs)
    ◦ Python packages that simplify working with the .NET Revit API.
    ◦ Provide tools to create ribbon buttons, run scripts, and more.
3. Extensions
    ◦ These are the tools and features users see inside Revit.
    ◦ They are mostly written in python, but can also be C#/VB.NET scripts, dynamo projects, and so on
    ◦ Bundled extensions appear in the "pyRevit" tab, offering many tools.
    ◦ Users can add extensions by:
        ▪ Enabling listed extensions in dev/extensions/extensions.json via the “Extensions” button in pyRevit.
        ▪ Creating custom extensions and adding their paths to the configuration.
4. pyRevit Command-Line Interface (CLI)
    ◦ A tool for managing configurations, running scripts in bulk, and troubleshooting.
    ◦ Useful for corporate setups and advanced users.
5. Telemetry Server
    ◦ A small server (written in Go) that tracks usage data of pyRevit tools.
    ◦ Stores data in MongoDB or PostgreSQL for business intelligence.
How pyRevit Loads in Revit
TL;DR:
• Revit reads the .addin manifest in the Addins folders
• The .addin manifest points to pyRevitLoader.dll
• pyRevitLoader.dll launches pyrevitloader.py inside an IronPython environment
• pyrevitloader.py calls functions from the pyrevit python package to build the UI and the buttons commands.
.addin Manifest
• The installer creates a file with .addin extension, called manifest, in the Revit Addins folder, instructing Revit to load pyRevit when it starts.
• The Addins folder can be located in one of these paths, depending on pyRevit installation:
    ◦ C:\ProgramData\Autodesk\Revit\Addins (for all users)
    ◦ %APPDATA%\Autodesk\Revit\Addins (for the current user only)
• The manifest points to pyRevitLoader.dll, which acts as the entry point for pyRevit.
pyRevitLoader.dll
The pyRevitLoader.dll file is a small C# program that:
• Ensures required .NET assemblies are loaded.
• Loads the IronPython engine and runs pyRevit’s Python startup script (pyrevitloader.py).Info
the source code is in PyRevitLoaderApplication.cs and it is an implementation of the Revit API IExternalApplication interface (the standard way to create a plugin for Revit).
There are multiple versions of pyRevitLoader.dll to support:
• different Revit versions:
    ◦ One for Revit 2025 and newer, built with .NET 8.
    ◦ Another for older Revit versions, built with the .NET Framework.
• different IronPython versions; to this date:
    ◦ version 2.7.12, the default one
    ◦ version 3.4.0, more recent but not fully tested.
They share the same source code, but are compiled against the different .net runtimes and IronPython versions.
Note
Since we cannot have multiple IronPython engines running at the same time, if the user switches the engine in the configuration, pyRevit will change the .addin manifest mentioned above to point to the correct dll path. It may be that sometimes the addin is not created correctly or points to the wrong path, and this is why most of the times the pyrevit attach command solves the installation issues.
Startup Script: pyrevitloader.py
This Python script is the first code executed by pyRevit inside Revit. It:
• Sets up environment variables.
• Initializes the logging system and prepares the script console
• Checks for updates if enabled, pulling changes for pyRevit and extensions.
• Loads extensions and creates UI elements like ribbons and buttons (see below).
• Activates hooks, which enable features like event-driven scripts.
• Initializes API routes and Telemetry, if enabledInfo
pyrevitloader.py is a small script that just calls the pyrevit.loader.sessionmgr.load_session function. That function is responsible to do all the things mentioned above.
Extensions discovery
• pyRevit scans known paths and user defined folders to find extensions.
• For each extension, it builds a .net assembly to create buttons, tabs, and other UI elements.Info
Extensions directories are detected by pyrevit.userconfig.PyRevitConfig.get_ext_root_dirs. Extension components discovery is performed by pyrevit.extensions.extensionmgr.get_installed_ui_extensions. Assemblies are generated by pyrevit.loader.asmmaker with types from pyrevit.runtime.create_type.
How pyRevit Commands run
TL;DR:
Command execution is handled by the c# project pyRevitLabs.Pyrevit.Runtime
Each button generated by the Extension discovery is bound to a command derived by the ScriptCommand.cs source code.
This code deals with:
• detecting the modifier keys hold while clicking the button, and change the behavior accordingly
• calling ScriptExcecutor.ExcecuteScript passing the python script (or any other supportesd script) for the commandInfo
The ScriptCommand class implements Revit’s IExternalCommand interface. The Execute method is the one called when you click the Ribbon button.
In turn, the code in ScriptExecutor.cs calls the appropriate script engine based on the type of (IronPython, CPython, .NET, and so on).Info
You can find the code of the engines in the files that end Engine.cs. 
