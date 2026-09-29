---
name: extension-authoring
description: Turning a working script into a pyRevit button the user keeps. Covers where agent-made extensions live, the bundle folder layout, bundle.yaml, converting an agent script into a button script, reloading pyRevit, and checking the button loaded. Use it for "make this a button", "add a tool to the ribbon", "create a pyRevit extension for this" and similar tasks.
---

# Extension authoring

A button outlives the conversation: it runs whenever the user clicks it, without the run guard, rollback or approval prompt that protect agent runs. Build it only from a script that already works, and only with the user's go-ahead.

## Workflow

1. **Prove the logic first.** Develop it with `run_query`, or `run_modify` with `dry_run=true`, until it does the job on the user's model.
2. **Agree on the button.** Before writing anything to disk, tell the user the extension, tab, panel and button names, the folder you will write to, and what the button does. Write files only after they agree.
3. **Write the bundle** in the layout below, with your own file tools. If you have none, write the files from a `run_query` script with `open()`; file writes aren't rolled back.
4. **Reload.** Ask the user to click **pyRevit → Reload**. Don't reload pyRevit from a run: it rebuilds the session, including the agent host serving your request.
5. **Check it loaded** (see [Check the button](#check-the-button)), then ask the user to try it.

## Where agent-made extensions live

- Put them in `%APPDATA%\pyRevit\Extensions\`. pyRevit loads every `*.extension` folder there without any configuration.
- Keep everything you make in one extension, for example `AgentTools.extension`, unless the user asks for another. Ask the user what to call it the first time.
- Never edit extensions you didn't create: not the ones shipped with pyRevit (`pyRevitTools`, `pyRevitCore`, ...) and not the user's own. Updates overwrite the shipped ones, and the user's own belong to them.

## Layout

```text
%APPDATA%\pyRevit\Extensions\
  AgentTools.extension\
    lib\                     optional: modules every button can import
    Agent Tools.tab\
      Rooms.panel\
        Number Rooms.pushbutton\
          script.py
          bundle.yaml
          icon.png           optional, 32x32 PNG
```

- The folder names are the UI: the tab is named after `*.tab`, the panel after `*.panel`, and the button after `*.pushbutton`, unless `bundle.yaml` sets `title`.
- The folder suffixes are required. Use `.pushbutton` for a plain button. A `.pulldown` or `.stack` groups several buttons; put `.pushbutton` folders inside it.
- A module shared by several buttons goes in the extension's `lib\` folder, which is on `sys.path` for every script in the extension. Copy helpers you kept in your `workspace` there; a button can't see your workspace.

## bundle.yaml

```yaml
title: Number Rooms
tooltip: Numbers the rooms on the active level from left to right.
author: pyRevit agent
context: doc-project
```

- `title` and `tooltip` are what the user sees. Say what the button does and to what.
- `context` greys the button out when it can't work: `selection` (something is selected), `doc-project`, `doc-family`, `zero-doc`, `active-3d-view`, or a category such as `OST_Rooms`. Leave it out when the button works anywhere.

## From agent script to button script

The names an agent run injects don't exist in a button script. Replace them:

| Agent run | Button script |
|---|---|
| `doc`, `uidoc` | `from pyrevit import revit` then `revit.doc`, `revit.uidoc` |
| `DB`, `UI` | `from pyrevit import DB, UI` |
| `inputs` | ask the user: `from pyrevit import forms` then `forms.ask_for_string(...)`, `forms.SelectFromList.show(...)`, `forms.alert(...)` |
| `result = ...` | report to the user: `from pyrevit import script` then `script.get_output().print_md(...)`, or `forms.alert(...)` |
| `run_modify` approval | one `with revit.Transaction("Number rooms"):` block; the user undoes it with Ctrl+Z |

- **Engine:** a `script.py` runs on the session's IronPython (`get_context.scripting.engines.ironpython.python`), not on the agent run engine. Write for that version. `#! python3` on the first line switches the button to CPython, only when `scripting.engines.cpython.available` is true.
- **Selection:** `revit.get_selection()` returns the selected elements. Check it's not empty and tell the user what to select when it is.
- **Failures:** let the button tell the user what went wrong with `forms.alert(...)` instead of raising, and keep every model change inside the transaction so a failure changes nothing.
- **No `print` for results the user must act on:** printed text goes to the pyRevit output window, which the user may close without reading.

Minimal button:

```python
from pyrevit import revit, DB, forms

rooms = [
    room for room in DB.FilteredElementCollector(revit.doc).OfCategory(DB.BuiltInCategory.OST_Rooms)
    if room.Area > 0
]
if not rooms:
    forms.alert("No placed rooms in this model.", exitscript=True)

with revit.Transaction("Number rooms"):
    for number, room in enumerate(sorted(rooms, key=lambda r: r.Location.Point.X), 1):
        room.Number = str(number)

forms.alert("Numbered {} rooms.".format(len(rooms)))
```

## Check the button

After the user reloads, confirm the command exists with `run_query`:

```python
import os
from pyrevit.loader import sessionmgr

extension = os.path.join(os.environ["APPDATA"], "pyRevit", "Extensions", "AgentTools.extension")
result = [
    {"command": command.typename, "script": command.script}
    for command in sessionmgr.find_all_commands(cache=False)
    if (command.script or "").lower().startswith(extension.lower())
]
```

An empty list means pyRevit didn't load the bundle: check the folder suffixes, then ask the user whether the pyRevit output window showed a load error. Then ask the user to click the button and tell you what happened.

## Changing or removing a button

- **Change:** edit the files, then ask for another Reload. Keep the folder names unless the user wants the button renamed.
- **Remove:** delete the button folder, or the whole extension folder, after the user agrees, then ask for a Reload.
