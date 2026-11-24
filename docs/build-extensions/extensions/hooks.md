# Hooks

UI Extensions can contain a `hooks/` subdirectory. This directory can contain especially named scripts that would hook up to the Revit event system and will get executed whenever that event occurs. For example, a `doc-changed.py` hook script, gets executed automatically every time **DocumentChanged** event occurs in Revit.

- Under current implementation, Python, CPython, C#, and VB.NET hook scripts are supported.
- The hooks scripts are only active if the Extension containing them is active and loaded. Disabling the extension, disables all the hook scripts in that extension.
- For performance reasons, multiple hooks scripts for the same event are NOT supported under the same `hooks/` directory. There are many events firing when working with Revit and having too many hooks will reduce performance dramatically due to the overhead of reading, compiling, and executing an external code file every time an event occurs.
- Hooks that are not supported under the running Revit version will not be activated.

**Hook Script Types**

| Hook Script Name | Revit Event Type | Comments |
|---|---|---|
| options-showing.\* | UIApplication.DisplayingOptionsDialog |  |
| app-init.\* | Application.ApplicationInitialized |  |
| app-closing.\* | UIApplication.ApplicationClosing |  |
| app-idling.\* | UIApplication.Idling |  |
| dialog-showing.\* | UIApplication.DialogBoxShowing |  |
| doc-changed.\* | Application.DocumentChanged |  |
| doc-closed.\* | Application.DocumentClosed |  |
| doc-closing.\* | Application.DocumentClosing |  |
| doc-created.\* | Application.DocumentCreated |  |
| doc-creating.\* | Application.DocumentCreating |  |
| doc-opened.\* | Application.DocumentOpened |  |
| doc-opening.\* | Application.DocumentOpening |  |
| doc-printed.\* | Application.DocumentPrinted |  |
| doc-printing.\* | Application.DocumentPrinting |  |
| doc-saved-as.\* | Application.DocumentSavedAs |  |
| doc-saved.\* | Application.DocumentSaved |  |
| doc-saving-as.\* | Application.DocumentSavingAs |  |
| doc-saving.\* | Application.DocumentSaving |  |
| doc-synced.\* | Application.DocumentSynchronizedWithCentral |  |
| doc-syncing.\* | Application.DocumentSynchronizingWithCentral |  |
| doc-worksharing-enabled.\* | Application.DocumentWorksharingEnabled |  |
| dock-focus-changed.\* | UIApplication.DockableFrameFocusChanged |  |
| dock-visibility-changed.\* | UIApplication.DockableFrameVisibilityChanged |  |
| fabparts-browser-changed.\* | UIApplication.FabricationPartBrowserChanged |  |
| failure-processing.\* | Application.FailuresProcessing |  |
| family-loaded.\* | Application.FamilyLoadedIntoDocument |  |
| family-loading.\* | Application.FamilyLoadingIntoDocument |  |
| file-exported.\* | Application.FileExported |  |
| file-exporting.\* | Application.FileExporting |  |
| file-imported.\* | Application.FileImported |  |
| file-importing.\* | Application.FileImporting |  |
| formula-editing.\* | UIApplication.FormulaEditing |  |
| link-opened.\* | Application.LinkedResourceOpened |  |
| link-opening.\* | Application.LinkedResourceOpening |  |
| progress-changed.\* | Application.ProgressChanged | Fires a lot and reduces performance. Use only when absolutely needed. |
| transferred-project-standards.\* | UIApplication.TransferredProjectStandards |  |
| transferring-project-standards.\* | UIApplication.TransferringProjectStandards |  |
| type-duplicated.\* | Application.ElementTypeDuplicated |  |
| type-duplicating.\* | Application.ElementTypeDuplicating |  |
| view-activated.\* | UIApplication.ViewActivated |  |
| view-activating.\* | UIApplication.ViewActivating |  |
| view-exported.\* | Application.ViewExported |  |
| view-exporting.\* | Application.ViewExporting |  |
| view-printed.\* | Application.ViewPrinted |  |
| view-printing.\* | Application.ViewPrinting |  |
| worksharing-ops-progress-changed.\* | Application.WorksharedOperationProgressChanged |  |
| command-before-exec\[\<cmd-id\>\].\* | AddInCommandBinding.BeforeExecuted | Executed before the original command is executed.<br>**See Notes** |
| command-can-exec\[\<cmd-id\>\].\* | AddInCommandBinding.CanExecute | Executed when Revit needs to know whether a tool is available in the GUI or not. **See Notes** |
| command-exec\[\<cmd-id\>\].\* | AddInCommandBinding.Executed | Overrides the normal function of the tool |
| journal-updated.\* | N/A (This is a pyRevit-provided hook) | Executed when the current Journal is updated.<br>**See Notes** |
| doc-updater.\* | N/A (This is a pyRevit-provided hook) |  |
| journal-command-exec.\* | N/A (This is a pyRevit-provided hook) | Executed when a new command execution is detected in the journal file. **See Notes** |

