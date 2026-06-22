# Repository organization
The pyRevit repository is organized in the following folders:

- **bin** contains the binaries (dll and other support files) for pyRevit; usually a source repository doesn't have these, but it was made like this to be able to switch pyRevit versions using clones. This may change in the future and we could get rid of most content of this folder. Note that in this folder there also are the python environments (for example the CPython dlls and core packages).
- **dev** is where the C# code resides.
- **docs** is for the automatic generation of the documentation website.
- **extensions** holds the various pyRevit extensions; the pyRevitCore.extension is the one that builds the pyRevit ribbon tab, the others can be enabled via the Extension button inside pyRevit itself. pyRevitDevTools is quite handy to run tests and check if pyRevit (and the modifications you'll do) is running fine.
- **extras** are… extra files that can come in handy (icons and the dark mode generator are there to this date).
- **licenses** contains all the licenses of the included third party projects.
- **pyrevitlib** contains pyRevit and other related project's python libraries. It is usually the library that gets imported in the user scripts to ease the Revit API development.
- **release** contains static assets needed to build the final product (pyRevit and pyRevit CLI installers).
- **site-packages** is the collection of third-party python packages that are made available by pyRevit to the user. Given that the main python engine is IronPython 2.7.12, packages in that folder need to be compatible with it.
- **static** are assets for the website, YouTube channels and so on; you can ignore it.

# Understanding pyRevit Architecture
This guide provides an overview of pyRevit's architecture to help new contributors understand how the software works. Whether you want to create tools, troubleshoot issues, or contribute code, understanding these components will help you navigate the project.

## Components of pyRevit

### 1. pyRevit Add-In (pyRevitLoader)
A small C# plugin that starts pyRevit inside Revit when Revit itself starts up.

### 2. pyRevit Python Libraries (pyrevitlib)
Python packages that simplify working with the Revit API. They provide abstractions for creating ribbon buttons, running scripts, and interacting with Revit data.

### 3. Extensions
These are the tools and features users see inside Revit. They are mostly written in Python, but can also be C#/VB.NET scripts, Dynamo projects, and so on. Bundled extensions appear in the "pyRevit" tab, offering many tools. Users can add extensions by:
- Enabling listed extensions via the "Extensions" button in pyRevit.
- Creating custom extensions and adding their paths to the configuration.

### 4. pyRevit Command-Line Interface (CLI)
A tool for managing configurations, running scripts in bulk, and troubleshooting. Useful for corporate setups and advanced users.

### 5. Telemetry Server
A small server that tracks usage data of pyRevit tools and stores it for business intelligence purposes.

---

## How pyRevit Loads in Revit

When Revit starts, it reads the `.addin` manifest installed by pyRevit's installer, which tells Revit to load the pyRevit add-in. The add-in then initializes the Python environment and runs the pyRevit startup script, which is responsible for:

- Setting up the environment and logging.
- Checking for updates, if enabled.
- Discovering extensions and building the ribbon UI.
- Activating hooks for event-driven scripts.
- Initializing API routes and telemetry, if enabled.

### .addin Manifest
The installer places a `.addin` manifest file in the Revit Addins folder, instructing Revit to load pyRevit on startup. Depending on the installation type, this folder is either:
- `C:\ProgramData\Autodesk\Revit\Addins` (all users)
- `%APPDATA%\Autodesk\Revit\Addins` (current user only)

### pyRevitLoader.dll
The loader dll is the C# entry point for pyRevit inside Revit. There are multiple versions to support:
- Different Revit versions: one for Revit 2025 and newer, another for older versions.
- Different IronPython versions: 2.7.12 (default) and 3.4.0 (available but not fully tested).

> Since only one IronPython engine can be active at a time, pyRevit updates the `.addin` manifest to point to the correct loader when the user switches engines. If installation issues arise, running `pyrevit attach` usually resolves them by regenerating the manifest correctly.

### Extension Discovery
pyRevit scans known paths and user-defined folders to find installed extensions. For each extension, it generates the necessary UI elements such as ribbon tabs, panels, and buttons.

---

## How pyRevit Commands Run

Each ribbon button is backed by a command that handles:
- Detecting any modifier keys held at click time and adjusting behavior accordingly.
- Running the appropriate script (Python, C#, Dynamo, etc.) based on the button's configuration.

The appropriate script engine is selected automatically based on the script type.

---

# Commenting guidelines

When writing or suggesting code comments, document **what** the code does and **why**, never **how**.

Implementation details are already visible in the code itself. Restating them in a comment adds noise and creates drift: when the implementation changes, comments that describe it become misleading if not updated at the same time.

**Avoid comments that:**
- Restate what the next line of code literally does (`# increment counter`, `# call the loader`, `# return the list`).
- Name specific internal functions, classes, or modules that the code depends on.
- Describe the sequence of steps the implementation follows.
- Reference implementation choices that could change (e.g. which engine, which data structure, which library).

**Prefer comments that:**
- Explain the purpose or intent of a block (`# ensure the session is clean before loading extensions`).
- Capture non-obvious **why** reasoning that cannot be inferred from the code (`# Revit does not allow re-entrant API calls during this event`).
- Warn about known constraints or side effects that a future editor needs to be aware of.
- Describe what a function or class is responsible for, not how it achieves it.

**Example — what to avoid:**
```python
# Call get_ext_root_dirs to retrieve the list of extension paths from user config,
# then pass each path to extensionmgr to scan for UI extension manifests.
extensions = get_all_extensions()
```

**Example — what to write instead:**
```python
# Collect all installed extensions visible to the current user before building the UI.
extensions = get_all_extensions()
```

The same rule applies to docstrings, inline comments, and any documentation generated alongside code.
