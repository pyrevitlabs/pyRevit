# Agent runtime

!!! warning "Status: experimental"

    The agent runtime is under active development on the `feature/agent-runtime` branch.
    It is off by default. Phase 0 (the in-Revit host) is validated on Revit 2024 and 2025; the CLI
    and MCP server (Phase 1) are in progress. See [Phases](#phases).

The agent runtime lets any MCP-capable coding agent (Claude Code, Codex, Cursor, VS Code,
OpenCode, ...) read and change a live Revit model by sending **Python programs**, not by calling
hundreds of per-API tools. The Revit API is the toolset; MCP is only the control
protocol. The human stays in control: by default, the model changes a run makes are approved inside Revit.

## Getting started

Everything below is also available in Revit under **pyRevit → Settings → Agent Runtime
(MCP)**. That section enables the host, sets the policy and default engine, shows whether
the host is listening, and has one button per MCP client to register the server. The agent
runtime is independent of the Routes server and doesn't need it enabled.

1. **Enable the agent host.** Run this with the `pyrevit.exe` of the clone you want the
   agent to use, then reload pyRevit or restart Revit.

    ```shell
    pyrevit configs agent enable
    ```

2. **Register the MCP server with your client.** The registration command does not change
   whether the host is enabled.

    ```shell
    pyrevit mcp install claude        # Claude Code, user scope
    pyrevit mcp install codex         # OpenAI Codex
    pyrevit mcp install cursor        # Cursor (~/.cursor/mcp.json)
    pyrevit mcp install vscode        # VS Code (user mcp.json)
    pyrevit mcp install opencode      # OpenCode (~/.config/opencode/opencode.json[c])
    ```

    Add `--project` to register for the current directory instead (Claude Code:
    `.mcp.json`, Cursor: `.cursor/mcp.json`, VS Code: `.vscode/mcp.json`, OpenCode:
    `opencode.json[c]`). Codex only supports user-level servers. A JSON config file that
    contains comments is never rewritten; the command prints the entry to add by hand.

3. **Start Revit** (or reload pyRevit), and open a model.
4. **Start an agent session.** Open **pyRevit → Agent Panel** (next to Python Shell) and
   click **Start on &lt;document&gt;**. Agents can read or change the model only while a session
   is active, and only in its document. When an agent asks for a session first, the panel
   opens with the agent's reason; click **Start** or **Decline**. See
   [Sessions and the agent panel](#sessions-and-the-agent-panel).
5. **Check the connection:**

    ```shell
    pyrevit agent status
    ```

6. **Ask your agent about the model**, for example *"How many doors on Level 2 have no
   Mark?"* or *"Set the Comments of the selected walls to 'Check fire rating'"*. Changes
   show an approval prompt in Revit, with the changed elements selected and temporarily
   isolated in the active view. *Keep* commits them as one undo entry named
   `Agent: <title>`; *Discard* rolls them back.

!!! note "Upgrading from an earlier build"

    Sessions are required by default. Until the user starts one in the agent panel, model
    tools answer `session_inactive`, and agents call `request_session` to ask for one. To keep
    the earlier behaviour on a dedicated agent machine, run
    `pyrevit configs agent requiresession no` and reload pyRevit.

To remove the server: `pyrevit mcp uninstall <client>`. `pyrevit mcp uninstall --all` removes
the user-level entry from every client, and the pyRevit uninstaller runs it with `--owned`, which
keeps entries that point at another pyRevit install. It only cleans the profile of the account
running it, never other users' profiles, so on a shared machine each user who registered the
server removes their own entry. When that command runs elevated, it doesn't start the `claude`
or `codex` command line tools, so those two entries stay; run `pyrevit mcp uninstall claude`
(or `codex`) from a normal prompt. Project-level entries
(`--project`) are never removed automatically. To turn the host off: `pyrevit configs agent disable`.

!!! warning "Model data leaves the machine and is recorded locally"

    Whatever the agent reads (element names, parameter values, results) is sent to
    the agent's model provider. Check this against your project's confidentiality rules
    before enabling the agent runtime. The runtime also stores each run's script, request,
    response, large result, and captured images in plaintext under `%APPDATA%\pyRevit\agent`
    for up to 14 days.

## Reference

### Configuration

| Setting | Command | Values |
|---|---|---|
| `[agent] enabled` | `pyrevit configs agent (enable \| disable)` | Starts the in-Revit host on the next pyRevit load. Default `false`. |
| `[agent] policy` | `pyrevit configs agent policy (readonly \| ask \| auto)` | `readonly`: queries and dry runs only; it does not sandbox Python or prevent file, network, or process side effects. `ask` (default): each modify run needs approval in Revit. `auto`: modify runs are committed without the prompt; each is still one undo entry, guarded and recorded. |
| `[agent] engine` | `pyrevit configs agent engine (ironpython \| cpython)` | Engine for runs that don't name one. Default `ironpython` (the attached IronPython). |
| `[agent] require_session` | `pyrevit configs agent requiresession (yes \| no)` | `yes` (default): model requests need a session the user starts in the agent panel. `no`: requests pass without one, as before sessions existed; a session the user starts still binds agents to its document, and only the user can end it. Read only when pyRevit loads, and a reload from inside an agent run can't turn it off. Also in pyRevit Settings. |
| `[agent] reckless` | `pyrevit configs agent reckless (enable \| disable)` | Default `false`. `true` runs scripts without the runner's in-script checks: no timeout and no transaction tracking. See [Reckless mode](#reckless-mode) for the risks. |

Run any of these commands without a value to print the current setting.

### Run document tab

The document captured at the start of a run has an amber pyRevit accent tab with black text throughout execution and the Keep/Discard prompt.
The tooltip reads `Agent: <run title>` during execution and `Agent: <run title> (awaiting approval)` during approval.
The highlight identifies the run document, not a document inspected by an earlier `get_context` request.
All tabs for the same native document identity are highlighted, even when document titles match.
The first successful paint remains visible for at least 1.5 seconds; consecutive runs on that document share the highlight without an intermediate restore.
Tab Coloring remains underneath the temporary overlay and resumes when it ends.

**Settings > Agent Runtime (MCP) > Highlight the document tab during agent runs** controls `[agent] tab_highlight`, which defaults to `true` and applies to the next run without reloading pyRevit.
The configuration accessor is `PyRevitConfigs.GetAgentTabHighlight()` / `SetAgentTabHighlight(bool)`; no flat Python userconfig alias is provided.
Three consecutive visual failures disable highlighting for the Revit process and produce one log entry without changing a run's outcome.

### MCP tools

| Tool | Changes the model | Purpose |
|---|---|---|
| `get_skill` | no | Task guidance in markdown (see [Skills](#skills)); the server's instructions tell agents which skill to read first |
| `list_revit_instances` | no | Running Revit sessions with the agent host, and each one's agent session state |
| `request_session` | no | Ask the user to start an agent session. The agent panel opens with the `reason` (at most 300 characters), at most once a minute. Only the user can start the session |
| `get_context` | no | Revit and pyRevit versions, agent policy (and `reckless: true` when [reckless mode](#reckless-mode) is on), `scripting` (engine and Python version scripts run on), document, `open_documents`, active view, selection, levels. The document and each open document carry a `key` that names it while it stays open; a reopened file gets a new one |
| `inspect_elements` | no | Class, category, type, level, location, bounding box and parameters of up to 50 elements of the `document` it names, active or not |
| `lookup_revit_api` | no | Signatures of a Revit API type or member, reflected from the running Revit. Also its namespace and Python import line, and a `creation` list: static factories and the `doc.Create.New…` methods that return the type. A missing member returns `found: false` with the closest names, including matching values of other enums |
| `show_elements` | no | Select, zoom to, or temporarily isolate / hide elements (by id or category) in the active view, or reset the temporary mode. The `document` it names must be the active one. No approval prompt. If Revit can't zoom, the response has `zoomed: false` and a `zoom_failed` error instead of a dialog blocking Revit. |
| `capture_view` | no | PNG of a view of the `document` it names, for visual checks. `export` renders any view through Revit, also in a document that isn't active; `viewport` renders an open view through Revit cropped to what its window shows now (zoom, pan, temporary isolate; no selection highlight), in a rolled-back transaction; `screen` captures the active view window as the user sees it (selection, temporary isolate); `viewport`, `screen` and view `active` need the document to be the active one, and fails with `view_obscured` when another application's window covers any part of it; view `3d` renders a temporary 3D view of model categories only, framed by a section box around the model (or `elements`) and seen from `direction`, which is rolled back. `eye` and `target` (feet) switch it to a perspective camera without a section box; `section` (`origin`, `normal`, optional `depth`) renders a temporary section or elevation for a horizontal `normal`, or a plan cut at `origin` height for `[0, 0, -1]`, framed on `elements` or the model. `detail_level` (`coarse`, `medium`, `fine`) and `display_style` (`wireframe`, `hidden_line`, `shaded`, `shaded_edges`) apply to the temporary view and, in `export` and `viewport` modes, to a named view for that capture only, inside the same rolled-back group (a view template that controls them is detached there). Saved under `%APPDATA%\pyRevit\agent\captures`. |
| `run_query` | never | Run a read-only script; model changes are always rolled back, but the script itself has full access to the machine, so the tool isn't marked read-only for MCP clients. `workspace` puts a folder of the agent's own modules on `sys.path`, re-imported fresh every run. `timeout_s` (default 300) stops a script that runs too long |
| `run_modify` | after approval | Run a changing script against the `document` it names. `dry_run=true` previews the change set and rolls back |
| `get_run` | no | A recorded run: response, script, and pages of a large result |
| `lookup_pyrevit_api` | no | Signature, docstring and import line of a pyrevitlib or rpw function, a module listing, or a search by words. Works without Revit |
| `list_automation` | no | The marked pyrevitlib and rpw operations (see [Automation operations](#automation-operations)), with `invocable` and the `inputs` each takes. Works without Revit |
| `run_automation` | never | Run an invocable operation by id with a JSON input object, in the `document` it names when the operation needs one. Runs as a query, so changes are rolled back; it accepts no Python source |

`run_query`, `run_modify`, `inspect_elements`, `show_elements` and `capture_view` require
`document`: a key from `get_context`. Element ids are always read in that document, so ids
from one document can't reach another. A key for a closed document is refused with
`unknown_document`. The CLI's `pyrevit agent run` takes `--document` and works in the active
document without it.

Every request that runs on Revit's main thread closes the dialogs Revit opens during it and
reports them in `dialogs`, so a dialog can't leave the call hanging.

Tools that read, show or change the model (`run_query`, `run_modify`, `inspect_elements`,
`show_elements`, `navigate_revit_link`, `capture_view`) require a `title` of at most 120
characters and accept a `reason` of at most 300. The agent panel shows both in its log.

Only agent-written code needs approval. `show_elements` is a fixed host operation that
changes presentation, never model elements. Temporary hide/isolate runs in its own small
transaction because the Revit API requires one, and that state isn't saved with the
model. The agent is told to use it rather than writing `run_modify` scripts to show
things.

`run_query` and `run_modify` return a compact result for the agent: `status`, then
`error` (when present), `decision`, `result`, `output`, and only the non-empty change
set, failures, dialogs and blocked operations. The full record stays available through
`get_run`. `AttributeError` and `TypeError` failures carry a `hint` that names the
`lookup_revit_api` call to make, for example `'Collector' does not exist in
Autodesk.Revit.DB` or `check the overloads of 'FilteredElementCollector.OfCategory'`.

If the host cannot persist a result or run record, the response keeps the final model decision
and adds a warning. The corresponding `get_run` record can be incomplete or unavailable.

Every tool that talks to Revit accepts an optional `revit` argument (a year such as
`"2024"`, or a process id) for when several Revit sessions run. `pyrevit mcp --revit=<year>`
sets a default.

### Automation operations

pyrevitlib and rpw functions marked with `@automation.operation` (from `pyrevit_automation`)
are listed by `list_automation` with a stable id, mode, effects, context and transaction.
`run_automation` can call an operation when it is hand-wired in
`dev/pyRevitLabs/pyRevitCLI/PyRevitAutomationOperations.cs`, or when its marker declares
`inputs` on a module-level `query` or `pure` function that opens no transaction:

```python
@automation.operation(
    "pyrevit.elements.name",
    PlainEnglish="Read an element name, including a view title on a sheet when requested.",
    effects=("model.read",),
    inputs=("element: element", "title_on_sheet: boolean?"),
)
def get_name(element, title_on_sheet=False):
```

Each input is `"<name>: <type>"`, with `?` for an optional one, and is passed as the keyword
argument of the same name. Types are `string` (non-blank, at most 256 characters), `number`,
`integer`, `boolean`, `element` (an element id, resolved in the named document) and `scalar`
(a string, number or boolean). `inputs=()` declares an operation that takes no inputs. A
function with a `doc` parameter gets the named document. List results keep their first 200
items and add `total` and `truncated`.

The CLI validates the inputs, then sends a fixed script that calls
`pyrevit.agent._operations.invoke`; the operation's module and function travel in the run's
inputs, never in the script. `invoke` checks the live marker and the inputs again inside
Revit. `dev/scripts/test_standalone_automation_marker.py` fails when declared inputs don't match the
function they mark.

!!! tip "Long approvals"

    A `run_modify` call waits until the user answers the prompt in Revit. The server
    sends progress notifications every 10 seconds while it waits. If your client still
    times out, raise its MCP tool timeout (Claude Code: the `MCP_TOOL_TIMEOUT`
    environment variable, in milliseconds).

### Sessions and the agent panel

The **pyRevit Agent** panel is a dockable pane where the user decides when agents may work.
Open it with **pyRevit → Agent Panel**. The button is hidden while the agent host is
disabled.

- **Start on &lt;document&gt;** starts a session bound to the active document. Only a click in the
  panel starts or resumes a session. Agents and the CLI can only ask for one or pause it, and
  end it while sessions are required.
- **Pause** and **Resume** stop and restart model requests. A request already waiting for
  Revit is refused when Revit picks it up.
- **End** ends the session. Closing the session's document ends it too.
- **Move session to &lt;document&gt;** appears while another document is active. The session keeps
  its id and state. From then on, requests that name the document it left are refused with
  `document_not_in_session`.
- Closing the panel pauses the session. Reopening the panel shows why, and only the user
  resumes it.

While another document, or none, is active, the panel says so. Agents still work in the
session's document by its key; only `show_elements`, and captures of the window, need it to be
active, and get `wrong_document` until the user switches back.

The panel also shows the policy, the MCP client that called last, the last request, and what a
waiting request is held up by (the approval prompt or a Revit dialog). Its activity log lists
the latest 200 requests of this Revit session, grouped by session: title and reason, outcome,
changes by category, elements to click and select, and for runs the script, output, errors
and engine. Lookups (`get_context`, `lookup_revit_api`) are hidden unless **Show lookups** is
on. The log lives in memory; run records stay on disk.

Model requests are refused with these error types. `ping`, `lookup_revit_api` and the
session requests always pass.

| Error type | When | What the agent does |
|---|---|---|
| `session_inactive` | Sessions are required and none is active | Call `request_session`, tell the user, and wait |
| `paused_by_user` | The user paused the session | Wait until the user resumes it |
| `paused_by_host` | pyRevit paused it: a run changed another open document, or the panel was closed. The message says which | Tell the user; only they can resume it |
| `paused_by_agent` | An agent paused it, with `pyrevit agent session pause` or from code in a run | Tell the user; only they can resume it |
| `document_not_in_session` | The request names another document than the session's, or names none while another document is active | Work in the session's document, or ask the user to move the session |
| `unknown_document` | No open document has the key: it was closed, or the key is wrong | Call `get_context` for the open documents' keys, and drop ids from a closed document |
| `wrong_document` | `show_elements`, or a capture of the window, names a document that isn't active | Ask the user to switch to it, or export a named view or `3d` instead |
| `session_locked` | Code running inside an agent run tried to start, resume or move the session or make sessions optional, or an agent tried to end it while sessions aren't required | Nothing; an agent can't loosen its own session. Pause it to stop |

When the user changed the session's document, view or selection since the agent's previous
model request, the next response carries `since_last_call`:

- `edits`: added, modified and deleted counts, up to 20 ids of each, the transaction names,
  and how many were undone or redone.
- `active_view`: the view now active, when it changed.
- `selection`: the count and up to 200 ids, when it changed.
- `session_moved`: `from` and `to`, when the user moved the session.

Nothing the host does for the agent is reported back to it. The active view and the
selection are compared when the next request arrives, so switching away and back reports
nothing.

### Skills

The guidance agents read lives in markdown, not in the CLI, so it can change without a
rebuild:

- `pyrevitlib/pyrevit/agent/skills/INSTRUCTIONS.md` is the short entry text the MCP
  server sends on `initialize`. `{skills}` is replaced with the list of skills. Keep it last,
  and the text before it under 4,096 characters: Claude Code keeps only that much of a
  server's instructions, and `list_skills` gives back a list cut short.
- Each skill is a folder with a `SKILL.md` that starts with `name` and `description`
  front matter. PR 1 ships `revit-scripting`, the core contract for raw Revit API scripts.
  PR 2 adds domain guidance and library integration.

Agents read a skill with `get_skill(name)`, and other markdown files in its folder with
`get_skill(name, file)`. `list_skills` reports each skill's source and SHA-256 digest before
the agent reads it. The server loads only shipped skills by default. Enable user skills with
`pyrevit configs agent skills enable` to load folders from `%APPDATA%\pyRevit\agent\skills`.
Those folders are trusted-account guidance, not organizational policy: a same-name user skill
is ignored, and user guidance cannot replace shipped safety instructions or host enforcement.
Names, descriptions, files and paths are bounded and validated; reparse-point paths are ignored.

### Navigation links

`inspect_elements` returns an element `link` with a destination, document reference (its
`key`, title and path) and element ids. Pass that object to `navigate_revit_link` to select,
zoom to, isolate or temporarily hide the same elements. The Revit host checks that the link's
document is still open and is the active document immediately before presenting elements. If the document has closed or changed, it returns `stale_link`; activate the
intended document and inspect the elements again. Navigation only uses the fixed presentation
operation and never executes a command or changes model elements.

### Script contract

Scripts are Python, executed inside Revit by the regular pyRevit engines. The runner
injects `doc`, `uidoc`, `app`, `uiapp`, `DB` (`Autodesk.Revit.DB`), `UI`
(`Autodesk.Revit.UI`) and `inputs` (the `inputs` argument as a dict). `doc` is the document
the request names, active or not; `uidoc` is set only when that document is the active one,
and is `None` otherwise. Assign `result`
to return data. It is serialized to JSON:

- `ElementId` becomes an integer.
- `Element` becomes `{id, category, name, class}`.
- `XYZ` becomes `[x, y, z]`.
- .NET numbers become numbers, and collections become lists.

Printed output is captured and returned too.

```python
walls = DB.FilteredElementCollector(doc).OfClass(DB.Wall).WhereElementIsNotElementType()
result = {"count": walls.GetElementCount()}
```

In `run_modify`, the script opens its own transactions:

```python
t = DB.Transaction(doc, "Set comments")
t.Start()
for element_id in uidoc.Selection.GetElementIds():
    doc.GetElement(element_id).get_Parameter(
        DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS
    ).Set(inputs["text"])
t.Commit()
```

Rules the host enforces:

- A query that changes the model fails with `query_modified_model` and is rolled back.
- `run_modify` requires a document, and may change only the one it names. The run's approval
  prompt names the document, and isolates the changes in a view only when it is the active one.
- Background documents a run created or opened (no view in Revit, not linked, not open when
  the run started) are closed without saving when the run ends, whatever its outcome, and
  listed in `closed_documents`. The host blocks their save and save-as operations while a run is
  active.
  `get_context.open_documents` lists every open document and marks the background ones.
- While a run is active, the host cancels Revit operations exposed through cancellable save,
  save-as, synchronize-with-central, file-export and view-export events. The response lists a
  cancelled operation in `blocked`.
- A run in any mode that changes another open document is rolled back. When nothing else
  failed, it fails with `other_document_modified`. If a session is open, the run also pauses it
  (`paused_by_host`) until the user resumes it, whatever else failed. `changes.other_documents`
  lists what changed. A project the script opens
  or a family from a file during the run counts as one that was already open: changing it fails
  the run, it is rolled back, and it can't be saved or saved as, so the file on disk stays
  unchanged. A family from `EditFamily` or a new document the script creates has no file yet;
  it is reported there but doesn't fail the run, and isn't rolled back.
- A script error rolls back everything, and the traceback points at the script's own lines.
  Decorated functions, context-manager yields and rewritten exception handlers retain
  their original script line numbers, including on IronPython.
  When a Revit call throws, the message carries the underlying .NET exception and its
  inner exceptions (`[.NET: Autodesk.Revit.Exceptions.… <- …]`), not only the generic
  "A managed exception was thrown".
- When Revit rolls back one of the script's transactions because of an error-level
  failure, the run fails with `revit_failure`, even if the script itself didn't raise.
- A transaction left open fails the run with `transaction_left_open`.
- A script that runs past `timeout_s` (default 300 seconds, a finite number above 0, at
  most 3600) is stopped and fails with `timeout`. A watchdog thread flags the deadline, and
  the runner rewrites every loop header of the script (`for`, `while`, comprehensions) to
  check that flag on each iteration; only the header expressions change, so line numbers and
  tracebacks still match the submitted source. On CPython the watchdog also raises the
  timeout in the script thread. Library code the script calls (pyrevitlib, rpw, workspace
  modules) runs unguarded at full speed, so on IronPython a long loop inside such a call is
  only stopped once the call returns. A single blocking call, such as a long Revit API call
  or `time.sleep`, can't be interrupted either; the run fails with `timeout` once it returns.
  When that call was the script's last, the error says so and carries no traceback.
- The runner compiles the script with every bare `except` and `except BaseException`
  narrowed to `except Exception`, so a script can't swallow its own timeout, and can't catch
  `KeyboardInterrupt` or `SystemExit` that way. A script that suppresses the timeout some
  other way, such as through an alias, is stopped again at its next loop header. On
  CPython 3.12 and later, a run still going a second after its deadline is also stopped at
  the end of every loop iteration it reaches, which covers `async for` loops and code
  compiled at run time.
- To roll back a transaction the script leaves open, the runner rewrites every
  `<expr>.Start(...)` call in the script to `__agent_start__(<expr>).Start(...)`, which
  records the object if it is a Revit transaction before starting it. That finds a
  transaction however it was created or named, in a helper, after its variable is rebound,
  or when a timeout stops the script, so scripts that open transactions run at full speed.
  Only the object expression is wrapped, so line numbers still match the submitted source.
  The runner falls back to tracing the script's own frames line by line when the rewrite
  can't see every start: the run uses a `workspace`, compiles code at run time, or reaches
  `Start` another way (`getattr(t, "Start")`, `start = t.Start`). Other runs have no trace
  function, which on IronPython makes them many times faster, but also means nothing checks
  the deadline outside loop headers: unbounded recursion, or a callback passed to `map`,
  `filter` or `sorted` over an endless iterable, is not stopped on IronPython. A
  transaction a library function starts and returns to the script is only found if the
  script still holds it in a global when the run ends.
- Tracebacks of errors and timeouts show the script's frames and the library code it
  called, never the runner's own frames, so a timeout points at the script line that was
  running.
- Code the script compiles at run time (`exec`, `eval`, `execfile`, the `compile`
  builtin) can't have its loops rewritten, and neither can a loop inside an f-string on
  IronPython 3.4, which reads the whole f-string as one token. On IronPython such a run
  falls back to checking the deadline on every line of every frame, which is slower but
  still stops it, unless that code catches the timeout in its own loop.
- Revit dialogs are closed automatically and reported in `dialogs`. Warnings are removed
  and reported in `failures`, and errors roll back the failing transaction.
- Documents can't be saved or synchronized during a run.
  Closing is blocked for documents open when the run started.
  The script may close documents it creates or opens during the run.

The timeout, loop rewriting, handler narrowing, start recording and transaction tracing
above are skipped when [reckless mode](#reckless-mode) is on. Every other rule in this
section still applies.

The MCP server's instructions teach agents these conventions, plus units (internal
feet) and `ElementId.Value` on Revit 2024+.

### Reckless mode

Reckless mode runs agent scripts the way a pyRevit button runs its script: compiled as
submitted, with no trace function. It is for users who accept the risks below in exchange
for speed. A script that loops or calls into Python many times can run many times faster
on IronPython, where every traced line or checked loop header costs several microseconds
([#3815](https://github.com/pyrevitlabs/pyRevit/issues/3815)).

It is off by default. Turn it on or off with the CLI, or set `reckless = true` under
`[agent]` in the pyRevit config:

```shell
pyrevit configs agent reckless enable
pyrevit configs agent reckless disable
pyrevit configs agent reckless          # prints the current setting
```

The host reads the setting at the start of each run, so a change applies to the next run
without reloading pyRevit. A script can't turn it on for its own run. A reckless run's
response, its `response.json` record and the compact MCP result carry `"reckless": true`,
and `get_context` reports `agent.reckless: true` while it is on.

What a reckless run skips:

- The timeout. `timeout_s` is accepted but not enforced: no watchdog thread, no loop-header
  rewriting, no deadline checks, and no `timeout` error.
- Handler narrowing. Bare `except` and `except BaseException` stay as written.
- Transaction tracking. `.Start(` calls are not rewritten to record their transaction, and
  no `sys.settrace` function is installed, so transactions are not recorded while the
  script runs.

Risks:

- A runaway loop, or any script that never ends, blocks Revit until you end the Revit
  process from Task Manager. Unsaved work in every open document is lost.
- A transaction the script leaves open is still rolled back when it is held in a global
  variable, or in a list or dict held in one. A transaction left open inside a function,
  and not returned or stored globally, is not found, and Revit can crash later when that
  abandoned transaction is finalized.

What still applies: the `[agent] policy`, the approval prompt under `ask`, rollback of
queries and dry runs, rollback on any script error, the `transaction_left_open` check on the
active document, the document, save and dialog guards, and the run record.

### Which Python runs the script

Agents must not guess the language level. `get_context.scripting` reports it:

```json
"scripting": {
  "default_engine": "ironpython",
  "default_python": "3.4.2",
  "default_syntax": "Python 3.4 syntax plus f-strings, ...",
  "engines": {
    "ironpython": {"available": true, "implementation": "IronPython", "python": "3.4.2", "syntax": "..."},
    "cpython":    {"available": true, "implementation": "CPython",    "python": "3.12.3", "syntax": "..."}
  }
}
```

The IronPython entry follows the attached engine (IronPython 2.7.12 or 3.4.2). Scripts
run on `default_engine` (the `[agent] engine` setting) unless a run passes `engine`. Every
run response carries an `engine` field with the interpreter's own `sys.version`, which
confirms what actually executed.

`available` means a run on that engine can start. CPython loads its engine DLL from the
clone attached to the Revit version or, in a session pyRevit isn't attached to, from the
clone the session was loaded from. When that clone has no CPython engine, CPython is
`available: false` with an `unavailable_reason`, and a run that asks for it fails with
`engine_unavailable` before any code runs. `get_context.pyrevit`
reports `attached`, and `clone` and the IronPython `python` are null when the session
doesn't know them, instead of `Unknown` or `0`.

Syntax measured in Revit on IronPython 3.4.2:

| Syntax | IronPython 3.4.2 |
|---|---|
| f-strings, variable annotations, keyword-only arguments, `*`/`**` unpacking in literals | supported |
| walrus `:=`, `async`/`await`, `1_000` numeric literals, positional-only `/`, `match` | SyntaxError |

IronPython 2.7.12 is Python 2.7 syntax. CPython 3.12 supports everything, but reaches the
Revit API through pythonnet, and pyrevitlib features built for IronPython may be limited.

### CLI

```text
pyrevit agent status [--json]              running Revit sessions with the agent host
pyrevit agent context [--revit=<year>]     get_context of a session
pyrevit agent run <script_file> [--mode=query|dry_run|modify] [--engine=<e>]
                  [--title=<t>] [--inputs=<json>] [--revit=<year>]
                  [--timeout=<seconds>] [--workspace=<folder>]
                  [--document=<key>]       in the document with that key
                                           (default: the active document)
pyrevit agent runs [--limit=<n>]           recent runs
pyrevit agent show <run_id|req-id>           request, script and response of a run, by run id or request id
pyrevit agent session (status | pause | end) [--revit=<year>]
pyrevit agent session request [--reason=<reason>] [--revit=<year>]
                                           ask the user to start a session; the CLI
                                           can't start or resume one
pyrevit mcp [--revit=<year>]               the MCP server (stdio); started by MCP clients
pyrevit mcp (install | uninstall) (claude | codex | cursor | vscode | opencode) [--project]
pyrevit mcp uninstall --all [--owned]      every client's user-level entry; --owned keeps
                                           entries that point at another pyRevit install
```

`--timeout` defaults to 300 and is capped at 3600; [reckless mode](#reckless-mode) ignores it. `--workspace` must be an existing folder.

The `agent` and `mcp` commands ship with the pyRevit CLI of the same build. An older `pyrevit`
on `PATH` doesn't know them and prints the global usage; upgrade the CLI or call the one from
the build that provides the agent runtime.

### Run records

Every run is recorded under `%APPDATA%\pyRevit\agent\runs\<timestamp>-<run_id>\`:

- `script.py`: the submitted source
- `request.json`: title, reason, mode, engine and inputs, the session id and the active
  document's title
- `response.json`: status, decision, changes, failures, dialogs, output and result, with the
  same session id and document, and the document's path
- `result.json`: present when the result was too large to return inline

For runs that start, `response.json` (and `get_run`) also carries `timings_ms`, the run's
wall-clock breakdown in milliseconds. Host phases, in order: `queue_wait` (request parsed to
Revit main thread),
`prepare`, `guard_arm`, `engine` (the whole script engine call), `changes`, `decide`,
`approval` (only when the user was asked), `guard_release` (rollback or assimilation),
`cleanup` and `outcome`, plus `total`. The `script.*` phases the runner reports (`setup`,
`compile`, `exec`, `result`, `rollback`, `cleanup`) are nested in `engine`, so `engine` minus their sum is
engine startup and runner import. The same breakdown is logged as a `[PERF] agent run` debug
line.

Run records and `capture_view` images older than 14 days are deleted when the host starts.

### Testing agent skills and library changes through MCP

A change to a skill under `pyrevitlib/pyrevit/agent/skills` or to a pyrevitlib helper it describes
is best checked by running its snippets through the MCP server in a Revit that has your clone
attached (`pyrevit attach dev default --installed`, see the developer guide). The steps in between
are easy to get wrong:

1. **Rebuild only for C# changes.** C# files under `dev/` and the build pipeline under `build/`
   need a rebuild. Python under `pyrevitlib` or `dev/scripts` and the skill markdown don't.
2. **Close Revit, stop the MCP servers, then rebuild.** Revit loads pyRevit from the clone's `bin\`
   and keeps its DLLs open, and each client session runs `bin\pyrevit.exe mcp` from there too.
   A build started while either runs fails with "The process cannot access the file ... because it
   is being used by another process", for example on `pyRevitLabs.Language.dll` (Revit) or
   `Colorful.Console.dll` (a server). Servers of other client sessions count too.

    ```shell
    pwsh dev/scripts/Stop-McpServers.ps1
    cd build && dotnet run -c Debug -- ci
    ```

    `-WhatIf` lists the servers without stopping them. Clients start a new server on the next
    tool call, so don't call an MCP tool between the script and the build; afterwards the
    new server starts by itself, or the client needs a reconnect.
3. **Restart Revit after a build.** Accept the "Security - Unsigned Add-In" dialog with **Load Once**
   every time; the MCP host doesn't answer before that. Python-only changes need no rebuild, but
   they need a restart or reload to take effect: IronPython can `reload()` a changed module, while
   CPython can't redefine classes that implement .NET interfaces (reloading `pyrevit.revit.db.create`
   raises `Duplicate type name within an assembly`). Restarting Revit loads the edits on both engines.
4. **Repeat full test runs on the other IronPython.** The attached IronPython is one setting per
   clone: `ironpython` runs on 2.7.12 after `pyrevit attach <clone> default --installed` and on 3.4.2
   after `pyrevit attach <clone> 342 --installed`, while `cpython` is unaffected. The switch
   rewrites the `.addin` manifest, so the running Revit keeps its engine until it is restarted
   (and the **Load Once** dialog appears again). `get_context` and every run's `engine` field show
   the version in use. Run the full tests once per IronPython. Attach `default` again, restart Revit
   and accept **Load Once** before continuing.
5. **Run the snippets in scratch documents.** `run_query` rolls back changes to the active
   document, so code that edits a family or project opens its own with `app.NewFamilyDocument(template)`
   or `app.NewProjectDocument(DB.UnitSystem.Metric)` and closes it with `Close(False)` in `finally`.
   Roll back an open transaction on that document first: `Close` raises while one is open, and the
   error hides the original failure. Put back any user setting the snippet touched, such as
   `app.SharedParametersFilename`.

The [in-Revit agent tests](#in-revit-agent-tests) cover the shipped skills and the pyrevitlib side
of the automation operations on both engines.

## Design

### Architecture

```text
 Claude Code / Codex / Cursor / VS Code / OpenCode
            │  MCP over stdio
            ▼
 ┌──────────────────────────────┐   pyRevitCLI (net8, out of process)
 │ pyrevit mcp                  │   MCP protocol, tool schemas, instructions,
 │                              │   instance discovery, run records
 └──────────────┬───────────────┘
                │  named pipe  \\.\pipe\pyrevit-agent-<pid>  (current user only)
                ▼
 ┌──────────────────────────────┐   inside Revit (PyRevit.Runtime, Agent/)
 │ AgentHost                    │
 │  AgentSessions: session gate, AgentPanel: dockable pane + activity log
 │  AgentDispatcher ─► ExternalEvent
 │  AgentRunGuard: TransactionGroup, DocumentChanged diff,
 │                 save/sync/close blocking, dialog + failure capture
 │  approval + isolate preview, AgentScriptRunner, run records,
 │  AgentInspector, AgentApiLookup
 └──────────────┬───────────────┘
                ▼
     ScriptExecutor ─► IronPython / CPython ─► Revit API + pyrevitlib
```

Why two processes:

- **Dependency isolation**: MCP handling and its dependencies stay out of `revit.exe`.
  Assembly clashes with other add-ins are a real risk on .NET Framework 4.8.
- **Multi-instance routing**: the CLI finds every running host and routes each call to one.
- **Stability**: the agent keeps its connection to `pyrevit mcp` across Revit restarts.
- **Client support**: every MCP client supports stdio.

Why a named pipe: no TCP port, no firewall prompt, and nothing on the network. The pipe's
access list allows only the current Windows user and denies network logons, and that is
the authentication. The trust boundary is the Windows account: any process running as that
user can connect to the host and submit scripts.

The CLI also checks that the process serving the pipe is the Revit recorded in the instance
file, and refuses to send a request otherwise, so another local process can't take over a
pipe name while the host is down.

Remote use is through Remote Desktop only. An RDP session is an interactive logon, so
`pyrevit mcp` started inside it reaches Revit. SSH is refused on purpose: an SSH logon
carries the Network SID, so connecting fails with `UnauthorizedAccessException`, even
under the same account.

Discovery: each host writes `%APPDATA%\pyRevit\agent\instances\<pid>.json` with the pipe
name, the Revit version and the process id, and removes it when Revit exits.
Discovery excludes registrations and attempts to delete their files only when the recorded process is missing, its readable name is not `Revit` (case-insensitive), or its readable start time exceeds the registration timestamp by more than two seconds.
A matching process name and start time establish liveness without requiring an available pipe.
If process metadata or the registration timestamp cannot establish liveness, discovery checks for the recorded named pipe without connecting, up to three times at 300 ms intervals.
Any successful pipe check includes the registration in discovery.
If all pipe checks fail, discovery excludes the registration from the current result but retains its file for subsequent discovery.
The host recreates its pipe between connections and waits 500 ms after a pipe error; a temporarily absent pipe does not establish that the host has stopped.
Excluded registrations do not appear in `ambiguous_revit` messages.

### Existing pieces this builds on

| Piece | Where | Used for |
|---|---|---|
| Queued ExternalEvent dispatcher | `ShellExternalEventDispatcher` in `dev/pyRevitLabs.PyRevit.Shell/ShellLauncher.cs` | Pattern for the agent request queue (task-based wait, no spin) |
| Script execution | `ScriptExecutor`, `ScriptRuntimeConfigs.Variables` | Running agent scripts on the IronPython / CPython engines |
| Config accessors | `PyRevitConfigs` | `[agent]` settings, shared by the host and the CLI |
| Structured command results | `__result__` / `script.get_results()` | Returning command output to the agent (Phase 3) |
| Command lookup | `sessionmgr.execute_command()` | Running a command by unique id (Phase 3) |
| Bundle metadata | `ParsedBundle` (`pyRevitExtensionParser`) | Opt-in `agent:` block (Phase 3) |
| Batch runs | `pyrevit run --models=` | Multi-model agent jobs (Phase 5) |

Deliberately **not** reused:

- **Routes server** (`pyrevit.routes`): it has no authentication
  (`# TODO: auth` in `pyrevitcore_api.py`) and falls back to `0.0.0.0`.
  Code execution must never be exposed through it.
- **`ScriptExecutor.RequestExecuteScript`**: it spins on `IsPending` and uses a single
  handler slot that a concurrent request can overwrite. The agent host owns its own
  queue.

### Where the code lives

| Area | Contents |
|---|---|
| `dev/pyRevitLabs.PyRevit.Runtime/Agent/` | Host, dispatcher, pipe server, run guard, approval and isolate preview, script runner, inspector, API lookup; sessions, change awareness, and the agent panel with its activity log. It lives in the runtime so it can call `ScriptExecutor` directly; every per-year runtime build shares the source. The panel's view is XAML embedded in the runtime and loaded at run time, so the per-year builds need no WPF markup compilation. |
| `pyRevitCore` `pyRevit.panel/Agent Panel.smartbutton` | Opens the agent panel; hides itself while the host is disabled. |
| `pyRevitAssemblyBuilder` `SessionManagerService` | Starts, refreshes or stops the host on every `LoadSession` to match the config. |
| `pyrevitlib/pyrevit/agent/` | In-engine runner: executes the agent source, captures output, serializes `result`. Must stay parseable by IronPython 2.7, IronPython 3.4 and CPython 3. |
| `pyRevitLabs.PyRevit` `PyRevitConfigs` | `Get/SetAgentEnabled`, `Get/SetAgentPolicy`, `Get/SetAgentEngine`, `Get/SetAgentRequireSession`. |
| `pyRevitCLI` | `PyRevitAgentClient` (discovery and pipe protocol), `PyRevitCLIAgentCmds` (`agent`, `configs agent`, `mcp install` and `uninstall`), `PyRevitMcpServer` (`pyrevit mcp`). |
| `pyRevitDevTools` `Debug.panel/Agent Tests.pulldown` | In-Revit end-to-end tests that drive the host through `AgentHost.HandleRequest`. |
| `dev/pyRevitLabs/tests/pyRevitLabs.PyRevit.Runtime.Agent.Tests` | Unit tests of the run guard against Revit test doubles, and of the parts with no Revit dependency: sessions, the activity log, change awareness and the panel's view models; run in CI. |

### Pipe protocol

Newline-delimited JSON-RPC 2.0, one request per connection. Revit serves one connection
at a time and closes one that sends nothing for 30 seconds. Methods: `ping`,
`get_context`, `run`, `inspect_elements`, `show`, `capture`, `lookup_api`, and the session
requests `session_status`, `request_session`, `pause_session` and `end_session`.
`get_context` with `keep_changes` reports `since_last_call` without clearing it;
`run_automation` uses it before its run. `run`, `inspect_elements`, `show` and `capture` take a
`document` key and work in the active document without one. Errors
carry a stable `data.type`, such as `revit_busy`, `no_active_document`, `policy_readonly`,
`invalid_params` or one of the session refusals in
[Sessions and the agent panel](#sessions-and-the-agent-panel).

### What became of a request that got no answer

A client that gets `revit_busy`, or loses the connection, has to know whether its request ran
before it sends it again. Every request goes out under a request id (the CLI and MCP server
use `req-` and twelve hex digits as the JSON-RPC `id`), and a failure says what is known:

| `outcome` | Meaning | What to do |
|---|---|---|
| `not_sent` | The request never reached the host: nobody was listening, another client held the pipe, or the pipe belongs to another process. | Send it again. |
| `not_run` | The host refused the request before running any of it and discarded it. It is removed from the queue and never runs later. | Send it again once Revit is idle. |
| `unknown` | The request was sent and the answer was lost (the connection broke or closed). It may have run, may still be waiting to run, or may never run. | Look it up by request id before sending it again. |

Every `revit_busy` the host raises is a `not_run`. For a `run` request the host also leaves a
run folder with `status` and `decision` `not_run`, and returns its `run_id` and `run_dir` in the
error's `data`. Without it a refused request would leave no trace. A run that did start records
the request id in `request.json` and `response.json` (`request_id`), so a request can be found
either way:

```
pyrevit agent show req-0123456789ab
```

The MCP tool `get_run` accepts the same request id. Errors from the MCP server carry
`outcome`, `request_id` and, when the host recorded one, `run_id`. A request that is still
queued has no record yet, and one that never arrived has none at all. Only a pipe error after
sending, or an answer that cannot be read, leaves the outcome `unknown`.

A missing record does not prove that resending is safe. A request waits to start for
`start_timeout_s` (30 seconds by default, up to an hour for a client that sets it on the pipe) and
leaves no record until it starts or is refused, so it may still run. Look the request up again
after that wait has passed, and send it again only if there is still no record.

### The guarded run

Every run executes in one ExternalEvent callback on the Revit main thread:

1. **Arm guards** (only while the run is active):
    - `DocumentSynchronizingWithCentral`, `DocumentSaving` and `DocumentSavingAs` are cancelled for documents open when the run started and for documents the script creates or opens during the run, when Revit marks the event cancellable.
      `DocumentClosing` is cancelled only for documents open when the run started.
      The script may close documents it creates or opens during the run, but cannot save them.
      After the guard is disposed, the host closes any of these documents still open in the background without saving; documents with an open view are left open.
    - `DialogBoxShowing` is captured and dismissed.
    - `FailuresProcessing` warnings are recorded and deleted, and errors roll back the
      failing transaction, in every non-linked document. A failure in a family or a new
      document fails the run with `revit_failure` instead of raising a dialog.
    - `DocumentChanged` collects added, modified and deleted ids, per document.
2. **`TransactionGroup.Start("Agent: <title>")`** on the active document if it is writable, and on every other open, editable, non-linked document that has no transaction already open.
   Documents the script creates or opens during the run get no rollback group.
   Changes to documents opened from disk are discarded when they are closed without saving, not by rolling back a group.
3. **Run the script.** Its own transactions nest inside the group.
4. **Decide:**
    - **any mode**, another document open at the start or opened from disk during the run changed: roll back every group.
      The run fails with `other_document_modified` if the script completed successfully and left no transaction open.
      Only the active document's group is ever assimilated.
    - **query**: always roll back. A recorded change becomes a `query_modified_model` error.
    - **dry_run**: roll back and return the change set.
    - **modify** with policy `readonly`: the policy is read before the script and again here,
      and the stricter value (`readonly`, then `ask`, then `auto`) decides. A run queued before
      the switch to `readonly` rolls back with `policy_readonly` instead of committing, and a
      script that rewrites the policy can't loosen it for its own run.
    - **modify** with policy `auto`: `Assimilate()` straight away. The response says
      `approval: auto`.
    - **modify** with policy `ask`: while the group is still open, select and temporarily
      isolate the changed elements, and show the approval prompt. The isolation is switched off
      again inside the group before deciding. Keep → `Assimilate()`, one undo entry.
      Discard → `RollBack()`.
5. **Disarm guards** and write the run record.

The approval must happen inside the same callback, because Revit won't keep a
transaction group open after the callback returns. The benefit is that the human
approves inside Revit, and no agent tool can approve a run.

Honest limits:

- Rollback protects the model, not the file system or the network. There is no sandbox;
  `readonly` means query-only model access, not restricted Python execution.
- The guard covers the run itself, not code the run leaves behind. A script has the live
  Revit API, so it can subscribe to a Revit event such as `Idling`, or start a thread, that
  changes the model or answers the approval prompt after the guard has ended. Those changes
  are neither approved nor recorded. Approval and `readonly` stop an agent's mistakes, not a
  hostile script: connect only agents you trust, and don't feed them untrusted content.
- Revit serves one agent request at a time. While one session's run is executing, which can
  last until its `timeout_s`, a second agent session can't connect and gets `revit_busy`
  after the CLI's 10-second connect timeout. Keep runs short, and run one agent per Revit.
- ExternalEvents only fire while Revit is idle, so a busy Revit returns `revit_busy`
  after 30 seconds. The error names Revit's open windows and whether an earlier agent
  request is still running: a modal dialog Revit shows while idle, such as the save
  reminder, isn't part of any run and blocks every request until the user answers it.
  The refused request is discarded and never runs after the dialog closes; see
  [What became of a request that got no answer](#what-became-of-a-request-that-got-no-answer).
- A rollback must not touch committed work, but rolling back a dry run once undid the
  previous committed run as well (that run used `StairsEditScope`; Revit's journal logged
  `UndoElement::simplify PROBLEMS`). The host remembers a sample of the elements each
  committed run created and checks them after every rollback and before every run; a
  loss comes back as `warnings` in the run result.
- Revit regeneration inflates change sets: two new walls can report 100+ modified
  elements (rooms, tags, paths of travel, schedules). The MCP tools therefore return only
  counts, categories and the first added ids; the element list is in `get_run`. Phase 2
  will rank the elements the script touched ahead of these side effects.

### pyRevit commands as agent tools (Phase 3)

Commands will opt in through `bundle.yaml`:

```yaml
agent:
  expose: true
  mode: query
  description: Reports doors missing company-standard parameters.
  inputs:
    level:
      type: string
      description: Level name to limit the check to
      required: false
  returns: List of door ids with the missing parameter names
```

- `forms` prompts read `agent.inputs[key]`. When an input is missing they raise
  `InputRequired`, and the tool returns `needs_input` with the options so the agent
  can call again.
- Output-window markdown and tables become text. `__result__` and `agent.result()`
  become structured data.

## Phases

| Phase | Deliverable | Status |
|---|---|---|
| **0: Spike** | In-Revit host, pipe, guarded run, script runner, test client | Done on Revit 2024 (IronPython 3.4). CPython and Revit 2026 passes pending. |
| **1: MCP MVP** | `pyrevit mcp`, `pyrevit agent`, `pyrevit configs agent`, `mcp install`, `get_context`, `inspect_elements`, `lookup_revit_api`, `run_query`, `run_modify`, `get_run`, policy | In progress |
| **2: Writes** | Ranked change sets with before/after values, cancellation (`timeout_s` is done) | In progress |
| **3: Commands** | `agent:` bundle block, `list_commands` / `run_command`, forms agent mode | Planned |
| **4: Authoring** | `save_as_command` (promote a script to a ribbon button), shipped agent skill | Planned |
| **5: Scale** | `batch_run` across models, persistent script sessions | Planned |

## Open questions

- Model data leaves the machine through the LLM provider; an admin lock for the
  `[agent]` settings should be available.
- Whether the CPython engine is mature enough to be the default for agent scripts.
- How to relate to the third-party `mcp-server-for-revit-python` extension.
- Behaviour on workshared models with elements owned by other users.

## Phase 0 results

Validated on Revit 2024 (build 24.1.11.26), IronPython 3.4.2, Snowdon Towers sample:

| Check | Result |
|---|---|
| Pipe, ExternalEvent, main-thread queue | Works; warm runs take under 1 s |
| `DocumentChanged` inside a `TransactionGroup` | Fires for every inner commit, so query detection and change sets work |
| Query and dry-run rollback | Verified in the model afterwards |
| Warning capture | Overlap warning recorded and removed, no popup |
| Dialog capture | API `TaskDialog` dismissed and reported. `DialogBoxShowing` fires for API dialogs too, so the host disarms it before its own prompt. |
| Save blocking | Revit itself refuses to save while an API transaction group is open; the `DocumentSaving` cancel covers runs without a group |
| Script error | Rolled back, traceback points at the script line |
| Transaction left open | Detected; Revit cleans up the open transaction |
| Modify, Keep / Discard | Committed or rolled back as chosen, verified in the model |
| Isolate preview | View isolation cleared after the prompt |

### In-Revit agent tests

The pyRevitDevTools extension has an **Agent Tests** pulldown under *pyRevitDev > Debug*. Its buttons
drive the host from inside Revit through `AgentHost.HandleRequest`, which runs the same JSON-RPC
requests the pipe carries synchronously on the Revit main thread. A command can't use the pipe
itself: the pipe executes requests through an ExternalEvent that never fires while a command runs.

| Button | Covers |
|---|---|
| Run Agent Tests | `get_context`, `inspect_elements`, `show`, `capture`, `lookup_api`; what each request refuses (invalid parameters, unsupported or closed views); query runs on both engines (results, error lines, timeouts, workspaces, records, dismissed dialogs); modify runs (decisions, change sets, rollback, open transactions, save and export blocks, other documents, warnings, `readonly`, a policy changed during the run or outside Revit); the agent settings; sessions (start, pause, end, requests, the wrong document, moves, closing documents); change awareness; the agent panel (pane, log, refused runs, closing it pauses the session); the real named pipe (`ping`, `lookup_api`, errors, `revit_busy` while a command runs) |
| Run Agent Tests (CPython) | The same tests started from a CPython command, which also checks that the command survives nested agent runs |
| Run Agent Library Tests | The shipped and user skills, `lookup_pyrevit_api` and `list_automation` through a short-lived `pyrevit mcp` process, and the pyrevitlib side of the automation operations on both engines |
| Run Agent Approval Tests | The `ask` prompt's *Keep* and *Discard*, answered through Revit's `DialogBoxShowing` event; if a prompt stays on screen, click the button its title names |

The tests create two scratch projects in the temp folder, require sessions and start one on the
scratch project, and set the policy to `auto` (or `ask` for the approval tests) while they run.
Then they end their session, close the projects without saving, reactivate the document that was
open before, and restore the policy and the session setting. They refuse to start while an agent
session is open, so end yours in the panel first. The settings tests change the real pyRevit config and
put every value back. The pipe tests are skipped when the host is disabled, and the other tests have
only been run with it enabled.
Each test is written to `%TEMP%\pyrevit-agent-tests.log` before it starts, so if Revit ever hangs, the
last line of that file names the test that was running.

`run_automation`, `navigate_revit_link` and the hints the MCP server adds to run errors call back
into Revit through the pipe, which can't answer while a command runs, so these buttons don't cover them.
