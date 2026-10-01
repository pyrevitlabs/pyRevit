# Agent runtime

!!! warning "Status: experimental"

    The agent runtime is under active development on the `feature/agent-runtime` branch.
    It is off by default. Phase 0 (the in-Revit host) is validated on Revit 2024 and 2025; the CLI
    and MCP server (Phase 1) are in progress. See [Phases](#phases).

The agent runtime lets any MCP-capable coding agent (Claude Code, Codex, Cursor, VS Code,
OpenCode, ...) read and change a live Revit model by sending **Python programs**, not by calling
hundreds of per-API tools. The Revit API is the toolset; MCP is only the control
protocol. The human stays in control: every model change is approved inside Revit.

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
keeps entries that point at another pyRevit install. When that command runs elevated, it
checks the Cursor, VS Code and OpenCode entries of every user profile on the machine, and it
doesn't start the `claude` or `codex` command line tools, so those two entries stay; run
`pyrevit mcp uninstall claude` (or `codex`) from a normal prompt. Project-level entries
(`--project`) are never removed automatically. To turn the host off: `pyrevit configs agent disable`.

!!! note "Model data leaves the machine"

    Whatever the agent reads (element names, parameter values, results) is sent to
    the agent's model provider. Check this against your project's confidentiality rules
    before enabling the agent runtime.

## Reference

### Configuration

| Setting | Command | Values |
|---|---|---|
| `[agent] enabled` | `pyrevit configs agent (enable \| disable)` | Starts the in-Revit host on the next pyRevit load. Default `false`. |
| `[agent] policy` | `pyrevit configs agent policy (readonly \| ask \| auto)` | `readonly`: queries and dry runs only. `ask` (default): each modify run needs approval in Revit. `auto`: modify runs are committed without the prompt; each is still one undo entry, guarded and recorded. |
| `[agent] engine` | `pyrevit configs agent engine (ironpython \| cpython)` | Engine for runs that don't name one. Default `ironpython` (the attached IronPython). |

Run any of these commands without a value to print the current setting.

### MCP tools

| Tool | Changes the model | Purpose |
|---|---|---|
| `get_skill` | no | Task guidance in markdown (see [Skills](#skills)); the server's instructions tell agents which skill to read first |
| `list_revit_instances` | no | Running Revit sessions with the agent host |
| `get_context` | no | Revit and pyRevit versions, agent policy, `scripting` (engine and Python version scripts run on), document, `open_documents`, active view, selection, levels |
| `inspect_elements` | no | Class, category, type, level, location, bounding box and parameters of up to 50 elements |
| `lookup_pyrevit_api` | no | Functions and classes of pyrevitlib and rpw, with signatures and docstrings, from the clone's source (see [Shared libraries](#shared-libraries)) |
| `lookup_revit_api` | no | Signatures of a Revit API type or member, reflected from the running Revit. Also its namespace and Python import line, and a `creation` list: static factories and the `doc.Create.New…` methods that return the type. A missing member returns `found: false` with the closest names, including matching values of other enums |
| `show_elements` | no | Select, zoom to, or temporarily isolate / hide elements (by id or category) in the active view, or reset the temporary mode. No approval prompt. If Revit can't zoom, the response has `zoomed: false` and a `zoom_failed` error instead of a dialog blocking Revit. |
| `capture_view` | no | PNG of a view for visual checks. `export` renders any view through Revit; `viewport` renders an open view through Revit cropped to what its window shows now (zoom, pan, temporary isolate; no selection highlight), in a rolled-back transaction; `screen` captures the active view window as the user sees it (selection, temporary isolate), and fails with `view_obscured` when another application's window covers any part of it; view `3d` renders a temporary 3D view of model categories only, framed by a section box around the model (or `elements`) and seen from `direction`, which is rolled back. Saved under `%APPDATA%\pyRevit\agent\captures`. |
| `run_query` | never | Run a read-only script; model changes are always rolled back, but the script itself has full access to the machine, so the tool isn't marked read-only for MCP clients. `workspace` puts a folder of the agent's own modules on `sys.path`, re-imported fresh every run. `timeout_s` (default 300) stops a script that runs too long |
| `run_modify` | after approval | Run a changing script against the active document; it is refused when no document is active. `dry_run=true` previews the change set and rolls back |
| `get_run` | no | A recorded run: response, script, and pages of a large result |

Every request that runs on Revit's main thread closes the dialogs Revit opens during it and
reports them in `dialogs`, so a dialog can't leave the call hanging.

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
  front matter. PR 1 ships `revit-scripting`, the core contract for raw Revit API scripts.
  Additional domain guidance and firm customization are delivered separately.

Agents read a skill with `get_skill(name)`, and other markdown files in its folder with
`get_skill(name, file)`. The foundation runtime loads only shipped skills from its selected
clone; it does not load user-supplied skill directories.

### Script contract

Scripts are Python, executed inside Revit by the regular pyRevit engines. The runner
injects `doc`, `uidoc`, `app`, `uiapp`, `DB` (`Autodesk.Revit.DB`), `UI`
(`Autodesk.Revit.UI`) and `inputs` (the `inputs` argument as a dict). Assign `result`
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
- `run_modify` requires an active document and is refused before the script runs when none is
  active. The other tools (`capture_view`, `inspect_elements`, `show_elements`) also require an
  active document.
- Background documents a run created or opened (no view in Revit, not linked, not open when
  the run started) are closed without saving when the run ends, whatever its outcome, and
  listed in `closed_documents`. The host blocks their save and save-as operations while a run is
  active.
  `get_context.open_documents` lists every open document and marks the background ones.
- While a run is active, the host cancels Revit operations exposed through cancellable save,
  save-as, synchronize-with-central, file-export and view-export events. The response lists a
  cancelled operation in `blocked`.
- A run in any mode that changes another open document fails with `other_document_modified`
  and is rolled back. `changes.other_documents` lists what changed. A project the script opens
  or a family from a file during the run counts as one that was already open: changing it fails
  the run, it is rolled back, and it can't be saved or saved as, so the file on disk stays
  unchanged. A family from `EditFamily` or a new document the script creates has no file yet;
  it is reported there but doesn't fail the run, and isn't rolled back.
- A script error rolls back everything, and the traceback points at the script's own lines.
  When a Revit call throws, the message carries the underlying .NET exception and its
  inner exceptions (`[.NET: Autodesk.Revit.Exceptions.… <- …]`), not only the generic
  "A managed exception was thrown".
- When Revit rolls back one of the script's transactions because of an error-level
  failure, the run fails with `revit_failure`, even if the script itself didn't raise.
- A transaction left open fails the run with `transaction_left_open`.
- A script that runs past `timeout_s` (default 300 seconds, a finite number above 0, at
  most 3600) is stopped and fails with `timeout`. The runner checks the deadline between
  Python lines, so it stops loops. A single blocking call, such as a long Revit API call or
  `time.sleep`, can't be interrupted; the run fails with `timeout` once it returns.
- Python drops a trace function after it raises once, so the runner compiles the script with
  every bare `except` and `except BaseException` narrowed to `except Exception`. A script
  can't swallow its own timeout, and can't catch `KeyboardInterrupt` or `SystemExit` that
  way. Suppression through an alias or `contextlib.suppress(BaseException)` still bypasses
  this; on CPython a watchdog thread is the backstop.
- Revit dialogs are closed automatically and reported in `dialogs`. Warnings are removed
  and reported in `failures`, and errors roll back the failing transaction.
- The document can't be saved, closed or synchronized during a run.

The MCP server's instructions teach agents these conventions, plus units (internal
feet) and `ElementId.Value` on Revit 2024+.

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
pyrevit agent runs [--limit=<n>]           recent runs
pyrevit agent show <run_id>                request, script and response of a run
pyrevit mcp [--revit=<year>]               the MCP server (stdio); started by MCP clients
pyrevit mcp (install | uninstall) (claude | codex | cursor | vscode | opencode) [--project]
pyrevit mcp uninstall --all [--owned]      every client's user-level entry; --owned keeps
                                           entries that point at another pyRevit install
```

### Run records

Every run is recorded under `%APPDATA%\pyRevit\agent\runs\<timestamp>-<run_id>\`:

- `script.py`: the submitted source
- `request.json`: title, mode, engine and inputs
- `response.json`: status, decision, changes, failures, dialogs, output and result
- `result.json`: present when the result was too large to return inline

Run records and `capture_view` images older than 14 days are deleted when the host starts.

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
the authentication.

The CLI also checks that the process serving the pipe is the Revit recorded in the instance
file, and refuses to send a request otherwise, so another local process can't take over a
pipe name while the host is down.

Remote use is through Remote Desktop only. An RDP session is an interactive logon, so
`pyrevit mcp` started inside it reaches Revit. SSH is refused on purpose: an SSH logon
carries the Network SID, so connecting fails with `UnauthorizedAccessException`, even
under the same account.

Discovery: each host writes `%APPDATA%\pyRevit\agent\instances\<pid>.json` with the pipe
name, the Revit version and the process id, and removes it when Revit exits.

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
| `dev/pyRevitLabs.PyRevit.Runtime/Agent/` | Host, dispatcher, pipe server, run guard, approval and isolate preview, script runner, inspector, API lookup. It lives in the runtime so it can call `ScriptExecutor` directly; every per-year runtime build shares the source. |
| `pyRevitAssemblyBuilder` `SessionManagerService` | Starts, refreshes or stops the host on every `LoadSession` to match the config. |
| `pyrevitlib/pyrevit/agent/` | In-engine runner: executes the agent source, captures output, serializes `result`. Must stay parseable by IronPython 2.7, IronPython 3.4 and CPython 3. |
| `pyRevitLabs.PyRevit` `PyRevitConfigs` | `Get/SetAgentEnabled`, `Get/SetAgentPolicy`, `Get/SetAgentEngine`. |
| `pyRevitCLI` | `PyRevitAgentClient` (discovery and pipe protocol), `PyRevitCLIAgentCmds` (`agent`, `configs agent`, `mcp install` and `uninstall`), `PyRevitMcpServer` (`pyrevit mcp`). |
| `extras/agent-spike/` | Phase 0 test client and scenario scripts. |

### Pipe protocol

Newline-delimited JSON-RPC 2.0, one request per connection. Revit serves one connection
at a time and closes one that sends nothing for 30 seconds. Methods: `ping`,
`get_context`, `run`, `inspect_elements`, `show`, `capture`, `lookup_api`. Errors carry a stable
`data.type`, such as `revit_busy`, `no_active_document`, `policy_readonly` or
`invalid_params`.

### The guarded run

Every run executes in one ExternalEvent callback on the Revit main thread:

1. **Arm guards** (only while the run is active):
    - `DocumentSynchronizingWithCentral` is cancelled, and so are `DocumentSaving`,
      `DocumentSavingAs` and `DocumentClosing` for every document open when the run started.
      `DocumentSaving` and `DocumentSavingAs` are also cancelled for a project or family the
      script opens from a file (`DocumentOpened`); the script may still close it, and the
      host closes it without saving when the run ends. A family from `EditFamily` or a new
      document the script created has no file yet and may be saved and closed.
    - `DialogBoxShowing` is captured and dismissed.
    - `FailuresProcessing` warnings are recorded and deleted, and errors roll back the
      failing transaction, in every non-linked document. A failure in a family or a new
      document fails the run with `revit_failure` instead of raising a dialog.
    - `DocumentChanged` collects added, modified and deleted ids, per document.
2. **`TransactionGroup.Start("Agent: <title>")`** on the active document and on every other
   open, editable, non-linked document, and later on each project or family the script
   opens from a file.
3. **Run the script.** Its own transactions nest inside the group.
4. **Decide:**
    - **any mode**, another open document changed: roll back every group. The run fails
      with `other_document_modified`. Only the active document's group is ever assimilated.
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
approves inside Revit, and the agent can't approve itself.

Honest limits:

- Rollback protects the model, not the file system or the network. There is no sandbox.
- Revit serves one agent request at a time. While one session's run is executing, which can
  last until its `timeout_s`, a second agent session can't connect and gets `revit_busy`
  after the CLI's 10-second connect timeout. Keep runs short, and run one agent per Revit.
- ExternalEvents only fire while Revit is idle, so a busy Revit returns `revit_busy`
  after 30 seconds. The error names Revit's open windows and whether an earlier agent
  request is still running: a modal dialog Revit shows while idle, such as the save
  reminder, isn't part of any run and blocks every request until the user answers it.
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

### Running the Phase 0 scenarios

1. Build the runtime for the Revit version and engine you test. For example:
   `dotnet build dev/pyRevitLabs.PyRevit.Runtime/2026/pyRevitLabs.PyRevit.Runtime.2026.csproj -c "Debug IPY2712PR"`.
   Also build `pyRevitLabs.PyRevit` and `pyRevitAssemblyBuilder`.
2. Enable the host (`pyrevit configs agent enable`) and reload pyRevit.
3. Run each scenario with
   `pyrevit agent run extras/agent-spike/scenarios/<file> --mode=<mode>`
   (or `python extras/agent-spike/agent_client.py run ...`) and compare the response with
   the expectation in the scenario's docstring.

| Scenario | Mode | Verifies |
|---|---|---|
| `01_query_walls.py` | query | Execution, output capture, result serialization |
| `02_query_that_writes.py` | query | `DocumentChanged` fires inside a transaction group; query rollback |
| `03_set_comments.py` | dry_run, then modify | Diff, approval prompt with isolate preview, single undo entry |
| `04_overlapping_walls.py` | dry_run | `FailuresProcessing` capture, no warning popup |
| `05_dialogs_and_save.py` | query | `DialogBoxShowing` dismissal, save blocking (use a writable model) |
| `06_transaction_left_open.py` | dry_run | Revit's behavior when a script leaves a transaction open |
| `07_script_error.py` | modify | Error rollback, traceback quality |
| `08_other_document.py` | query, then modify | A change in another open document fails the run and is rolled back (open two projects first) |
| `09_timeout.py` | query with `--timeout 5` | The script is stopped even though it swallows exceptions with a bare `except` |

Repeat the set with `--engine=cpython`, and run it on Revit 2026 (net8).
