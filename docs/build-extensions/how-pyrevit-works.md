# How pyRevit works

pyRevit's architecture has three major components. Each of of these components are documented under [Developer Docs](index.md)  

## pyRevit Bundles
---

Bundles are single, or collection of tools, scripts, libraries, and other content. pyRevit Core decides how to incorporate these bundles into the Revit environment, depending on the bundle type. The most basic bundle is a **Command Button** bundle (`.pushbutton`). Each command bundle is a folder that contains a script file (`script.*`) and might also include an icon (`icon.*`) and is named similar to `MyButton.pushbutton`

Command bundles are grouped and organized inside **UI Bundles** and then placed inside an **Extension** (`.extension`) bundle. Extensions are collection of bundles - of many types - that make these bundles accessible through the Revit user interface.

## pyRevit Runtime
---

Runtime is the part that is in charge of parsing the bundles, creating necessary assembly files, preparing the user interface, and executing the commands. pyRevit runtime is currently a combination of C#, and IronPython code (see `pyrevit/runtime/` directory under pyRevit files). The C# code is dynamically compiled on launch time and is cached for performance. This allows dynamic changes to the runtime code that gets reflected when pyRevit reloads. pyRevit can reload without restarting Revit.

## pyRevit Core

The core is a collection of tools (e.g. [pyRevit CLI](../cli/index.md)  or Telemetry System ) and libraries (e.g. Labs API Overview ) that assist the Bundles and Runtime. See `bin/` directory under pyRevit files.
