# Repository organization

The pyRevit repository is organized in the following folders:

- `bin` is **not tracked in git**. It holds runtime binaries (DLLs, engines, CLI, CPython under `cengines/`, etc.) produced locally by `dotnet run -- ci` in [`build/`](../build/) or downloaded by `pyrevit clone` / `pyrevit clones update` from public CI Release assets. See [Clone workflows](dev-guide.md#clone-workflows) for the two supported setups. Static sources live under [`release/bin-assets/`](../release/bin-assets/), [`release/cengines/`](../release/cengines/), and [`release/pyrevit-hosts.json`](../release/pyrevit-hosts.json).
- `build` is the C# ModularPipelines project that builds, tests, stamps, signs and publishes the product, plus its own unit tests in `build/tests/`. See [`build/README.md`](https://github.com/pyrevitlabs/pyRevit/blob/develop/build/README.md) and [CI/CD](ci-cd.md).
- `dev` is where the C# code resides. `dev/scripts` holds the repository's Python tooling and its host-free CPython test suites: `test_<script>.py` covers a script in that folder and runs through a `pipenv run test-*` entry, while `test_standalone_*.py` covers a `pyrevitlib` module without a Revit host and is what CI runs (see [CI/CD](ci-cd.md#ciyml-triggers-and-path-filter)).
- `docs` holds the sources of the [documentation website](https://docs.pyrevitlabs.io/), built with mkdocs. `docs/gen_ref_pages.py` generates the reference API from the `pyrevitlib/pyrevit` docstrings and copies the `*.md` files of the repository root into the site. `docs/static` and `docs/images` hold the website assets.
- `extensions` holds the pyRevit extensions and the `extensions.json` catalog. `pyRevitCore.extension` builds the `pyRevit` ribbon tab. `pyRevitTools`, `pyRevitTags`, `pyRevitTutor`, `pyRevitTemplates` and `pyRevitBundlesCreatorExtension` ship tools that can be enabled from the Extensions button inside pyRevit. `pyRevitDevTools` and `pyRevitDevHooks` are for contributors: DevTools runs tests and checks that pyRevit, and your modifications, work in a live Revit; DevHooks logs hook events.
- `extras` holds auxiliary files: icon sources (`adskicons`), the dark mode generator (`dark_mode`), bundle translation scripts, and an Advanced Installer project for Revit shortcuts.
- `licenses` contains the licenses of the included third party projects.
- `pyrevitlib` contains pyRevit's Python libraries and related projects'. It is the library user scripts import to ease Revit API development.
- `release` contains the static assets and installer scripts needed to build the final products (the pyRevit and pyRevit CLI installers).
- `site-packages` is the collection of third-party Python packages that pyRevit makes available to scripts. The default engine is IronPython 2.7.12, so the packages must be compatible with it.
- `.github` holds the GitHub Actions workflows, issue and pull request templates, and the agent skills under `.github/skills`.
