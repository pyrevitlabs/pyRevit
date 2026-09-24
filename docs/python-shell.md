# Interactive Python shell

pyRevit ships an interactive IronPython console that runs on the engine the current session is
loaded with. Statements execute against the live model, with syntax highlighting and
<kbd>Ctrl</kbd>+<kbd>Space</kbd> autocompletion.

It lives at **pyRevit tab → pyRevit panel → Python Shell**.

The console is built on AvalonEdit and lives in `dev/pyRevitLabs.PyRevit.Shell`.

## Opening modes

<kbd>Shift</kbd>+click the button to pick how it opens. The choice persists in the button's script
config, so the next plain click uses it.

| Mode | Window | Editor pane | Needs an open project |
|---|---|---|---|
| `Modeless` (default) | Floating, non-blocking | no | no |
| `Modeless Editor` | Floating, non-blocking | yes | no |
| `Modal` | Blocks Revit until closed | no | no |
| `Modal Editor` | Blocks Revit until closed | yes | no |
| `Docked` | Revit dockable pane | no | **yes** |
| `Docked Editor` | Revit dockable pane | yes | **yes** |

The editor variants add a code panel beside the prompt, for composing something longer than a single
statement before running it.

Docked modes need an open project because Revit only hosts dockable panes when a document is open.
Picking one with no project loaded raises a dialog pointing you at the modeless modes; the button
itself is `context: zero-doc`, so it stays enabled either way.

## Which engine it runs on

The shell attaches to the engine pyRevit is **already** loaded with — it locates the loaded
`pyRevitLoader` assembly and loads `pyRevitLabs.PyRevit.Shell.dll` from beside it, which preserves
the active engine fork. It also copies the launching engine's `sys.path` into the console, so
imports resolve the same way they do in a normal script.

That means it is **IronPython only**. The shell assembly is deployed to `IPY2712PR` and `IPY342`,
not to the CPython engines. If pyRevit is running on a CPython engine, the button reports that the
shell is not installed for the active engine.

## Theming

The console follows Revit's UI theme rather than always rendering dark — the prompt, the editor
surface, the completion popups, and the dockable pane's own background all switch together. See
[Theming and dark mode](theming.md).

## Keeping Revit responsive

Statements in modeless and docked shells are marshalled through a Revit `ExternalEvent`. Revit stays interactive while a
modeless or docked shell is open, and the statement runs in a valid API context, so model
modifications behave the same as they would from a button.

## Startup cost

Registering the dockable pane does not load the shell:

- The pane defaults to hidden, and is re-hidden on the first Idling tick after startup. Revit
  persists dockable pane visibility across sessions, so without this a pane you opened once would
  reappear in every later session.
- `pyRevitLabs.PyRevit.Shell.dll` loads during session startup so the dockable pane can be
  registered. The console itself is built later, on an Idling handler once the pane is shown.

A shell you never open still incurs assembly loading and pane registration, but not console construction.

## Troubleshooting

**"Python Shell is not installed for the active engine"** — the shell DLL is missing next to the
loaded engine. Expected on CPython engines; on an IronPython engine it means the deployment is
incomplete, so rebuild or reinstall.

**"The docked Python Shell pane is not registered for this session"** — the pane is registered at
startup by `pyRevitCore.extension/startup.py`. Reload pyRevit, or switch to a modeless mode.

**The pane is empty** — a build failure renders its traceback inside the pane rather than leaving a
blank surface, so read the pane first, then the log.
