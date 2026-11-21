# How pyRevit works

pyRevit has three parts you meet when you build tools for it.

## Bundles

A bundle is a folder with a special name that holds a tool, a group of tools, or other content. pyRevit decides how to show a bundle in Revit from its type. The most common one is the **command bundle** (`.pushbutton`): a folder such as `MyButton.pushbutton` that contains a script (`script.*`) and usually an icon (`icon.*`).

Command bundles are grouped inside **UI bundles** (tabs, panels, pull-downs, stacks), and everything lives inside an **extension** (`.extension`). See [Command bundles](bundles/command-bundles.md), [UI bundles](bundles/ui-bundles.md) and [Extension structure](extensions/structure.md).

## Loader and runtime

When Revit starts, the pyRevit add-in reads the extensions, builds the ribbon and creates a command for every bundle. When a button is clicked, the runtime runs its script on the right engine: IronPython, CPython, C#, VB.NET, Dynamo or Grasshopper.

pyRevit can reload without restarting Revit, so new or changed bundles show up after **Reload**.

[Understanding pyRevit Architecture](../architecture.md) describes these components in detail.

## Command line and services

The [pyRevit CLI](../cli/index.md) installs, configures and repairs pyRevit from a command prompt. [Telemetry](../teams/telemetry.md) and [Routes](../teams/routes.md) are optional services for teams.
