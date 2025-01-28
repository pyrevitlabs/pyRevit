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

### Clone Your Fork

if you already have a copy of pyRevit or pyRevit CLI installed, you can use the command

```shell
pyrevit clone <name-of-your-choice> --source <url-of-you-repo> --dest <destination-directory> --branch develop
```

As an example, I choose to call the clone "dev" and put it in "C:\pyrevit", so my command becomes

```shell
pyrevit clone dev --source https:/gitlab.com/sanzoghenzo/pyrevit.git --dest c:\pyrevit --branch=develop
```

!!! note

    I will use the `dev` name in the following steps, make sure to replace it with the name of your choice.

If you don't have pyrevit cli installed, or prefer to do things in the canonical way, follow these steps:

1. **Clone Your Fork**: Clone your forked repository to your local machine:

    ```shell
    git clone <your-fork-url>
    ```

2. **Enter pyRevit folder**:

    ```shell
    cd pyrevit
    ```

3. **Checkout the Develop Branch**: This is where active development happens, so make sure you're working on this branch:

    ```shell
    git checkout develop
    ```

### Set Upstream Remote

Add the original pyrevitlabs repository as an "upstream" remote to keep your fork in sync:

```shell
git remote add upstream https://github.com/pyrevitlabs/pyrevit.git
```

You can choose any name for the remote, but "upstream" is a common convention.

### Retrieve the submodules

At this time of writing, the pyRevit repository uses git submodules (stored in the `dev\modules` folder) to get some of its dependencies.
Initialize and fetch them with the following commands:

```shell
git submodule update --init --recursive
```

!!! note

    you may have to repeat the `git submodule update` command when you switch to another existing branch, or when new commits in the develop branch update the dependencies.

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

To run and test your changes in Revit, follow these steps:

1. **Create a Clone**: If you cloned the git repository without the pyRevit CLI, you need to use it now to create a clone of your git directory:

   ```shell
   pyrevit clones add dev <path-to-your-git-directory>
   ```

2. **Attach the Clone**: Attach your clone to the default Revit installation:

   ```shell
   pyrevit attach dev default --installed
   ```

!!! note

    the pyRevit dll paths have changed with pyrevit 5 (current WIP version), so you need to use the pyrevit CLI from a WIP installer for this to work.
    If you don't have it already, you can build the CLI from sources and run it with

    ```shell
    pipenv run pyrevit build labs
    copy .\release\.pyrevitargs .
    .\bin\pyrevit.exe attach dev default --installed
    ```

## Debugging Code

Currently, you cannot use Visual Studio's "Run" button to debug pyRevit because of some build issues. Instead, follow this approach:

1. **Build the Project**: Open a command prompt or PowerShell, navigate to your git directory, and build the project in Debug mode:

   ```shell
   pipenv run pyrevit build products Debug
   ```

2. **Open the Solution in Visual Studio**: Once the DLLs are built, open the `pyRevitLabs.PyRevit.Runtime` solution in Visual Studio.

3. **Attach the Debugger**: Attach the Visual Studio debugger to the `revit.exe` process to start debugging:
   - Go to `Debug` > `Attach to Process...` and select `revit.exe` from the list.

## Conclusion

You're now ready to start contributing to pyRevit! Whether you're fixing bugs, adding new features, or improving documentation, your contributions are valuable. If you have any questions, feel free to reach out to the community through GitHub or other communication channels.

Happy coding!
