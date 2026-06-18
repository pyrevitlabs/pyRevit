# pyRevit Developer's Guide

This guide is designed to help new contributors set up their development environment, get familiar with the codebase, and start contributing to the project.

!!! note

    This guide is for people that wants to get their hands dirty in the core pyRevit code, the part written in C#.

    It is not for the development of the python side.

## Requirements

Before you begin, you'll need to set up your development environment with the following tools:

### Visual Studio

Install Visual Studio 2022 and select:

- under **workloads**, enable **.NET desktop development**
- under ¨**Individual components** make sure the following are selected:
    - .NET 8.0 Runtime (Long Term Support)
    - .NET Framework 4.7.2 Targeting Pack
    - .NET Framework 4.8 SDK
    - .NET Framework 4.8 Targeting Pack
    - .NET 3.1 Runtime (MahApps.Metro)
    - NuGet package manager
    - MSBuild

### Python 3

Make sure Python 3 is installed on your system.

Download it from the [Python official website](https://www.python.org/downloads/).

### Pipenv

This tool manages Python environments and dependencies.

You can install Pipenv by running:

```shell
pip install pipenv
```

## Git Setup

To contribute to pyRevit, you'll need to set up your Git environment as follows:

### Fork the Repository

Go to the [pyrevitlabs/pyrevit](https://github.com/pyrevitlabs/pyrevit) GitHub page and click on the "Fork" button to create your own copy of the repository.

Make sure to uncheck the "Copy the master branch only" option, since we mostly use the develop branch to make changes.

### Clone workflows

`bin/` is **not in git**. Choose one workflow below. Only **`develop`** and **`master`** support CI binary download. Details on CI assets and fallbacks: [CI/CD — Prebuilt binaries for clone](ci-cd.md#prebuilt-binaries-for-clone).

| Profile | You want to… | Get source via | Get `bin/` via |
|---------|----------------|----------------|----------------|
| **1 — Run in Revit** | Use pyRevit without building C# | `pyrevit clone` | Public Release `ci-binaries` (no token on upstream when assets exist) |
| **2 — C# contributor** | Change DLLs and debug in Visual Studio | `git clone` | `dotnet run -- ci` in [`build/`](../build/) |

#### Profile 1 — Run in Revit (CI binaries)

Uses the pyRevit CLI to clone git source **and** download pre-built `bin/` from the [`ci-binaries`](https://github.com/pyrevitlabs/pyRevit/releases/tag/ci-binaries) release. Normal path on `pyrevitlabs/pyRevit` needs no `GITHUBTOKEN`. Synced forks use upstream Release assets for the same commit SHA.

```shell
pyrevit clone dev --source <repo-url> --dest <parent-directory> --branch develop
pyrevit attach dev default --installed
```

Refresh source and binaries later:

```shell
pyrevit clones update dev
```

If public Release download fails (diverged fork, private repo), set `GITHUBTOKEN` (`read:packages` and/or `actions:read`) and retry — the CLI falls back to the `PyRevit.UnsignedBin` NuGet mirror and Actions artifacts. See [download order](ci-cd.md#prebuilt-binaries-for-clone).

#### Profile 2 — C# contributor (local build)

Use **git**, not `pyrevit clone` — `clone` would pull CI binaries and overwrite the local-build workflow.

```shell
git clone <your-fork-url>
cd pyRevit
git checkout develop
git submodule update --init --recursive
git remote add upstream https://github.com/pyrevitlabs/pyrevit.git

cd build
dotnet run -c Release -- ci
cd ..

pyrevit clones add dev .
pyrevit attach dev default --installed
```

The `ci` pipeline seeds `bin/pyrevit-products.json` from tracked `release/` templates before building labs. No manual `bin/` setup or `Build__Channel` override is required for a first local build.

After pulling source changes, refresh **without** downloading CI binaries:

```shell
git pull
pyrevit clones update dev --skip-bin
cd build && dotnet run -c Release -- ci && cd ..
```

Rebuild in Debug when attaching the debugger (see [Debugging Code](#debugging-code)).

#### Build channel (maintainers)

Most contributors can use the default build channel (`none`) shown in Profile 2 above. **Repo admins and maintainers** who need to reproduce what CI does on the main repository — version stamping, copyright year, and product metadata in `bin/` — set `Build__Channel` before running `dotnet run -- ci`.

| Channel | When to use | Matches CI on |
|---------|-------------|---------------|
| `none` (default) | Local dev, fork PRs, unsigned builds | Fork PR validation; any build without stamping |
| `wip` | Testing a **develop**-style stamped build locally | Push to `develop` on `pyrevitlabs/pyRevit` |
| `release` | Testing a **master** / tag-style stamped build locally | Push to `master` or `v*` tag on `pyrevitlabs/pyRevit` |

Set the channel with the `Build__Channel` environment variable (maps to [`build/appsettings.json`](../build/appsettings.json) → `Build:Channel`). Run commands from `build/`.

**PowerShell:**

```powershell
cd build

# develop-style stamping (WIP version suffix, product metadata refresh)
$env:Build__Channel = 'wip'
dotnet run -c Release -- ci

# master / release-tag stamping
$env:Build__Channel = 'release'
$env:DOTNET_ENVIRONMENT = 'Production'
dotnet run -c Release -- ci

# back to unsigned (default)
Remove-Item Env:Build__Channel -ErrorAction SilentlyContinue
Remove-Item Env:DOTNET_ENVIRONMENT -ErrorAction SilentlyContinue
dotnet run -c Release -- ci
```

**cmd:**

```bat
cd build
set Build__Channel=wip
dotnet run -c Release -- ci
```

**bash:**

```bash
cd build
export Build__Channel=wip
dotnet run -c Release -- ci
```

!!! warning "Stamping modifies source files"

    `wip` and `release` update tracked files under `pyrevitlib/`, `release/`, and installer metadata — the same steps CI runs before building products. Review `git status` before committing; do not push accidental version bumps from a local stamped build.

On GitHub Actions, full stamping runs only when `Build__Channel` is `wip` or `release` **and** `GITHUB_REPOSITORY` is `pyrevitlabs/pyRevit`. Fork workflows always use `none` for stamping even if you set the variable in a custom workflow. Locally, `GITHUB_REPOSITORY` is usually unset, so setting `Build__Channel` is enough to mirror main-repo CI. See [CI/CD — Official repository vs forks](ci-cd.md#official-repository-vs-forks) and [`build/README.md`](../build/README.md).

### Set Upstream Remote

If you did not add upstream in Profile 2, add the original pyrevitlabs repository to keep your fork in sync:

```shell
git remote add upstream https://github.com/pyrevitlabs/pyrevit.git
```

You can choose any name for the remote, but "upstream" is a common convention.

### Retrieve the submodules

If you skipped Profile 2 step 4, or switch branches that change dependencies:

```shell
git submodule update --init --recursive
```

!!! note

    Repeat `git submodule update` when you switch branches or when `develop` updates submodule pointers.

## Initialize the pipenv environment

This will create a python environment for running the toolchain scripts to build the various pyrevit components.

```shell
pipenv install
```

## IDE Setup

You have a couple of options for setting up your development environment:

1. **Visual Studio Code**: You can open the entire pyRevit directory in Visual Studio Code. This setup works well for Python development, but may lack some C#/.NET language support.

   - Recommended extensions: C#, Python, and GitLens.

2. **Visual Studio**: For full C#/.NET support, it's better to open a specific solution file (`.sln`) in Visual Studio. This gives you access to language checks, autocompletion, and suggestions.

   - Open the solution that corresponds to the area of the project you're working on.

But you can of course use your IDE of choice, such as Rider for .NET and pyCharm for python.

## Revit Setup

Follow [Profile 1](#profile-1-run-in-revit-ci-binaries) or [Profile 2](#profile-2-c-contributor-local-build) under [Clone workflows](#clone-workflows) — each includes `pyrevit attach`.

Quick checks:

```shell
pyrevit clones info dev
pyrevit attachments
```

!!! note

    pyRevit 5 (current WIP) needs a WIP `pyrevit` CLI. Build it from this repo if needed:

    ```shell
    cd build
    dotnet run -c Release -- ci
    cd ..
    .\bin\pyrevit.exe attach dev default --installed
    ```

## Debugging Code

Currently, you cannot use Visual Studio's "Run" button to debug pyRevit because of some build issues. Instead, follow this approach:

1. **Build the Project**: Open a command prompt or PowerShell, navigate to your git directory, and build in Debug mode:

   ```shell
   cd build
   dotnet run -c Debug -- ci
   cd ..
   ```

2. **Open the Solution in Visual Studio**: Once the DLLs are built, open the `pyRevitLabs.PyRevit.Runtime` solution in Visual Studio.

3. **Attach the Debugger**: Attach the Visual Studio debugger to the `revit.exe` process to start debugging:
   - Go to `Debug` > `Attach to Process...` and select `revit.exe` from the list.

## Conclusion

You're now ready to start contributing to pyRevit! Whether you're fixing bugs, adding new features, or improving documentation, your contributions are valuable. If you have any questions, feel free to reach out to the community through GitHub or other communication channels.

Happy coding!
