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

The shell creates a new IronPython host that uses the same deployment/runtime family as the
engine pyRevit is **already** loaded with. It locates the loaded `pyRevitLoader` assembly and
loads `pyRevitLabs.PyRevit.Shell.dll` from beside it, which preserves the active engine fork.
It also copies the launching engine's `sys.path` into the console, so
imports resolve the same way they do in a normal script.

That means it is **IronPython only**. The shell assembly is deployed to `IPY2712PR` and `IPY342`,
not to the CPython engines. For the non-docked modes, if pyRevit is running on a CPython engine, the
button reports that the shell is not installed for the active engine.
For Docked and Docked Editor modes, if the pane is unavailable, the button
reports that the Python Shell pane is not registered for this session.

## Theming

The console follows Revit's UI theme rather than always rendering dark — the prompt, the editor
surface, the completion popups, and the dockable pane's own background all switch together. See
[Theming and dark mode](theming.md).

## Keeping Revit responsive

Statements in modeless and docked shells are marshalled through a Revit `ExternalEvent`. Revit stays interactive while a
modeless or docked shell is open, and the statement runs in a valid API context, so model
modifications behave the same as they would from a button.

## Interrupting the shell

<kbd>Ctrl</kbd>+<kbd>C</kbd> with no selection interrupts the current Python statement and prints `KeyboardInterrupt`.
With a selection, the shortcut copies the selected text.
The console handles <kbd>Ctrl</kbd>+<kbd>C</kbd> locally during execution and when idle; the shortcut does not invoke Revit's Copy command.
The shell must have keyboard focus and its containing window must be in the foreground.
Interrupts are checked at Python trace events, without processing nested Revit UI messages.
A long-running .NET or native call, such as `time.sleep(60)`, cannot be preempted; cancellation takes effect at the next Python trace event.
An interrupt belongs to its current statement; a delayed key event or a shortcut still held after that statement ends does not cancel the next statement.
Code that replaces or disables `sys.settrace` disables these trace checks.
Each statement installs the shell's trace callback and resets `sys.settrace` to `None` when it finishes; user trace callbacks do not persist between statements.
IronPython disables tracing when a trace callback raises an exception.
A bare `except:` or `except BaseException:` can swallow `KeyboardInterrupt`; subsequent interrupts cannot stop that statement after its tracing has been disabled.
Interruptible loops must allow `KeyboardInterrupt` to propagate.

An interrupt also cancels a queued statement waiting for Revit API context.
The cancelled statement does not run when Revit later processes the external event.
Pressing <kbd>Enter</kbd> during completion cancels that completion request without aborting a thread.
Running editor code while another statement is pending prints a busy message; the editor retains the code for another run.


## Regression tests

`dev/pyRevitLabs/tests/pyRevitLabs.PyRevit.Shell.Tests` tests execution cancellation, external-event queue lifetime, and a real IronPython REPL's shutdown without Revit.
The test project builds the pinned vendored engines from initialized submodules; it does not require a prebuilt product `bin` directory.
Run `dotnet test dev/pyRevitLabs/tests/pyRevitLabs.PyRevit.Shell.Tests/pyRevitLabs.PyRevit.Shell.Tests.csproj -p:IronPythonVersion=IPY2712PR` and repeat with `IPY342`.
`ShellEnginesDirectory` selects an existing engine deployment for testing instead of building engine sources.
The build pipeline runs both engine variants against its built assemblies after the runners build. The project is not part of the Labs solution build, which precedes engine staging.
On Windows, the same project also runs the WPF dispatcher error-path test; that test cannot execute on macOS.


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
