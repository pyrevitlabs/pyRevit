# Agent runtime (design)

!!! warning "Status: design + Phase 0 spike"

    This page is the working plan for the pyRevit agent runtime. Nothing here is a
    shipped feature yet. The host is off by default and only starts when
    `[agent] enabled = true` is set in the pyRevit config.

## Goal

Let any MCP-capable coding agent (Claude Code, Codex, OpenCode, ...) read and modify a
live Revit model by sending **Python programs**, not by calling hundreds of
per-API tools, and let it run existing **pyRevit commands** as tools. The human stays
in control of every model change and approves it inside Revit.

The Revit API is the toolset. MCP is only the control protocol.

## Existing pieces this builds on

| Piece | Where | Used for |
|---|---|---|
| Queued ExternalEvent dispatcher | `ShellExternalEventDispatcher` in `dev/pyRevitLabs.PyRevit.Shell/ShellLauncher.cs` | Pattern for the agent request queue (task-based wait, no spin) |
| Script execution | `ScriptExecutor`, `ScriptRuntimeConfigs.Variables` | Running agent scripts on the IronPython / CPython engines |
| Structured command results | `__result__` / `script.get_results()` | Returning command output to the agent |
| Command lookup | `sessionmgr.execute_command()` | Running a command by unique id |
| Bundle metadata | `ParsedBundle` (`pyRevitExtensionParser`) | Opt-in `agent:` block |
| LLM docs | `docs/llms.txt`, `docs/llms-full.txt` | Grounding resources for the agent |
| Batch runs | `pyrevit run --models=` | Multi-model agent jobs |

Deliberately **not** reused:

- **Routes server** (`pyrevit.routes`): it has no authentication
  (`# TODO: auth` in `pyrevitcore_api.py`) and falls back to `0.0.0.0`.
  Code execution must never be exposed through it.
- **`ScriptExecutor.RequestExecuteScript`**: it spins on `IsPending` and uses a single
  handler slot that a concurrent request can overwrite. The agent host owns its own
  queue.

## Architecture

```text
 Claude Code / Codex / OpenCode
            │  MCP over stdio
            ▼
 ┌──────────────────────────────┐   pyRevitCLI (net8, out of process)
 │ pyrevit mcp                  │   MCP protocol, tool schemas, instructions,
 │                              │   instance discovery, API reflection, docs
 └──────────────┬───────────────┘
                │  named pipe  \\.\pipe\pyrevit-agent-<pid>  (current user only)
                ▼
 ┌──────────────────────────────┐   inside Revit (PyRevit.Runtime, Agent/)
 │ AgentHost                    │
 │  AgentDispatcher ─► ExternalEvent
 │  AgentRunGuard: TransactionGroup, DocumentChanged diff,
 │                 save/sync/close blocking, dialog + failure capture
 │  approval (inside Revit), AgentScriptRunner, run folder audit
 └──────────────┬───────────────┘
                ▼
     ScriptExecutor ─► IronPython / CPython ─► Revit API + pyrevitlib
```

Why two processes:

- **Dependency isolation**: the MCP SDK and its dependencies stay out of `revit.exe`.
  Assembly clashes with other add-ins are a real risk on .NET Framework 4.8.
- **Multi-instance routing**: the CLI already knows about installed Revits and attachments.
- **Stability**: the agent keeps its connection to `pyrevit mcp` across Revit restarts.
- **Client support**: every MCP client supports stdio.

Why a named pipe: no TCP port, no firewall prompt, and nothing on the network. The pipe
accepts only the current Windows user, and that is the authentication.

Discovery: each host writes `%APPDATA%\pyRevit\agent\instances\<pid>.json` with the pipe
name, the Revit version and the process id, and removes it on shutdown.

## Where the code lives

