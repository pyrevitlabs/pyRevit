# Agent runtime

!!! warning "Status: experimental"

    The agent runtime is experimental and off by default. Enable it with
    `pyrevit configs agent enable` (see [Getting started](#getting-started)). The setting is stored in the
    clone's own config when it has one, otherwise in the shared user config. A clone without its own config
    therefore shares the setting with every other clone that reads the user config.

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

2. **Start Revit** (or reload pyRevit), and open a model.
3. **Check the connection:**

    ```shell
    pyrevit agent status
    ```

4. **Ask your agent about the model**, for example *"How many doors on Level 2 have no
   Mark?"* or *"Set the Comments of the selected walls to 'Check fire rating'"*. Changes
   show an approval prompt in Revit, with the changed elements selected and temporarily
   isolated in the active view. *Keep* commits them as one undo entry named
   `Agent: <title>`; *Discard* rolls them back.

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
| `[agent] enabled` | `pyrevit configs agent (enable \| disable)` | Starts the in-Revit host on the next pyRevit load. Default `false`. Disabling also refuses every later request with `agent_disabled` at once. The host never starts in a Revit running as administrator. |
| `[agent] policy` | `pyrevit configs agent policy (readonly \| ask \| auto)` | `readonly`: queries and dry runs only; it does not sandbox Python or prevent file, network, or process side effects. `ask` (default): each modify run needs approval in Revit. `auto`: modify runs are committed without the prompt; each is still one undo entry, guarded and recorded. A stricter policy applies at the next request. A looser one applies only after you confirm it in a Revit prompt before the next modify run; No keeps the stricter one until Revit restarts. |
| `[agent] engine` | `pyrevit configs agent engine (ironpython \| cpython)` | Engine for runs that don't name one. Default `ironpython` (the attached IronPython). |
| `[agent] reckless` | `pyrevit configs agent reckless (enable \| disable)` | Default `false`. `true` runs scripts without the runner's in-script checks: no timeout and no transaction tracking. Turning it on needs your confirmation in Revit, like a looser policy. See [Reckless mode](#reckless-mode) for the risks. |

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
Three consecutive visual failures disable highlighting until pyRevit is reloaded and produce one log entry without changing a run's outcome.

### MCP tools

| Tool | Changes the model | Purpose |
|---|---|---|
| `get_skill` | no | Task guidance in markdown (see [Skills](#skills)); the server's instructions tell agents which skill to read first |
| `list_skills` | no | The available skills with their source and SHA-256 digest (see [Skills](#skills)) |
| `list_revit_instances` | no | Running Revit sessions with the agent host |
| `get_context` | no | Revit and pyRevit versions, agent policy (and `reckless: true` when [reckless mode](#reckless-mode) is on), `scripting` (engine and Python version scripts run on), document, `open_documents`, active view, selection, levels |
| `inspect_elements` | no | Class, category, type, level, location, bounding box and parameters of up to 50 elements; a repeated id is described once |
| `lookup_revit_api` | no | Signatures of a Revit API type or member (`name`, up to 256 characters), reflected from the running Revit. Also its namespace and Python import line, and a `creation` list: static factories and the `doc.Create.New…` methods that return the type. A missing member returns `found: false` with the closest names, including matching values of other enums. Takes `name`, or `query` as an alias to match `lookup_pyrevit_api` |
| `show_elements` | no | Select, zoom to, or temporarily isolate / hide elements (by id or category) in the active view, or reset the temporary mode. Up to 20000 integer ids and 100 distinct categories (a repeated category counts once), and the categories may match at most 20000 elements (`too_many_elements` otherwise); an id with no element is listed in `missing_ids`. No approval prompt. If Revit can't zoom, the response has `zoomed: false` and a `zoom_failed` error instead of a dialog blocking Revit. `isolate` and `hide` leave out ids the active view doesn't show and list them in `not_in_view_ids`; `select` lists them there too but still selects them, so `zoom` can open a view that shows them; while a temporary isolate is on, the elements it hides count as not shown, so `reset` before isolating others. `view` is the view acted on; when zooming makes Revit open another view, `active_view` names it. |
| `navigate_revit_link` | no | Select, zoom to, isolate or temporarily hide the elements of a `link` returned by `inspect_elements` (see [Navigation links](#navigation-links)) |
| `capture_view` | no | PNG of a view for visual checks. `export` renders any view through Revit, named by name, id or sheet number, and a schedule on a temporary sheet that is rolled back (a schedule rejects `detail_level` and `display_style` with `view_not_supported`, and so does one filtered by sheet on Revit 2023 and later, which would render empty there; Revit 2021 and 2022 can't report it); `viewport` renders an open view through Revit cropped to what its window shows now (zoom, pan, temporary isolate; no selection highlight), in a rolled-back transaction; `screen` captures the active view window as the user sees it (selection, temporary isolate), fails with `view_not_active` for any other view, and fails with `view_obscured` when another application's window covers any part of it (click-through overlays such as the GeForce overlay don't count); view `3d` renders a temporary 3D view of model categories only, framed by a section box around the model (or `elements`, up to 20000 integer ids) and seen from `direction`, which is rolled back. `eye` and `target` (feet) switch it to a perspective camera without a section box; `section` (`origin`, `normal`, optional `depth`) renders a temporary section or elevation for a horizontal `normal`, or a plan cut at `origin` height for `[0, 0, -1]`, framed on `elements` or the model; ids in `elements` that don't exist are listed in `missing_ids`, also on an error. `detail_level` (`coarse`, `medium`, `fine`) and `display_style` (`wireframe`, `hidden_line`, `shaded`, `shaded_edges`) apply to the temporary view and, in `export` and `viewport` modes, to a named view for that capture only, inside the same rolled-back group (a view template that controls them is detached there; in a workshared model a view you don't own is duplicated and the copy is changed, so nothing is borrowed; `viewport` refuses such a view while its temporary hide/isolate is on). A view name shared by several views fails with `view_ambiguous` and lists their ids, except in `screen` mode when one of them is the active view; a digits-only selector is tried as an id first, then as a name. Saved under `%APPDATA%\pyRevit\agent\captures`. |
| `run_query` | never | Run a read-only script; model changes are always rolled back, but the script itself has full access to the machine, so the tool isn't marked read-only for MCP clients. `workspace` puts a folder of the agent's own modules on `sys.path`, re-imported fresh every run. `timeout_s` (default 300) stops a script that runs too long. `document` (title or path from `get_context`) refuses the run with `document_changed` when another document is active. |
| `run_modify` | after approval | Run a changing script against the active document; it is refused when no document is active. `dry_run=true` previews the change set and rolls back. `document` (title or path from `get_context`) refuses the run with `document_changed` when another document is active. |
| `get_run` | no | A recorded run: response, script, and pages of a large result |
| `lookup_pyrevit_api` | no | Signature, docstring and import line of a pyrevitlib or rpw function, a module listing, or a search by words. Works without Revit |
| `list_automation` | no | The marked pyrevitlib and rpw operations (see [Automation operations](#automation-operations)), with `invocable` and the `inputs` each takes. Works without Revit |
| `run_automation` | never | Run an invocable operation by id with a JSON input object. Runs as a query, so changes are rolled back; it accepts no Python source. `document` (title or path from `get_context`) refuses the run with `document_changed` when another document is active. |

`run_query`, `run_modify` and `run_automation` accept an optional `document`: the title or path of the document
as returned by `get_context`. When it is given and the active document differs, Revit refuses the run with
`document_changed` before anything runs (a `not_run` request, see
[What became of a request that got no answer](#what-became-of-a-request-that-got-no-answer)), so a plan made for
one model never lands in another after the user switches tabs. A value with a path separator is compared, normalised
and ignoring case, with the active document's path only; any other value is compared with its title only, so pass
the path when two open documents share a title. A blank value, or one that is neither a string nor `null`, is `invalid_params`. Omitting
`document`, or passing `null`, leaves the run unbound. The approval prompt always names the document the changes apply to.

Every request that runs on Revit's main thread closes the dialogs Revit opens during it and
reports them in `dialogs`, so a dialog can't leave the call hanging.

Only agent-written code needs approval. `show_elements` is a fixed host operation that
changes presentation, never model elements. Temporary hide/isolate runs in its own small
transaction because the Revit API requires one, and that state isn't saved with the
model. The agent is told to use it rather than writing `run_modify` scripts to show
things. Because they change view state or write files, `show_elements`,
`navigate_revit_link` and `capture_view` are annotated for MCP clients as neither
read-only nor destructive.

`run_query` and `run_modify` return a compact result for the agent: `status`, then
`error` (when present), `decision`, `result`, `output`, and only the non-empty change
set, failures, dialogs and blocked operations. The change set starts with `summary`, one
line the host builds from every change, for example `added 1 family (Door) with 3 types and 2
other elements (Legend Components), modified 1 element (Project Information), deleted 1
element`: it names up to 3 families and the 3 most frequent categories, then `+N more`, and
reads `no changes` for an empty set. It then keeps counts, `by_category`,
`added_ids`, `added_families` (id, category, name and class of every added family and
type, system types included), `modified` (the same fields) and `deleted_ids`, each
capped at 20 entries. The full record, with up to 50 of each, stays available through
`get_run`. `AttributeError` and `TypeError` failures carry a `hint` that names the
`lookup_revit_api` call to make, for example `'Collector' does not exist in
Autodesk.Revit.DB` or `check the overloads of 'FilteredElementCollector.OfCategory'`.

If the host cannot persist a result or run record, the response keeps the final model decision
and adds a warning. The corresponding `get_run` record can be incomplete or unavailable.

Every tool that talks to Revit accepts an optional `revit` argument (a year such as
`"2024"`, or a process id) for when several Revit sessions run. `pyrevit mcp --revit=<year>`
sets a default, which an empty or `null` `revit` also uses. Its schema lists `null` as a type.

The MCP server sends one call at a time to each Revit, since Revit runs one request at a time
(and a host older than the multi-connection pipe server accepts one connection at a time); calls to
different Revit sessions don't wait for each other. `list_revit_instances` doesn't
wait for calls in progress: it pings every Revit at once, and reports `busy: true` for one that
still has a call from this server open, or that doesn't accept the ping within 1.5 seconds because
other clients (such as `pyrevit agent run`) hold all its connections. The host answers a ping on its
pipe thread, so a Revit that is only running another client's request still answers it. A Revit whose pipe is not listening, or that gets no answer within
5 seconds, reports `responding: false` (`pyrevit agent status` uses the same ping, prints `busy` for a Revit that is only serving another client, and shows each session's clone and engine). A client's `notifications/cancelled` frees the call's
turn. A call cancelled while it waited for its turn was not sent; one cancelled while waiting for
Revit's answer keeps running in Revit, so its outcome is `unknown`. The server sends no response to a cancelled `tools/call`, as the MCP specification asks; the server does not reveal its own request id (it is not the MCP call id), so look for a run record with `pyrevit agent runs` (newest first) and open it with `pyrevit agent show <run_id>`. A call cancelled before it was sent, or while it still waited for an earlier call, left no run record.

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
`integer`, `boolean`, `element` (an element id, resolved in the active document) and `scalar`
(a string, number or boolean). `inputs=()` declares an operation that takes no inputs. A
function with a `doc` parameter gets the active document. List results keep their first 200
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

### Skills

The guidance agents read lives in markdown, not in the CLI, so it can change without a
rebuild:

- `pyrevitlib/pyrevit/agent/skills/INSTRUCTIONS.md` is the short entry text the MCP
  server sends on `initialize`. `{skills}` is replaced with the list of skills.
- Each skill is a folder with a `SKILL.md` that starts with `name` and `description`
  front matter. The shipped skills are `revit-scripting` (the core contract for raw Revit API
  scripts), `pyrevit-library`, `modeling`, `drawings`, `views`, `scheduling`, `family-editing`,
  `family-geometry`, `revit-files` and `extension-authoring`.

Agents read a skill with `get_skill(name)`, and other markdown files in its folder with
`get_skill(name, file)`. `list_skills` reports each skill's source and SHA-256 digest before
the agent reads it. The server loads only shipped skills by default. Enable user skills with
`pyrevit configs agent skills enable` to load folders from `%APPDATA%\pyRevit\agent\skills`.
Those folders are trusted-account guidance, not organizational policy: a same-name user skill
is ignored, and user guidance cannot replace shipped safety instructions or host enforcement.
Names, descriptions, files and paths are bounded and validated; reparse-point paths are ignored.

### Navigation links

`inspect_elements` returns an element `link` with a destination, document reference and element
ids. Pass that object to `navigate_revit_link` to select, zoom to, isolate or temporarily hide
the same elements. The Revit host compares its active document with the link immediately before
presenting elements. If the document has closed or changed, it returns `stale_link`; activate the
intended document and inspect the elements again. Navigation only uses the fixed presentation
operation and never executes a command or changes model elements.

### Script contract

Scripts are Python, executed inside Revit by the regular pyRevit engines. The runner
injects `doc`, `uidoc`, `app`, `uiapp`, `DB` (`Autodesk.Revit.DB`), `UI`
(`Autodesk.Revit.UI`) and `inputs` (the `inputs` argument as a dict). Assign `result`
to return data. It is serialized to JSON:

- `ElementId` becomes an integer.
- `Element` becomes `{id, category, name, class}`.
- `XYZ` becomes `[x, y, z]`.
- .NET numbers become numbers, and collections become lists.
- `bytearray` values, and `bytes` on CPython and IronPython 3, become text, decoded as UTF-8. On
  IronPython 2.7 `bytes` is `str` and stays as it is. Dictionary keys must already be text or
  numbers.

Printed output is captured and returned too, up to its first 64 KB (`output_truncated: true`
when there was more; the rest is dropped while the script prints). The cap counts every
character ever written, so `truncate(0)` or `seek` does not make room for more.

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
- A run started from inside another run (through `AgentHost.HandleRequest`) is refused with
  `nested_run`, or with `nested_cpython` when a CPython run is started from a CPython script.
- `run_modify` requires an active document and is refused before the script runs when none is
  active. The other tools (`capture_view`, `inspect_elements`, `show_elements`) also require an
  active document.
- Background documents a run created or opened (no view in Revit, not linked, not open when
  the run started) are closed without saving when the run ends, whatever its outcome, and
  listed in `closed_documents`. The host blocks their save and save-as operations while a run is
  active.
  `get_context.open_documents` lists every open document and marks the background ones.
- While a run is active, the host cancels Revit operations exposed through cancellable save,
  save-as, synchronize-with-central, file-export, view-export and printing events. The response
  lists a cancelled operation in `blocked`. APIs that write files without raising one of these
  events, such as `ViewSchedule.Export`, shared parameter file edits and
  `TransmissionData.WriteTransmissionData`, are not blocked.
- A run in any mode that changes another open document fails with `other_document_modified`
  and is rolled back. `changes.other_documents` lists what changed. A project the script opens
  or a family from a file during the run counts as one that was already open: changing it fails
  the run, it is rolled back, and it can't be saved or saved as, so the file on disk stays
  unchanged. A family from `EditFamily` or a new document the script creates has no file yet;
  it is reported there with a `scope` statement and without a `rolled_back` field, doesn't fail
  the run, and isn't rolled back; it is discarded when closed.
- When `blocked` isn't empty, `warnings` gains an `operation_blocked` entry
  naming each cancelled operation, because the script itself only sees Revit's generic
  exception.
- A script error rolls back everything, and the traceback points at the script's own lines.
  Decorated functions, context-manager yields and rewritten exception handlers retain
  their original script line numbers, including on IronPython.
  When a Revit call throws, the message carries the underlying .NET exception and its
  inner exceptions (`[.NET: Autodesk.Revit.Exceptions.… <- …]`), not only the generic
  "A managed exception was thrown".
- When Revit rolls back one of the script's transactions because of an error-level
  failure, the run fails with `revit_failure`, even if the script itself didn't raise.
- A transaction left open fails the run with `transaction_left_open`.
- A failure in the host itself reports `host_error` with decision `rolled_back`, or
  `not_run` when it failed before the script started (for example when Revit refused to start
  the run's transaction group, or the script engine failed to start), or
  `committed` when the change set had already been kept, or `rollback_incomplete` when the
  run's rollback failed, or left the model different from before the run (an element the
  run deleted is still missing, or one it added is still there), so its changes may remain
  in the active document. A script engine that reports a failure (`engine_error`) before the
  script's first statement ran is `not_run` too.
- A script that runs past `timeout_s` (default 300 seconds, a finite number above 0, at
  most 3600) is stopped and fails with `timeout`. A watchdog thread flags the deadline, and
  the runner rewrites every loop header of the script (`for`, `while`, comprehensions) to
  check that flag on each iteration; only the header expressions change, so line numbers and
  tracebacks still match the submitted source. On CPython the watchdog also raises the
  timeout in the script thread. Modules imported from the run's `workspace` folder get the same rewrite
  through an import hook that exists only for the run (regular modules and
  packages that `sys.path` order resolves to the workspace; namespace packages are not rewritten). Library code the script calls
  (pyrevitlib, rpw) runs unguarded at full speed, so on IronPython a long loop inside such a
  call is only stopped once the call returns. A single blocking call, such as a long Revit API call,
  `time.sleep`, .NET `Thread.Sleep`, or a printer or window waiting for input, can't be
  interrupted on any engine; the run fails with `timeout` once it returns, and returns no
  `result`. When that call was the script's last, or the limit passed while the runner was
  converting `result`, the error carries no traceback and gives the same message for both cases:
  the run was inside a call that could not be interrupted. If such a call is still
  blocking 30 seconds after the deadline, the request fails with `run_hung` (outcome
  `unknown`, plus the run's `run_id` and `request_id`) so the caller stops waiting. The run
  itself keeps Revit busy until the call returns, then ends and is recorded as usual with
  that `timeout`, so look it up with `get_run` before sending it again; meanwhile later
  requests fail with `revit_busy`, and the message says an earlier run is stuck past its
  time limit. Time spent waiting for approval doesn't count.
- The runner compiles the script with every bare `except` and `except BaseException`
  (also spelled as an attribute, such as `except builtins.BaseException`) narrowed to
  `except Exception`, so a script can't swallow its own timeout, and can't catch
  `KeyboardInterrupt` or `SystemExit` that way. If a handler can't be rewritten in the
  source, the run compiles the narrowed syntax tree instead, at the cost of line numbers,
  rather than keep the broad handler. A script that suppresses the timeout some
  other way, such as through an alias, `except tuple(...)`, a library's bare `except`, or
  `sys.settrace(None)`, is stopped again at its next loop header. On
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
  the deadline outside loop headers: a callback passed to `map`, `filter` or `sorted` over
  an endless iterable is not stopped on IronPython. Unbounded recursion ends in a
  `RecursionError`; see [Deep recursion on IronPython](#deep-recursion-on-ironpython). A
  transaction a library function starts and returns to the script is only found if the
  script still holds it in a global when the run ends.
- Tracebacks of errors and timeouts show the script's frames and the library code it
  called, never the runner's own frames, so a timeout points at the script line that was
  running.
- Code the script compiles at run time (`exec`, `eval`, `execfile`, the `compile`
  builtin) can't have its loops rewritten, and neither can a loop inside an f-string on
  IronPython 3.4, which reads the whole f-string as one token. On IronPython such a run
  falls back to checking the deadline on every line of every frame, which is slower but
  still stops it, unless that code catches the timeout in its own loop, or the script
  removes that check with `sys.settrace(None)` first. Importing such a module from the
  `workspace` turns that check on for the rest of the run. `async for` loops are not
  rewritten either; only CPython can run them, and it stops them as described above.
- Threads the script starts are not stopped. They keep running after the run returns, with
  no timeout, outside the guard (see the limits under [The guarded run](#the-guarded-run)).
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
on IronPython, where every traced line or checked loop header costs several microseconds.

It is off by default. Turn it on or off with the CLI, or set `reckless = true` under
`[agent]` in the pyRevit config:

```shell
pyrevit configs agent reckless enable
pyrevit configs agent reckless disable
pyrevit configs agent reckless          # prints the current setting
```

The host reads the setting at the start of each run, so a change applies to the next run
without reloading pyRevit. Turning it off applies at once. Turning it on applies only after
you confirm it in a Revit prompt before the next run of any mode, so a script that rewrites
the config can't make later runs reckless; No keeps it off until the setting is turned off
and on again or Revit restarts. A script can't turn it on for its own run. A reckless run's
response, its `response.json` record and the compact MCP result carry `"reckless": true`,
and `get_context` reports `agent.reckless: true` while it is in force.

What a reckless run skips:

- The timeout. `timeout_s` is accepted but not enforced: no watchdog thread, no loop-header
  rewriting, no deadline checks, no `timeout` error, and no `run_hung`: a call that blocks
  keeps the caller waiting until it returns.
- Handler narrowing. Bare `except` and `except BaseException` stay as written.
- Transaction tracking. `.Start(` calls are not rewritten to record their transaction, and
  no `sys.settrace` function is installed, so transactions are not recorded while the
  script runs.

Risks:

- A runaway loop, or any script that never ends, blocks Revit until you end the Revit
  process from Task Manager. Unsaved work in every open document is lost.
- A transaction the script leaves open is still rolled back when it is held in a global
  variable, in a list or dict held in one, or in an attribute of an object held in one
  (such as `pyrevit.revit.Transaction`). A transaction left open inside a function,
  and not returned or stored globally, is not found, and Revit can crash later when that
  abandoned transaction is finalized.

What still applies: the `[agent] policy`, the approval prompt under `ask`, rollback of
queries and dry runs, rollback on any script error, the `transaction_left_open` check on the
active document, the document, save and dialog guards, and the run record.

### Deep recursion on IronPython

Scripts run on Revit's main thread, whose stack is 1 MB. Unbounded recursion stops at the
engine's limit of 1000 calls with `RecursionError` (`RuntimeError` on IronPython 2.7) like
any other script error, and an exception raised deep in a call chain is caught as usual.

Upstream IronPython rethrows an exception once per Python frame from inside a `catch` block,
which on .NET holds about 12 KB of stack per frame until the exception is caught, so an
exception raised about 100 calls deep crashed Revit. It also stopped checking the recursion
limit in a function that had raised more than 20 times. pyRevit ships both engines with
fixes for this:

- IronPython 2.7.12 is built from the `dev/modules` forks.
- IronPython 3.4.2 uses patched `IronPython.dll` and `Microsoft.Dynamic.dll` drop-ins with
  the upstream version and identity; see `dev/libs/IronPython/IPY342/README.md` for their
  sources.

The fixes have not been released upstream, so other hosts running IronPython still crash.

A trace function makes every IronPython frame larger. While the runner traces a script (it
uses a `workspace`, compiles code at run time, or reaches `Start` other than by a direct
call; see [Script contract](#script-contract)), an IronPython run's recursion limit is 500
instead of 1000, because frames with several `with` or `try` blocks overflow Revit's stack
between 750 and 900 calls when traced. A script that raises its limit is put back to 500 on
its next call, and the previous limit is restored when the script ends. CPython runs keep
their limit. The cap lives in the runner's trace function, so a script that removes it with
`sys.settrace(None)` and then raises its own limit is no longer held at 500; handler-dense
recursion past about 750 calls can then still crash Revit.

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

### Engine warm-up

Agent runs reuse one cached engine per session load, so only the first run starts the engine,
imports `pyrevit.agent._runner` and runs the runner's code for the first time, which costs
two to three seconds on IronPython. The host does that work ahead of time, once per session
load, when an agent first makes contact: after the pipe handles the first request of the
load (`ping`, `get_context` or any other method), it queues the warm-up on the Revit main
thread, where it runs when Revit is next idle. A session whose agent never connects pays
nothing.

The warm-up uses the same engine cache key and flags as a real run, and calls
`_runner.warm_up()`, which passes a small fixed script through the real `run()` against a
stand-in context with no Revit application: setup, source rewriting, compilation, loop
guards, the watchdog, execution, transaction recording, result serialization and the
rollback scan all run once. It reads no document, starts no transaction, writes no run
record and shows no output. Its two-line entry script goes to a file of the Revit process's
own, `%APPDATA%\pyRevit\agent\engine_warmup.<pid>.py`, which is deleted after it ran, so
Revit sessions warming at the same time never share it. A `run` request never queues it: a
run that executes starts the engine anyway, and one refused before it executes leaves the
next request to warm. The
warm-up is skipped when the engine is already cached, when the agent is off, and when
`default_engine` is not IronPython. A request during which pyRevit reloads, such as a
`run` that reloads it, counts for the old load, so the new load warms on its own first
request. Requests made in-process through `AgentHost.HandleRequest` don't trigger it. The
warm-up reports to the debug log only, as a `[PERF] agent engine warm-up` line with the
script's exit code, or as `Agent engine warm-up failed`, and never affects the host.

A request that arrives while the warm-up runs waits for it, as it would for a run. A run
sent right after the first `ping` therefore takes about 0.1 to 0.4 s longer than a cold first
run would have, because it waits for the whole warm-up, which does a little more than a run
needs. This is accepted: a run sent after the warm-up finishes starts in tens of
milliseconds instead of two to three seconds.

CPython is not warmed: pythonnet's first initialize is heavy, scans every loaded assembly and
keeps the interpreter up for the rest of the process, so the first CPython run still pays for
it. A run that asks for an engine other than the default also starts cold.

### CLI

```text
pyrevit agent status [--json]              running Revit sessions with the agent host
pyrevit agent context [--revit=<year>]     get_context of a session
pyrevit agent run <script_file> [--mode=query|dry_run|modify] [--engine=<e>]
                  [--title=<t>] [--inputs=<json>] [--revit=<year>]
                  [--timeout=<seconds>] [--workspace=<folder>]
pyrevit agent runs [--limit=<n>]           recent runs
pyrevit agent show <run_id|req-id>           request, script and response of a run, by run id or request id
pyrevit mcp [--revit=<year>]               the MCP server (stdio); started by MCP clients
pyrevit mcp (install | uninstall) (claude | codex | cursor | vscode | opencode) [--project]
pyrevit mcp uninstall --all [--owned]      every client's user-level entry; --owned keeps
                                           entries that point at another pyRevit install
```

`--timeout` defaults to 300 and is capped at 3600; [reckless mode](#reckless-mode) ignores it.
`--workspace` must be an existing local folder; network (UNC) paths are refused.

The `agent` and `mcp` commands ship with the pyRevit CLI of the same build. An older `pyrevit`
on `PATH` doesn't know them and prints the global usage; upgrade the CLI or call the one from
the build that provides the agent runtime. If that still happens after an upgrade, another
install comes first on `PATH`: `where.exe pyrevit` in a new terminal lists every `pyrevit.exe` in the
order Windows resolves them (`pyrevit env path which` does the same on a CLI that has it), and
the first one is the one that runs. Update or uninstall that install.

### Run records

Every run is recorded under `%APPDATA%\pyRevit\agent\runs\<timestamp>-<run_id>\`:

- `script.py`: the submitted source
- `request.json`: title, mode, engine and inputs
- `response.json`: status, decision, changes, failures, dialogs, output and result
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

Run records and `capture_view` images older than 14 days are deleted when the host starts, and
again at most once a day when a run is recorded.

### Testing agent skills and library changes through MCP

A change to a skill under `pyrevitlib/pyrevit/agent/skills` or to a pyrevitlib helper it describes
is best checked by running its snippets through the MCP server in a Revit started from your clone
or git worktree with `pyrevit launch <clone> <engine> <year>`. A launch uses a manifest of its own
and leaves the attachment alone; run it as a background process, since it stays up while that Revit
runs. Details are in [Running several clones side by side](#running-several-clones-side-by-side).
`pyrevit attach dev default --installed` still works for a single session, but it rewrites the shared
per-year `pyRevit.addin` that the next plain Revit start loads. The steps in between are easy to get
wrong:

1. **Rebuild only for C# changes.** C# files under `dev/` and the build pipeline under `build/`
   need a rebuild. Python under `pyrevitlib` or `dev/scripts` and the skill markdown don't.
2. **Close Revit, stop the MCP servers, then rebuild.** Revit loads pyRevit from the clone's `bin\`
   and keeps its DLLs open, and each client session runs `bin\pyrevit.exe mcp` from there too.
   A build started while either runs fails with "The process cannot access the file ... because it
   is being used by another process", for example on `pyRevitLabs.Language.dll` (Revit) or
   `Colorful.Console.dll` (a server). Servers of other client sessions count too.

    ```shell
    pwsh dev/scripts/Stop-McpServers.ps1
    cd build
    dotnet run -c Debug -- --trust-cert
    dotnet run -c Debug -- local
    ```

    `--trust-cert` is needed once per Windows user and again after the certificate is renewed (about
    a year after it was created, within 30 days of expiry): `local` refuses to start until the developer
    certificate is trusted, and Windows asks you to confirm the new root, see `build/README.md`.
    `local` runs `ci` and then signs `bin\` with that certificate, so Revit loads the build without
    the unsigned add-in dialog. A plain `ci` build is unsigned.

    `-WhatIf` lists the servers without stopping them. Clients start a new server on the next
    tool call, so don't call an MCP tool between the script and the build; afterwards the
    new server starts by itself, or the client needs a reconnect.
3. **Restart Revit after a build.** Close the launched Revit and run `pyrevit launch` again. The
   "Security - Unsigned Add-In" dialog appears for unsigned builds only, such as a plain `ci`
   build; accept it with **Load Once**, because the MCP host doesn't answer before that. A `local`
   build is signed and doesn't raise it. Python-only changes need no rebuild, but they need a restart or
   reload to take effect: IronPython can `reload()` a changed module, while
   CPython can't redefine classes that implement .NET interfaces (reloading `pyrevit.revit.db.create`
   raises `Duplicate type name within an assembly`). Restarting Revit loads the edits on both engines.
4. **Repeat full test runs on the other IronPython.** `ironpython` runs on 2.7.12 or 3.4.2
   depending on the engine the session was started with, while `cpython` is unaffected. Start one
   session per engine with `pyrevit launch <clone> default <year>` and
   `pyrevit launch <clone> 342 <year>`, one after the other or side by side, and select the session
   with the `revit` argument of the MCP tools. `get_context` and every run's `engine` field show the
   version in use. Run the full tests once per IronPython. Nothing is attached, so there is no
   re-attach, and the next plain Revit start is unchanged.

    If you test a single session through an attachment instead, the engine is one setting per clone:
    `pyrevit attach <clone> default --installed` selects 2.7.12 and `pyrevit attach <clone> 342
    --installed` selects 3.4.2. The switch rewrites the `.addin` manifest, so the running Revit keeps
    its engine until it is restarted (and the **Load Once** dialog appears again on an unsigned build). Attach `default`
    again, restart Revit and accept **Load Once** before continuing, and don't switch the attachment
    while other sessions share the machine.
5. **Run the snippets in scratch documents.** `run_query` rolls back changes to the active
   document, so code that edits a family or project opens its own with `app.NewFamilyDocument(template)`
   or `app.NewProjectDocument(DB.UnitSystem.Metric)` and closes it with `Close(False)` in `finally`.
   Roll back an open transaction on that document first: `Close` raises while one is open, and the
   error hides the original failure. Put back any user setting the snippet touched, such as
   `app.SharedParametersFilename`.

The [in-Revit agent tests](#in-revit-agent-tests) cover the shipped skills and the pyrevitlib side
of the automation operations on both engines.

### Running several clones side by side

`pyrevit attach` writes one `pyRevit.addin` per Revit year, so only one clone and engine can be
attached to a year at a time, and rewriting it changes what the next Revit of that year loads.
Parallel review or test sessions should not attach at all. `pyrevit launch` starts Revit with a
manifest of its own and leaves the shared one alone:

```shell
pyrevit launch <clone name or path> default 2026 --language=ENU
pyrevit launch <clone name or path> 342 2026 --isolated
pyrevit launch <clone name or path> default 2026 <model path>
```

Run it as a background process: it prints the process id, the clone, the engine and the launch
directory, stays running while that Revit runs, and deletes its temporary files when Revit exits.
Revit writes the session's journal into the launch directory, the folder of the journal it was
started with, so before deleting it the launcher copies the journal and its worker logs into
Revit's standard `%LOCALAPPDATA%\Autodesk\Revit\Autodesk Revit <year>\Journals` folder as
`journal.launch-<launch directory>.0001.txt`; Revit numbers every launch's journals from 0001, so
the plain name would replace one of your own. An `--isolated` session's journals go there too:
isolation covers pyRevit's user folder, which is removed with the launch directory, not Revit's.
A launch directory left by a killed launcher is removed later without saving its journals.
The clone may be a registered name or any path to a built clone, such as a git worktree. The
engine is `default`, a version such as `342` or `2712`, or an engine id.

- **Per-launch manifest.** Revit reads add-in manifests from the folder of the journal it is
  started with, and a manifest there replaces a standard-folder manifest with the same add-in id.
  A manifest merely sitting in the working directory is ignored, so the launcher always starts
  Revit with a journal. The shared `Addins\<year>\pyRevit.addin` is neither read nor written, and
  the session reports the clone it loaded, not the one attached.
- **Closing one session** leaves the others, and the attachment, as they were. The next plain
  start of a Revit year loads whatever is attached.
- **`--isolated`** points the session at its own pyRevit user folder (`PYREVIT_PATH_OVERRIDE`),
  seeded with a copy of the config the clone would load anyway (the clone's own config, else yours),
  so config changes, caches and logs of the session don't reach the others. A config stored in the
  clone is ignored by such a session (`PYREVIT_IGNORE_LOCAL_CONFIG`). Instance records, run records and captures stay under
  `%APPDATA%\pyRevit\agent` (`PYREVIT_AGENT_DIR`), because clients look for sessions there.
- **Model.** An optional model path after the year, such as
  `pyrevit launch dev default 2026 C:\Models\Tower.rvt`, is checked before anything is prepared
  and opened when Revit starts: the launch journal opens it the way Revit records a model passed
  on its command line, since Revit doesn't take a model and a journal together. Revit's own
  dialogs while opening, such as worksets or an upgrade, are left to the user. A path with
  characters outside ASCII is refused: Revit 2026 did not find such a model when the journal named
  it and stopped on "Failed to open document". Open that model once the session is up.
- **Unsigned Add-In dialog.** The signing of `bin\` by a `local` build removes the dialog; for an
  unsigned (`ci`) build accept **Load Once**.

Each instance record, and so `list_revit_instances`, carries `clone`, `clone_path`, `engine`,
`engine_version`, `commit`, `branch`, `config_root` and `per_launch`; `get_context` reports the same
under `pyrevit`. `branch` is the checked-out branch of a git clone, a git worktree included, or
the branch a clone deployed from an image was made from. The `revit` selector of the MCP tools and of `pyrevit agent` accepts a clone name or
path besides a year or process id, so two Revit 2026 sessions on different clones are told apart by
`revit: "<clone name>"`. A clone whose name is a number is selected as `clone:<name>`, because a bare
number is a process id or a year. When several sessions match, `ambiguous_revit` lists each with its clone and
engine; pick one by clone name, or by process id when one clone runs in several sessions.

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
name, the Revit version, the process id and the clone and engine the session runs, and removes it
when Revit exits.
Discovery excludes registrations and attempts to delete their files only when the recorded process is missing, its readable name is not `Revit` (case-insensitive), or its readable start time exceeds the registration timestamp by more than two seconds.
A matching process name and start time establish liveness without requiring an available pipe.
If process metadata or the registration timestamp cannot establish liveness, discovery checks for the recorded named pipe without connecting, up to three times at 300 ms intervals.
Any successful pipe check includes the registration in discovery.
If all pipe checks fail, discovery excludes the registration from the current result but retains its file for subsequent discovery.
The host keeps a free pipe instance waiting while fewer than four connections are open, and waits 500 ms after a pipe error; a temporarily absent pipe does not establish that the host has stopped.
After ten failed attempts in a row to create the pipe, the host stops listening, logs an error, removes its registration and keeps no pipe until pyRevit is reloaded.
Excluded registrations do not appear in `ambiguous_revit` messages.

### Existing pieces this builds on

| Piece | Where | Used for |
|---|---|---|
| Queued ExternalEvent dispatcher | `ShellExternalEventDispatcher` in `dev/pyRevitLabs.PyRevit.Shell/ShellLauncher.cs` | Pattern for the agent request queue (task-based wait, no spin) |
| Script execution | `ScriptExecutor`, `ScriptRuntimeConfigs.Variables` | Running agent scripts on the IronPython / CPython engines |
| Config accessors | `PyRevitConfigs` | `[agent]` settings, shared by the host and the CLI |

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
| `dev/pyRevitLabs.PyRevit.Runtime/Agent/` | Host, dispatcher, pipe server, run guard, approval and isolate preview, script runner, inspector, API lookup. It lives in the runtime so it can call `ScriptExecutor` directly; every per-year runtime build shares the source. |
| `pyRevitAssemblyBuilder` `SessionManagerService` | Starts, refreshes or stops the host on every `LoadSession` to match the config. |
| `pyrevitlib/pyrevit/agent/` | In-engine runner: executes the agent source, captures output, serializes `result`. Must stay parseable by IronPython 2.7, IronPython 3.4 and CPython 3. |
| `pyRevitLabs.PyRevit` `PyRevitConfigs` | `Get/SetAgentEnabled`, `Get/SetAgentPolicy`, `Get/SetAgentEngine`, `Get/SetAgentReckless`, `Get/SetAgentUserSkillsEnabled`, `Get/SetAgentTabHighlight`. |
| `pyRevitCLI` | `PyRevitAgentClient` (discovery and pipe protocol), `PyRevitCLIAgentCmds` (`agent`, `configs agent`, `mcp install` and `uninstall`), `PyRevitMcpServer` (`pyrevit mcp`). |
| `pyRevitDevTools` `Debug.panel/Agent Tests.pulldown` | In-Revit end-to-end tests that drive the host through `AgentHost.HandleRequest`. |
| `dev/pyRevitLabs/tests/pyRevitLabs.PyRevit.Runtime.Agent.Tests` | Unit tests of the run guard against Revit test doubles; run in CI. |

### Pipe protocol

Newline-delimited JSON-RPC 2.0, one request per connection. Revit accepts up to four
connections at once, each served on its own thread, and closes one that sends nothing for 30
seconds; the dispatcher still runs their requests one at a time on the main thread. A line longer than 16,777,216
characters (up to three bytes each in UTF-8) is answered with a `request_too_large` error
(outcome `not_run`; the message says the request was refused and nothing ran) without being run, on any connection; the CLI and MCP server refuse lines they read past
the same limit. Reading a line character by character costs about 1.5 to 2 s for a 16 MB line
on .NET 8 and about twice that on .NET Framework, well inside the 30 second idle limit.
Methods: `ping`,
`get_context`, `run`, `inspect_elements`, `show`, `capture`, `lookup_api`. Errors carry a stable
`data.type`, such as `revit_busy`, `no_active_document`, `document_changed`, `policy_readonly` or
`invalid_params`. Only a line that isn't JSON is `parse_error` (-32700). A parameter of the
wrong JSON type, or a `capture` width outside 320-2400, is `invalid_params`. Any other
unexpected failure is `internal_error` with `data.outcome` `unknown`, because the work may
already have run.

### What became of a request that got no answer

A client that gets `revit_busy`, or loses the connection, has to know whether its request ran
before it sends it again. Every request goes out under a request id (the CLI and MCP server
use `req-` and twelve hex digits as the JSON-RPC `id`), and a failure says what is known:

| `outcome` | Meaning | What to do |
|---|---|---|
| `not_sent` | The request never reached the host: nobody was listening, another client held the pipe, or the pipe belongs to another process. | Send it again. |
| `not_run` | The host refused the request before running any of it and discarded it. It is removed from the queue and never runs later. | Send it again once Revit is idle. |
| `unknown` | The request was sent and the answer was lost (the connection broke or closed, or the client stopped waiting), or the host stopped waiting for a run stuck past its time limit (`run_hung`). It may have run, may still be running or waiting to run, or may never run. | Look it up by request id before sending it again. |

Every `revit_busy` and `document_changed` the host raises is a `not_run`. For a `run` request the host also leaves a
run folder with `status` and `decision` `not_run`, and returns its `run_id` and `run_dir` in the
error's `data`. Without it a refused request would leave no trace. A run that did start records
the request id in `request.json` and `response.json` (`request_id`), so a request can be found
either way. Lookups work for the ids the CLI and MCP server generate (`req-` and twelve hex
digits). A request another client sent under a different `id` is stored under that id, but
`pyrevit agent show` and `get_run` only search for the generated form:

```
pyrevit agent show req-0123456789ab
```

The MCP tool `get_run` accepts the same request ids. Errors from the MCP server carry
`outcome`, `request_id` and, when the host recorded one, `run_id`. A request that is still
queued has no record yet, and one that never arrived has none at all. A pipe error after
sending, an answer that cannot be read, a client that stops waiting after sending (a cancelled
call, or a ping with no answer in time: `no_answer`), a host `internal_error`, or an MCP
`server_error` raised while processing the host's answer leaves the outcome `unknown`. Before
sending, the MCP server checks the type, numeric range and array length of each argument given
against the tool's `inputSchema`; required arguments and enum values are left to the tool and
the host. An explicit JSON `null` is checked like any other value: it is `invalid_params` unless
the property's schema lists `null`, which only `revit` and `document` do. An `invalid_params` from that check has no `request_id`: nothing was sent. An
`invalid_params` the host returns comes with the `request_id` of the request it refused.

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
      script that rewrites the policy can't loosen it for its own run, nor, without the user
      confirming it in Revit, for later runs.
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
- Script engines are reused between runs. Whatever a run changes in the interpreter, such as
  `sys.modules`, patched pyRevit functions, builtins or environment variables, stays for later
  runs, and on CPython also for the user's CPython buttons, which share the one interpreter.
  Rolling back the model doesn't undo it.
- Revit runs one agent request at a time. While one session's run is executing, which can
  last until its `timeout_s` (plus 30 seconds before a stuck run fails with `run_hung`), a
  second request connects at once, waits up to its `start_timeout_s` (30 seconds by default)
  and then gets `revit_busy` (`not_run`), which says how long an earlier request has run. A call
  whose client cancelled it or stopped waiting keeps running too, but no longer blocks the
  next connection. Four connections can be open at once; a fifth client waits for one to
  close, up to the CLI's 10-second connect timeout. Keep runs short, and run one agent per Revit.
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
- A rollback can report success and still leave the model changed. In a workshared local
  bound to a central model, deleting or changing elements the local doesn't own makes Revit
  borrow them while the script's transaction commits. That flushes Revit's undo stack under
  the run's open group, whose `RollBack()` then still returns `RolledBack`.
  After every rollback the
  host therefore checks the run's change set against the model: an element the run deleted
  that is still missing, or one it added that is still there, makes the run
  `rollback_incomplete` with `status: error`, for dry runs and queries too, also when the
  group had already ended before the rollback was requested. The host can't undo the
  changes then, and the borrowed ownership stays with the local; the user has to
  undo in Revit or close the document without saving. The check does not cover
  modifications: the host records no state from before the run, so a script that only
  changes elements it doesn't own is reported `rolled_back` even if the changes stay. Run
  dry runs of destructive or modifying scripts on a detached or non-workshared copy.
- Revit regeneration inflates change sets: two new walls can report 100+ modified
  elements (rooms, tags, paths of travel, schedules). The MCP tools therefore return only
  counts, categories and the first 20 added, modified and deleted elements; the longer
  sample is in `get_run`.

### Decisions and known limits

Choices made on purpose, with the reason, so they aren't reopened as bugs:

- **Leftover documents.** After a run the host closes, without saving, every background
  document that wasn't open when the run started. A viewless document another add-in opened
  during the run (for example from its own `DocumentOpened` handler) is closed too: its handler
  runs inside the script's own API call, so Revit gives no way to tell who opened it.
- **`deleted_ids` carries ids only.** The change set is described while the run's group is still
  open, when deleted elements no longer exist, so their category, name and class can't be read.
  Only a run that rolls back could describe them, after the rollback.
- **Traced runs are slower.** When the `__agent_start__` rewrite can't prove it wraps every
  `Start` call, the runner traces the script to find open transactions and checks the attributes
  of every local on every traced line. Measured on IronPython 2.7: 1.6 times slower with
  empty objects, 3.7 times with 40 attributes (100,000 iterations: 13.6 s against 3.7 s). A
  per-object cache would miss a transaction stored on an object after it was first seen, so the
  cost is accepted.
- **Screen-capture overlays.** `screen` mode ignores windows that are both layered and transparent
  to input (`WS_EX_LAYERED | WS_EX_TRANSPARENT`), such as the GeForce overlay, which span the
  screen and draw little. Such a window that draws opaque content over the view ends up in the
  image. The check keeps a capture from showing another application's window by mistake; it isn't
  a privacy boundary, and `GetLayeredWindowAttributes` reports nothing for an overlay drawn with
  per-pixel alpha (`UpdateLayeredWindow`), so there is no cheap way to tell how much it covers.
- **Host error details reach the agent.** The client passes every `error.data` field the host
  sets (such as `run_dir`) through to MCP results. The host only puts fields there that it wrote for
  the agent, and the agent runs as the same user on the same machine.
- **Dialogs during requests.** Every request that runs on Revit's main thread dismisses each dialog
  Revit raises through `DialogBoxShowing` while it runs, including a prompt another add-in shows
  in reaction to it (for example to a view `zoom` opens), and lists it in `dialogs`. Requests other
  than `run` install no `IFailuresPreprocessor`; their transactions only change temporary view
  state or are rolled back.
- **Run-tab highlight flush.** The highlight paints the document tab and then flushes rendering
  with a nested `Dispatcher.Invoke` at `Render` priority, so the tab shows while the run blocks
  Revit's main thread. That nested frame also runs every dispatcher item queued at `Normal`,
  `DataBind` or `Render` priority, for example another add-in's `BeginInvoke`, inside the run's
  external event handler (checked with a plain WPF dispatcher: the queued items ran before the
  flush returned, a `Background` item after it). Kept: WPF has no public way to render without
  pumping the queue, and without the flush the highlight would only appear once the run is over.
  The flush when the run asks for approval happens while its transaction group is open, but the
  approval `MessageBox` that follows runs a modal loop that processes the same queue; the flush
  when the run starts happens before its transaction group exists.
- **Shared agent storage.** Per-launch sessions keep their instance and run records in the shared
  `%APPDATA%\pyRevit\agent` folder, so clients find every session; see
  [Running several clones side by side](#running-several-clones-side-by-side).
- **Uninterruptible calls.** A single blocking call can't be stopped on any engine; `run_hung`
  releases the caller. See the timeout rules in [Script contract](#script-contract).
- **`null` tool arguments.** A `null` argument is `invalid_params` unless the
  property's schema lists `null`; see
  [What became of a request that got no answer](#what-became-of-a-request-that-got-no-answer).
- **Built-in automation input types.** The hand-wired operations in
  `PyRevitAutomationOperations` declare their inputs the way markers do (`"value: scalar"`,
  `"name: string"`), and one set of rules lists and checks both. Only
  `pyrevit.elements.by-category` keeps a JSON-schema `array` input and its own C# check, because
  no marker type describes a bounded list of category names. The unit parsers
  (`pyrevit.units.parse-length`, `pyrevit.units.parse-slope`) follow the `scalar` rule: a boolean
  is accepted, as `parse_length` and `parse_slope` take it as the number 1 or 0, and an integer
  beyond Int64 is refused. Their errors read like those of marked operations, for example
  `'inputs.value' is required.` and `'inputs' accepts only value (got extra).`
- **Runner reload check in C#.** The few lines that drop a stale `pyrevit.agent._runner` before
  importing it are a string in `AgentScriptRunner`, because they decide whether the runner module
  itself is current; moved into a Python module, that module would need the same check.

## In-Revit agent tests

The pyRevitDevTools extension has an **Agent Tests** pulldown under *pyRevitDev > Debug*. Its buttons
drive the host from inside Revit through `AgentHost.HandleRequest`, which runs the same JSON-RPC
requests the pipe carries synchronously on the Revit main thread. A command can't use the pipe
itself: the pipe executes requests through an ExternalEvent that never fires while a command runs.

| Button | Covers |
|---|---|
| Run Agent Tests | `get_context`, `inspect_elements`, `show`, `capture`, `lookup_api`; what each request refuses (invalid parameters, unsupported or closed views); query runs on both engines (results, error lines, timeouts, workspaces, records, dismissed dialogs); modify runs (decisions, change sets, rollback, open transactions, save and export blocks, other documents, warnings, `readonly`, a policy changed during the run or outside Revit); the agent settings; the real named pipe (`ping`, `lookup_api`, errors, `revit_busy` while a command runs) |
| Run Agent Tests (CPython) | The same tests started from a CPython command, which also checks that the command survives nested agent runs |
| Run Agent Library Tests | The shipped and user skills, `lookup_pyrevit_api` and `list_automation` through a short-lived `pyrevit mcp` process, and the pyrevitlib side of the automation operations on both engines |
| Run Agent Approval Tests | The `ask` prompt's *Keep* and *Discard*. The prompt is a native Windows message box that `DialogBoxShowing` can't answer, so a helper thread presses the button; if a prompt stays on screen, click the button its title names |

The tests create two scratch projects in the temp folder, set the policy to `auto` (or `ask` for the
approval tests) while they run, then close the projects without saving, reactivate the document
that was open before, and restore the policy. The settings tests change the real pyRevit config and
put every value back. The pipe tests are skipped when the host is disabled, and the other tests have
only been run with it enabled.
Each test is written to `%TEMP%\pyrevit-agent-tests.log` before it starts, so if Revit ever hangs, the
last line of that file names the test that was running.

`run_automation`, `navigate_revit_link` and the hints the MCP server adds to run errors call back
into Revit through the pipe, which can't answer while a command runs, so these buttons don't cover them.
