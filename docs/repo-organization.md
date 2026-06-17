# Repository organization

The pyRevit repository is organized in the following folders:

- `bin` is **not tracked in git**. It holds runtime binaries (DLLs, engines, CLI, CPython under `cengines/`, etc.) produced locally by `dotnet run -- ci` in [`build/`](../build/) or downloaded by `pyrevit clone` / `pyrevit clones update` from public CI Release assets. See [Clone workflows](dev-guide.md#clone-workflows) for the two supported setups. Static sources live under [`release/bin-assets/`](../release/bin-assets/), [`release/cengines/`](../release/cengines/), and [`release/pyrevit-hosts.json`](../release/pyrevit-hosts.json).
- `dev` is where the c# code resides.
- `docs` is for the automatic generation of the [documentation website](https://docs.pyrevitlabs.io/)
- `extensions` holds the various pyRevit extensions; the pyRevitCore.extension is the one that build the `pyRevit` ribbon tab, the others can be enabled via the Extension button inside pyRevit itself. `pyRevitDevTools` is quite handy to run tests and check if pyRevit (and the modifications you'll do) is running fine.
- `extras` are… extra files that can come in handy (icons and the dark mode generator are there to this date).
- `licenses` contains all the licenses of the included third party projects.
- `pyrevitlib` contains pyRevit and other related project's python libraries. It is usually the library that gets imported in the user scripts to ease the Revit API development.
- `release` contains static assets needed to build the final product (pyrevit and pyrevit cli installers).
- `site-packages` is the collection of third-party python packaces that are made available by pyRevit to the user. Given that the main python engine is IronPython 2.7.12, packages in that folder needs to be compatible with it.
- `static` are assets for the website, youtube channels and so on, you can ignore it.