| Area | Change |
|---|---|
| `dev/pyRevitLabs.PyRevit.Runtime/Agent/` | Agent host, dispatcher, pipe server, run guard, script runner. It lives in the runtime so it can call `ScriptExecutor` directly; the source is shared by every per-year runtime build. |
| `pyRevitAssemblyBuilder` `SessionManagerService` | Starts the host during `LoadSession` when enabled. Starting is idempotent, like `ScriptExecutor.Initialize`, so reloads don't leak pipes or events. |
| `pyrevitlib/pyrevit/agent/` | In-engine runner: executes the agent source, captures stdout, serializes `result`. |
| `pyRevitCLI` | `pyrevit mcp` stdio server and `pyrevit agent status\|runs\|show` (Phase 1). |
| `pyRevitLabs.Configurations` | Typed `AgentSection`: `enabled`, `policy`, `default_engine`, `max_result_kb`, `run_timeout_s` (Phase 1). |
| `pyrevit.forms` | Agent mode for prompts (Phase 3). |
| `pyRevitExtensionParser`, `pyrevit/extensions` | `agent:` block in `bundle.yaml` (Phase 3). |

## MCP surface

| Tool | Changes the model? | Purpose |
|---|---|---|
| `list_revit_instances` | – | CLI-side: open Revit sessions |
| `get_context` | – | Revit/pyRevit versions, engines, active document, view, selection summary |
| `inspect_elements(ids, params?)` | – | Category, type, level, parameters, bounding box |
| `lookup_revit_api(name)` | – | Reflection over the running RevitAPI.dll, so the agent doesn't call APIs that aren't there |
| `run_query(script, engine?, inputs?)` | never | Read-only execution |
| `run_modify(title, script, dry_run?, inputs?)` | after approval | Guarded write with change set |
| `list_commands(filter?)` | – | Commands that opted in |
| `run_command(id, inputs?)` | as declared | Run a pyRevit command without its UI |
| `get_run(run_id, page?)` | – | Full output, traceback, diff, paged large results |
| `cancel_run(run_id)` | – | Cooperative cancel |
| `set_selection(ids)` / `zoom_to(ids)` | view only | Show the human what the agent found |
| `save_as_command(...)` | writes files | Promote a script to a ribbon button |

The MCP server `instructions` carry the conventions:

- Write CPython 3 unless `engine` is `ironpython`.
- Assign `result` instead of printing large data.
- Never open transactions in `run_query`.
- Internal units are feet.
- Use `ElementId.Value` on 2024+.
- Explore first, then dry-run, then modify.

### Script contract

The engine pre-injects `doc`, `uidoc`, `app`, `uiapp`, `DB`, `UI` and `inputs`. The
script assigns `result`, which the runner serializes:

- `ElementId` → integer
- `Element` → `{id, category, name}`
- `XYZ` → `[x, y, z]`
- .NET collections → lists

Printed output is captured and returned (truncated when large).

```python
walls = DB.FilteredElementCollector(doc).OfClass(DB.Wall).ToElements()
result = {"count": len(walls), "ids": [w.Id for w in walls[:50]]}
```

## The guarded run

Every run executes in one ExternalEvent callback on the Revit main thread:

1. **Arm guards** (only while the run is active):
    - `DocumentSaving`, `DocumentClosing` and `DocumentSynchronizingWithCentral` are cancelled.
    - `DialogBoxShowing` is captured and dismissed.
    - `FailuresProcessing` warnings are recorded and deleted.
    - `DocumentChanged` collects added, modified and deleted ids.
2. **`TransactionGroup.Start("Agent: <title>")`**.
3. **Run the script.** Its own transactions nest inside the group.
4. **Decide:**
    - **query**: always roll back. A recorded change becomes a `query_modified_model` error.
    - **dry_run**: roll back and return the change set.
    - **modify**: while the group is still open, show the approval dialog in Revit.
      Commit → `Assimilate()`, which is one undo entry. Discard → `RollBack()`.
5. **Disarm guards** and write the run folder (`script.py`, request, response).

