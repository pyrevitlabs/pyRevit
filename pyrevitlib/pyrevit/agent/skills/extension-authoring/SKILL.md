---
name: extension-authoring
description: Turning a working script into a pyRevit button the user keeps. Covers where agent-made extensions live, adding and removing extension search paths, the bundle folder layout, bundle.yaml, converting an agent script into a button script, reloading pyRevit, and checking the button loaded. Use it for "make this a button", "add a tool to the ribbon", "create a pyRevit extension for this", "load the extension in this folder", "remove that tab" and similar tasks.
---

# Extension authoring

A button outlives the conversation: it runs whenever the user clicks it, without the run guard, rollback or approval prompt that protect agent runs. Build it only from a script that already works, and only with the user's go-ahead.

## Workflow

1. **Prove the logic first.** Develop it with `run_query`, or `run_modify` with `dry_run=true`, until it does the job on the user's model.
2. **Agree on the button.** Before writing anything to disk, tell the user the extension, tab, panel and button names, the folder you will write to, and what the button does. Write files only after they agree.
3. **Write the bundle** in the layout below, with your own file tools. If you have none, write the files from a `run_query` script with `open()`; file writes aren't rolled back.
4. **Register the folder** if it isn't `%APPDATA%\pyRevit\Extensions` (see [Extension search paths](#extension-search-paths)).
5. **Reload pyRevit** (see [Reload](#reload)).
6. **Check it loaded** (see [Check the button](#check-the-button)), then ask the user to try it.

## Where agent-made extensions live

- By default, put them in `%APPDATA%\pyRevit\Extensions\`. pyRevit loads every `*.extension` folder there without any configuration.
- When the user wants them somewhere else, such as next to their scripts or in a repository, put them there and register that folder as a search path.
- Keep everything you make in one extension, for example `AgentTools.extension`, unless the user asks for another. Ask the user what to call it the first time.
- Never edit extensions you didn't create: not the ones shipped with pyRevit (`pyRevitTools`, `pyRevitCore`, ...) and not the user's own. Updates overwrite the shipped ones, and the user's own belong to them.

## Extension search paths

A search path is a folder that *contains* `*.extension` folders, not an extension folder itself. Changing the list changes the user's pyRevit config, so do it only when the user asked for it or agreed to it. Run this with `run_query`, passing `inputs={"path": ..., "action": "add"}` or `"remove"`:

```python
import os
from pyrevit.userconfig import user_config

path = inputs.get("path") or ""
if not os.path.isabs(path) or (inputs["action"] == "add" and not os.path.isdir(path)):
    raise ValueError("Extension search path must be an absolute, existing folder: {!r}".format(path))
path = os.path.normpath(path)
paths = user_config.get_thirdparty_ext_root_dirs(include_default=False)
others = [p for p in paths if os.path.normcase(os.path.normpath(p)) != os.path.normcase(path)]
user_config.set_thirdparty_ext_root_dirs(others + [path] if inputs["action"] == "add" else others)
user_config.save_changes()
result = user_config.get_thirdparty_ext_root_dirs(include_default=False)
```

- Always pass an absolute path. A relative or empty one would register Revit's working folder.
- Removing a path takes its tabs off the ribbon after the reload; the folder stays on disk. Say so, and delete files only if the user asks.
- With a shell, `pyrevit extensions paths add <path>` and `pyrevit extensions paths forget <path>` do the same.

## Reload

Reload pyRevit with `run_query`, so the new or removed extensions take effect:

```python
from pyrevit.loader import sessionmgr
result = {"session": str(sessionmgr.reload_pyrevit())}
```

- Tell the user first: the ribbon rebuilds, which takes about 10-20 seconds, and any open pyRevit window closes.
- The agent host keeps serving during and after the reload; your next request works as usual.
- Don't reload while the user is in the middle of a pyRevit tool.

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
- **Modules in `lib\`:** pyRevit may reuse a button's engine between clicks, and with it the modules it already imported. A module that reads `revit.doc` at import time would then keep the document of the first click. Read `revit.doc` inside functions, or set a clean engine in the button's `bundle.yaml`:

  ```yaml
  engine:
    clean: true
  ```
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

After the reload, check the ribbon and the commands with `run_query`, passing the extension folder and the tab title as `inputs`:

```python
import os
import clr
clr.AddReference("AdWindows")
from Autodesk.Windows import ComponentManager
from pyrevit.loader import sessionmgr

extension = os.path.normcase(os.path.normpath(inputs["extension"]))
tabs = [tab for tab in ComponentManager.Ribbon.Tabs if tab.Title == inputs["tab"]]
result = {
    "tab_visible": bool(tabs) and bool(tabs[0].IsVisible),
    "panels": [panel.Source.Title for panel in tabs[0].Panels] if tabs else [],
    "commands": [
        command.typename
        for command in sessionmgr.find_all_commands(cache=False)
        if os.path.normcase(command.script or "").startswith(extension)
    ],
}
```

- **New button:** `tab_visible` is true and its command is listed. Nothing listed means pyRevit didn't load the bundle: check the folder suffixes and that its parent folder is a search path, then ask the user whether the pyRevit output window showed a load error.
- **Removed tab:** `tab_visible` is false. Its commands can stay listed until Revit restarts, because Revit can't unload the assembly pyRevit built for them; that's expected.
- Then ask the user to click the button and tell you what happened. Don't click it for them with a script: the button has no run guard.

## Changing or removing a button

- **Change:** edit the files, then reload. Keep the folder names unless the user wants the button renamed.
- **Remove:** after the user agrees, delete the button folder, or the whole extension folder, or remove its search path to keep the files. Then reload.

## Before you report done

- [ ] The user agreed to the names, the folder and any search path change before you wrote them.
- [ ] Only your own extension changed; no shipped or user extension was edited.
- [ ] After the reload, the check shows the tab visible and every new command listed.
- [ ] The user clicked the button and told you what happened.
- [ ] You told the user the extension's folder and how to remove it.