!!! tip ""

    Start with the short introduction to hook scripts at [Create Your First Hook](../tutorials/first-hook.md)  

!!! warning ""

    Current pyRevit implementation supports hook scripts in IronPython, CPython, C#, and VB.Net  

    See [Anatomy of IronPython Scripts](../scripting/ironpython.md)  for more information about IronPython scripts and the support modules  
    See [Anatomy of CPython Scripts](../scripting/cpython.md)  for more information about CPython scripts and the support modules  
    See [Anatomy of .NET (C#, VB) Scripts](../scripting/dotnet.md)  for more information about .NET scripts and the support modules

!!! tip ""

    The examples here are all part of the `pyRevitDevHooks.extension` (part of the `basex` deployment, see [Deployments](../../teams/deployments.md))

## Python Hook Scripts

Both IronPython and CPython engines provide the two `__eventsender__` and `__eventargs__` global variables to give you access to the event sender and arguments provided by Revit. Avoid using these variables directly though. The `pyrevit` module gives you safe access to them using `EXEC_PARAMS` as shown below. This way you will mask your scripts against interal pyRevit runtime changes should the name of these global variables ever change.

**Runtime Global Variables**

```python
# ONLY FOR EVENT HOOKS

# event sender
__eventsender__
# event arguments
__eventargs__
```

**Safe Access Method**

```python
from pyrevit import EXEC_PARAMS

# event sender
EXEC_PARAMS.event_sender
# event arguments
EXEC_PARAMS.event_args
```

See the Revit API documentation for the event argument types provided by `EXEC_PARAMS.event_args` (differ based on the event type). There are plenty of examples for hook scripts under the `pyRevitDevHooks.extension`. Below are examples of a hook script named `view-activated.py`

!!! tip ""

    In the test examples below, the hook scripts write some information about the event to a log file named `hooks.log` on user desktop.

### IronPython

!!! warning ""

    pyRevit caches the IronPython engine that is used for event hooks. Reload pyRevit if you are making changes to the modules being imported by the hook scripts to refresh the IronPython engine

IronPython hook scripts are written like any other IronPython script.

```python
from pyrevit import EXEC_PARAMS

# hooks_logger is a helper module to provide write methods to hooks.log
# that all python hook scripts can use
import hooks_logger

# __file__ is set to the path of the hook script, per python conventions
hooks_logger.log_hook(__file__,
    {
        "cancellable?": str(EXEC_PARAMS.event_args.Cancellable),
        "doc": str(EXEC_PARAMS.event_args.Document),
        "current_view": str(EXEC_PARAMS.event_args.CurrentActiveView),
        "prev_view": str(EXEC_PARAMS.event_args.PreviousActiveView),
        "status": str(EXEC_PARAMS.event_args.Status),
    }
)
```

#### CPython

The CPython hook script is identical to IronPython. Just start the first line with the CPython identifier.

```python
#! python3
```

## .NET Hook Scripts

!!! warning ""

    For .NET scripts, pyRevit will look for a method with the correct event handler signature for that specific event type. If a correct method is not provided, nothing will happen.

!!! tip ""

    In the test examples below, the hook scripts write some information about the event to a log file named `hooks.log` on user desktop.

### C#

The example below is taken from `pyRevitDevHooks.extension` and is named `view-activated.cs`. When the **ViewActivated** event happens, pyRevit finds the method defining the signature with sender `object sender` and event arguments `ViewActivatedEventArgs e` and executes the method, passing the sender and arguments objects provided by Revit.

```csharp
using System;
using System.IO;

using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

namespace MyEvents {
    public class MyEventMgr {
        // executor needs to find the correct function signature and executes that
        // first argument name must be "sender", type must be object
        // second argument name must be either "e" or "args" and type must be the event argument type associated
        // with the hook event type
        public void MyEventMgr_UiApp_ViewActivated(object sender, Autodesk.Revit.UI.Events.ViewActivatedEventArgs e) {
            string desktopPath = Environment.GetFolderPath(Environment.SpecialFolder.Desktop);
            File.AppendAllText(
                Path.Combine(desktopPath, "hooks.log"),
                string.Format("[view-activated-csharp] doc:\"{0}\" active_view:\"{1}\" prev_view:\"{2}\" status:\"{3}\"\n",
                    e.Document != null ? e.Document.ToString() : "",
                    e.CurrentActiveView != null ? e.CurrentActiveView.ToString() : "",
                    e.PreviousActiveView != null ? e.PreviousActiveView.ToString() : "",
                    e.Status.ToString()
                )
            );
        }
    }
}
```

### VB.NET

The example below is taken from `pyRevitDevHooks.extension` and is named `view-activated.vb`. When the **ViewActivated** event happens, pyRevit find the method defining the signature with sender `sender As Object` and event arguments `e As ViewActivatedEventArgs` and executes the method, passing the sender and arguments objects provided by Revit.

```vbnet
Imports System
Imports System.IO
Imports Microsoft.VisualBasic

Imports Autodesk.Revit.UI
Imports Autodesk.Revit.UI.Events
Imports Autodesk.Revit.DB

Public Class MyEventMgr
    ' executor needs to find the correct function signature and executes that
    ' first argument name must be "sender", type must be object
    ' second argument name must be either "e" or "args" and type must be the event argument type associated
    ' with the hook event type
    Public Sub MyEventMgr_UiApp_ViewActivated(sender As Object, e As ViewActivatedEventArgs)
        File.AppendAllText(
             Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Desktop), "hooks.log"),
                     String.Format("[view-activated-vb] doc:""{0}"" active_view:""{1}"" prev_view:""{2}"" status:""{3}""" + Environment.NewLine,
                                   If(e.Document IsNot Nothing, e.Document.ToString(), ""),
                                   If(e.CurrentActiveView IsNot Nothing, e.CurrentActiveView.ToString(), ""),
                                   If(e.PreviousActiveView IsNot Nothing, e.PreviousActiveView.ToString(), ""),
                                   e.Status.ToString()))
    End Sub
End Class
```

## Notes on specific hooks

### `command-before-exec[<cmd-id>].*`

This hook is executed when the command with id `<cmd-id>` is being executed in Revit.

For example:

    `command-before-exec[ID_INPLACE_COMPONENT].py`

is executed just before the **Model-In Place** (`ID_INPLACE_COMPONENT`) tool is executed in Revit. You can use these hooks to notify users of certain standards before the user can use the tool.

### `command-can-exec[<cmd-id>].*`

This hook is executed when Revit wants to know if the command with id `<cmd-id>` is available in the current context or not.

For example:

    `command-can-exec[ID_INPLACE_COMPONENT].py`

is executed, when the user switchs to the tab that contains the **Model-In Place** (`ID_INPLACE_COMPONENT`) tool. At this point, pyRevit calls this hook (initiated by the `CanExecute` event in Revit) to check whether this tools is available or not. The hook script needs to return `True` or `False` to Enable or Disable the tool in the Revit user interface.

```python
print(EXEC_PARAMS.event_args.ActiveDocument.Title)

# set the CanExecute property to enable/disable the tool in Revit GUI
EXEC_PARAMS.event_args.CanExecute = True
```

### `journal-command-exec.*`

!!! warning ""

    See the command execution tracking features in the [Telemetry System](../../teams/telemetry.md) first, if you intend to use this hook, to track the commands being executed in Revit interface.

If this hook is provided, pyRevit startes a Journal Listener that runs this hook every time the journal is updated. pyRevit will provide the ID of the detected command, through the hook `.event_args`

```python
from pyrevit import EXEC_PARAMS

print(EXEC_PARAMS.event_args.CommandId)
```

### `journal-updated.*`

!!! warning ""

    This hook adds a significant amount of overhead to pyRevit since the journal file is constantly being updated. If you intend to use this hook, to track the commands being executed in Revit interface, use the `journal-command-exec` hook or the command execution tracking features in the [Telemetry System](../../teams/telemetry.md)  

If this hook is provided, pyRevit startes a Journal Listener that runs this hook every time the journal is updated. You can grab the new lines added to the journal, every time this hook is executed, through the hook `.event_args`

```python
from pyrevit import EXEC_PARAMS

for new_journal_line in EXEC_PARAMS.event_args.NewJournalLines:
    print(new_journal_line)
```
