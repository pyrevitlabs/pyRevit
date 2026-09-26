# Agent runtime

!!! warning "Status: experimental"

    The agent runtime is under active development on the `feature/agent-runtime` branch.
    It is off by default. Phase 0 (the in-Revit host) is validated on Revit 2024; the CLI
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

1. **Register the MCP server with your client.** Run it with the `pyrevit.exe` of the
   clone you want the agent to use. The command also turns the agent host on.

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

To remove the server: `pyrevit mcp uninstall <client>`. To turn the host off:
`pyrevit configs agent disable`.

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
| `get_context` | no | Revit and pyRevit versions, agent policy, `scripting` (engine and Python version scripts run on), document, active view, selection, levels |
| `inspect_elements` | no | Class, category, type, level, location, bounding box and parameters of up to 50 elements |
| `lookup_pyrevit_api` | no | Functions and classes of pyrevitlib and rpw, with signatures and docstrings, from the clone's source (see [Shared libraries](#shared-libraries)) |
| `lookup_revit_api` | no | Signatures of a Revit API type or member, reflected from the running Revit. Also its namespace and Python import line, and a `creation` list: static factories and the `doc.Create.New…` methods that return the type. A missing member returns `found: false` with the closest names, including matching values of other enums |
| `show_elements` | no | Select, zoom to, or temporarily isolate / hide elements (by id or category) in the active view, or reset the temporary mode. No approval prompt. |
| `capture_view` | no | PNG of a view for visual checks. `export` renders any view through Revit; `screen` captures the active view window as the user sees it (selection, temporary isolate); view `3d` renders a temporary 3D view of model categories only, framed by a section box around the model (or `elements`) and seen from `direction`, which is rolled back. Saved under `%APPDATA%\pyRevit\agent\captures`. |
| `run_query` | never | Run a read-only script; always rolled back. `workspace` puts a folder of the agent's own modules on `sys.path`, re-imported fresh every run |
| `run_modify` | after approval | Run a changing script; `dry_run=true` previews the change set and rolls back |
| `get_run` | no | A recorded run: response, script, and pages of a large result |

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
  front matter (the Agent Skills layout). `revit-scripting` covers the rules every
  script needs, and `pyrevit-library` maps the shared libraries; `modeling`, `views`,
  `family-editing`, `scheduling` and `drawings` cover tasks.
- Skills in `%APPDATA%\pyRevit\agent\skills\<name>\SKILL.md` are added, and replace a
  shipped skill with the same name, so a firm can add its own standards.

Agents read a skill with `get_skill(name)`, and other markdown files in its folder with
`get_skill(name, file)`.

### Shared libraries

Agents are pointed at pyrevitlib (`pyrevit.revit`) and rpw first, and at the raw Revit
API only for what those don't cover. The libraries are large and maintained, handle
differences between Revit versions and engines, and every addition helps pyRevit tool
authors too.

- `lookup_pyrevit_api` indexes the public functions, classes and docstrings of
  `pyrevit.revit`, `pyrevit.compat`, `rpw.db` and parts of `rpw.ui` and `rpw.utils` from the
  clone's source. It needs no Revit and follows edits to the source. A failed script that
  used a missing library name gets similar names in its hint.
- The `pyrevit-library` skill maps tasks to modules.
- Where agents kept failing and the libraries had nothing, functions were added to them:

| Module | Added |
|---|---|
| `pyrevit.revit.db.query` | `find_level`, `find_type`, `find_family_symbol`, `find_view`, `find_plan_view` (raise with the valid names instead of returning None), `get_model_elements`, `get_face_references`; `get_category` accepts `"OST_..."` names |
| `pyrevit.revit.db.create` | `create_wall(s)`, `create_profile_wall`, `create_gable_wall`, `create_floor`, `create_ceiling`, `create_footprint_roof`, `create_gable_roof`, `create_hip_roof`, `create_shed_roof`, `place_hosted_instance`, `place_family_instance`, `create_column`, `create_room`, `create_room_separation_lines`, `create_model_lines`, `create_plan_view`, `create_model_3d_view`, `create_section_view`, `create_elevation_view`, `create_dimension`, `tag_elements`, `create_room_tags`, `create_schedule`, `place_on_sheet` |
| `pyrevit.revit.db.update` | `attach_wall_tops`, `orient_3d_view`, `set_3d_view_camera`, `set_section_box`, `crop_view_to_elements`, `hide_non_model_categories`, `hide_categories` |
| `pyrevit.revit.units` | `parse_length` (`32'-6"`, `900mm`), `parse_slope` (`8:12`, `30deg`) |
| `pyrevit.revit.ui` | `request_view_change`, `get_active_ui_view`, `zoom_to_elements`, `zoom_fit` |

The roof functions call `NewFootPrintRoof` through reflection, because IronPython 3.4
doesn't marshal its out parameter, and the gable, hip and shed variants measure the built
roof and raise when its rise doesn't match the pitch. `create_room` raises when the point
isn't enclosed, which turns rooms into a check for gaps in a layout.

rpw methods that defaulted to `doc=revit.doc` bound the document once, at import. Agent
runs reuse the script engine, so those defaults now resolve the document on each call.

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
- A script error rolls back everything, and the traceback points at the script's own lines.
  When a Revit call throws, the message carries the underlying .NET exception and its
  inner exceptions (`[.NET: Autodesk.Revit.Exceptions.… <- …]`), not only the generic
  "A managed exception was thrown".
- When Revit rolls back one of the script's transactions because of an error-level
  failure, the run fails with `revit_failure`, even if the script itself didn't raise.
- A transaction left open fails the run with `transaction_left_open`.
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
```

### Run records

Every run is recorded under `%APPDATA%\pyRevit\agent\runs\<timestamp>-<run_id>\`:

- `script.py`: the submitted source
- `request.json`: title, mode, engine and inputs
- `response.json`: status, decision, changes, failures, dialogs, output and result
- `result.json`: present when the result was too large to return inline

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
| `pyRevitCLI` | `PyRevitAgentClient` (discovery and pipe protocol), `PyRevitCLIAgentCmds` (`agent`, `configs agent`, `mcp install`), `PyRevitMcpServer` (`pyrevit mcp`). |
| `extras/agent-spike/` | Phase 0 test client and scenario scripts. |

### Pipe protocol

Newline-delimited JSON-RPC 2.0, one request per connection. Methods: `ping`,
`get_context`, `run`, `inspect_elements`, `lookup_api`. Errors carry a stable
`data.type`, such as `revit_busy`, `no_active_document`, `policy_readonly` or
`invalid_params`.

### The guarded run

Every run executes in one ExternalEvent callback on the Revit main thread:

1. **Arm guards** (only while the run is active):
    - `DocumentSaving`, `DocumentSavingAs`, `DocumentClosing` and
      `DocumentSynchronizingWithCentral` are cancelled.
    - `DialogBoxShowing` is captured and dismissed.
    - `FailuresProcessing` warnings are recorded and deleted.
    - `DocumentChanged` collects added, modified and deleted ids.
2. **`TransactionGroup.Start("Agent: <title>")`**.
3. **Run the script.** Its own transactions nest inside the group.
4. **Decide:**
    - **query**: always roll back. A recorded change becomes a `query_modified_model` error.
    - **dry_run**: roll back and return the change set.
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
| **2: Writes** | Ranked change sets with before/after values, cancellation and timeouts | Planned |
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

Repeat 01–03 with `--engine=cpython`, and run the set on Revit 2026 (net8).