The approval must happen inside the same callback, because Revit won't keep a
transaction group open after the callback returns. The benefit is that the human
approves inside Revit, and the agent can't approve itself.

Cancellation is cooperative:

- IronPython uses the shell's keyboard-interrupt path.
- CPython uses pythonnet's `PythonEngine.Interrupt`.
- .NET 8+ can't abort threads, so a timed-out modify always rolls back.

Honest limits:

- Rollback protects the model, not the file system or the network. There is no sandbox.
- ExternalEvents only fire while Revit is idle, so a busy Revit returns `revit_busy`.

## pyRevit commands as agent tools

Commands opt in through `bundle.yaml`:

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

| Phase | Deliverable | Done when |
|---|---|---|
| **0: Spike** | Pipe server + guarded run + script runner, Python test client | On 2024 (net48) and 2026 (net8): DocumentChanged fires for transactions inside a transaction group; a modal approval works while the group is open; dialog and failure capture work inside an ExternalEvent |
| **1: Read-only MVP** | `pyrevit mcp`, `get_context`, `inspect_elements`, `lookup_revit_api`, `run_query`, `get_run`, typed config | An agent answers model questions and provably can't change the model |
| **2: Writes** | `run_modify` + dry run, approval UI with diff, cancellation, policy | End-to-end renumbering with a correct diff and a single undo |
| **3: Commands** | `agent:` bundle block, `list_commands` / `run_command`, forms agent mode | An agent runs a command, handles `needs_input`, and fixes the reported issues |
| **4: Authoring and docs** | `save_as_command`, shipped agent skill, setup docs | A new user connects a client in under 5 minutes |
| **5: Scale** | Multi-instance routing, `batch_run`, persistent sessions | Multi-model audit through the CLI |

## Open questions

- Model data leaves the machine through the LLM provider. The feature stays off by
  default, and an admin lock should be available.
- Whether the CPython engine is mature enough to be the default for agent scripts.
- How to relate to the third-party `mcp-server-for-revit-python` extension.
- Behaviour on workshared models with elements owned by other users.

## Phase 0: trying the spike

1. Build the runtime for the Revit version and engine you test. For example:
   `dotnet build dev/pyRevitLabs.PyRevit.Runtime/2026/pyRevitLabs.PyRevit.Runtime.2026.csproj -c "Debug IPY2712PR"`.
   Also build `pyRevitLabs.PyRevit` and `pyRevitAssemblyBuilder`.
2. Enable the host by adding this to `%APPDATA%\pyRevit\pyRevit_config.ini`, then reload pyRevit:

    ```ini
    [agent]
    enabled = true
    ```

3. Run `python extras/agent-spike/agent_client.py ping`. The client finds the running Revit
   through `%APPDATA%\pyRevit\agent\instances`.
4. Run each scenario with
   `python extras/agent-spike/agent_client.py run extras/agent-spike/scenarios/<file> --mode <mode>`
   and compare the response with the expectation in the scenario's docstring. Every run is
   also recorded under `%APPDATA%\pyRevit\agent\runs\`.

| Scenario | Mode | Verifies |
|---|---|---|
| `01_query_walls.py` | query | Execution, output capture, result serialization |
| `02_query_that_writes.py` | query | `DocumentChanged` fires inside a transaction group; query rollback |
| `03_set_comments.py` | dry_run, then modify | Diff, approval dialog with selection preview, single undo entry |
| `04_overlapping_walls.py` | dry_run | `FailuresProcessing` capture, no warning popup |
| `05_dialogs_and_save.py` | query | `DialogBoxShowing` dismissal, save blocking |
| `06_transaction_left_open.py` | dry_run | Revit's behavior when a script leaves a transaction open |
| `07_script_error.py` | modify | Error rollback, traceback quality |

Repeat 01–03 with `--engine cpython`. Run the whole set on Revit 2024 (net48) and
2026 (net8).
