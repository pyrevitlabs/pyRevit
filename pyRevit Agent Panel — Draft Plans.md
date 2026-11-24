# pyRevit Agent Panel — Draft Plans

Oct 5, 2026 · @Chris C

## Context

Plan 1 adds a dockable panel that gates, shows and controls agent access to Revit. Plan 2 adds input forms to that panel, so the agent can ask the user to choose elements or confirm a step. Neither plan changes the public `pyrevit.forms` API.

What these plans build on:

- [#3684 — pyRevit Agent Runtime](https://github.com/pyrevitlabs/pyRevit/pull/3684) (merged): `pyrevit mcp` talks over a named pipe to a host inside Revit, which runs scripts through ExternalEvent. Runs act on the active document and are guarded by a TransactionGroup (query, dry run, modify) under a readonly / ask / auto policy, with run records under `%APPDATA%\pyRevit\agent\runs`. Every other open document gets a guard group too, so a change there fails the run and is rolled back.
- [#3709 — library integration and skills](https://github.com/pyrevitlabs/pyRevit/pull/3709) (merged): pyrevitlib lookup, registered automations with validated inputs, task skills and element links.
- [RFC #3567 — pyRevit → CPython](https://github.com/pyrevitlabs/pyRevit/issues/3567): Phases 2–4 restructure `pyrevit.forms`; Tier 5 adds a C# window host for modeless and dockable windows.

Shared assumptions:

- \#3684's reviewer findings on policy refresh, the loaded config file and idle pipe clients were fixed before it merged (see 1.0).
- The panel never calls the Revit API directly. Every action goes through the host's existing ExternalEvent dispatcher.
- Testing targets Revit 2024 first, matching the sessions #3684 was tested in.

## Roadmap at a glance

&#91;embedded content: phase dependencies · Plan 1 and Plan 2\]

Plan 2's catalog and queue need only the session model; its question cards wait for the panel shell, and its guidance waits for the activity log.

## Plan 1 — Session panel: goals

Agents can touch the model only while a user-started session is active, and everything they do is visible and stoppable from a dockable pane.

Goals:

- **Consent per session.** The host rejects agent requests unless the user started a session in the panel. An agent can ask for a session, but only a click in the panel starts one. A config switch turns this off for a dedicated agent instance.
- **One bound document.** A session is tied to the document it was started in. Requests made while another document is active are rejected, and a change to any other open document fails the run. Only the user can move a session to another document, from the panel, and the agent must re-read the context before it does anything else there.
- **Live controls.** Start, pause and end. Permission toggles are deferred (see 1.3); until they land, the config policy applies to sessions as it does today.
- **Activity log.** Each action shows the agent's description, what the host observed, and the code that ran.
- **Change awareness.** The agent is told what the user changed since its last call.

Not in this plan:

- **Input forms.** That's Plan 2.
- **Non-modal approvals.** Under `ask`, approval keeps the modal prompt, because it must happen while the run's TransactionGroup is still open.
- **Stopping a running script.** The panel shares Revit's main thread, so Pause only stops new requests.
- **Undo from the log.** Revit's undo is a stack, so only the newest entry could be undone.
- **Several sessions per Revit instance.** One session at a time.
- **Translations beyond English.** The panel ships in English; the other locales the Settings window supports follow in a separate change.

Ground rules, so RFC #3567 never forces rework:

- **Keep the Python small.** Plan 1's only Python is the smartbutton, one Settings checkbox and the test harness. The button only sets its visibility and calls into C#: no `pyrevit.forms`, no Python handlers on Revit events, and every message comes from C#.
- **Build no general window host.** The RFC's Tier 5 C# host covers ExternalEvent marshaling, Dispatcher marshaling and pane registration for Python windows. The panel keeps its own versions internal (`AgentDispatcher` and a Shell-sized pane registration), so it can adopt Tier 5 later but never has to.
- **Don't load `pyrevit.forms` XAML or theme files from C#.** RFC Phase 2 restructures that folder.
- **New Python runs on IronPython 2 and passes `pipenv run check-py3`**, the RFC's checker, which isn't wired into CI yet.
- **Follow the Python Shell (#3480) for C# UI.** Copy its pane lifecycle (content built on first show, hidden on first idle), its theme dictionary of named brushes switched for Revit's dark theme, Segoe Fluent / MDL2 glyphs instead of bitmap icons, and AvalonEdit at the same version for code (from 1.4). The Shell's and the loader's theme detectors can't be shared without a new dependency for the separately deployed Shell or a loader refactor, so the panel has its own short reflection-only check that matches the loader's. Unlike the Shell's code-behind views, the panel uses view models, so its views can be replaced later.

## Plan 1 — Phases

Eight phases, each small enough to review on its own; 1.3 is deferred. The session model (1.1) comes before any UI, so the gating can be tested before the panel exists.

### 1.0 — Prerequisites

The runtime guarantees the panel relies on are already in place. #3684 fixed them before it merged:

- The policy is read when Revit starts the run and again before commit, and the stricter of the two wins (`0432ea38f`).
- The host watches the config file it actually loaded, including a local clone's (`95e5eefad`).
- Pipe connections idle for 30 seconds are closed, so one stalled client can't block every other request (`bd7ea1580`).

Decision: the panel is built in C#, in the Runtime project beside the agent host (see Plan 1 risks).

**Depends on:** #3684. **Done:** the reviewer findings were closed in #3684, and the panel decision is recorded here.

### 1.1 — Session model, no UI

Host-side session state that everything else hangs off.

- States: inactive → active ⇄ paused → ended. A session holds an id, the bound document and a start time. The session model has no Revit types, so it is unit-tested like the run decision logic.
- The check when Revit picks up a request is a single per-request permission check. The config policy is its only input until 1.3 adds the session's toggles.
- New config key `[agent] require_session`, read only when pyRevit loads, so a script or CLI command can't turn the gate off mid-session. It defaults to false in 1.1 and true from 1.2, when the panel exists. When false, the host behaves as #3684 does today.
- Gate every request that reads or changes the model. Return `session_inactive` or `paused_by_user` immediately, with a sentence the agent can relay to the user. `ping`, `lookup_revit_api` and the session requests stay open.
- Check the gate when a request arrives and again when Revit picks it up, so a pause also stops requests already queued.
- Bind to the document by the host's own reference to it, not by title or path. Runs act on the active document, so a request made while another document is active is rejected with `wrong_document`. Closing the bound document ends the session.
- Report session state in `ping`, which `list_revit_instances` shows, and in `get_context` during a session.
- Add `request_session`, a pipe request and MCP tool with an optional reason. In 1.1 the host records the request and reports it in session status; from 1.2 it opens the panel with a Start / Decline prompt, rate-limited.
- Add `pyrevit agent session status | request | pause | end`, with usage, help and autocomplete. The CLI can't start or resume a session; tests start one through an in-process call.
- Refuse session changes while a run executes, so run code can't resume or loosen its own session.
- Update the in-Revit Agent Tests to start a session on their scratch document.

**Depends on:** 1.0. **Done when:** unit tests cover every transition and gate, #3684's tests pass with `require_session = false`, and the in-Revit Agent Tests pass with it true.

### 1.2 — Panel shell

A dockable pane that starts, pauses and ends sessions and shows status.

- The host registers the pane on its first load at Revit startup, even when it is disabled, because a pane can't be registered on a pyRevit reload or removed. Turning the host on then needs only a reload. The pane builds its content the first time it opens; while the host is disabled, it is hidden at startup and says the host is off.
- A smartbutton next to Python Shell in pyRevitCore's slide-out opens the pane. It hides itself while the host is disabled, and calls into the host instead of repeating the pane id.
- Controls: Start session (binds to the active document), Pause / Resume, End. Hiding the pane pauses the session with `paused_by_host`, whether the user closed it or Revit hid it on its Home screen; only the user resumes it.
- A pending `request_session` shows the agent's reason with Start and Decline. Declining tells the agent the user said no. A request opens the pane at most once a minute.
- Status: the bound document, the policy, the MCP client that sent the last request, the last request with its result, and any request still waiting together with what holds it up (the approval prompt or an open Revit dialog). The panel shares Revit's main thread, so it can only redraw between requests or while a dialog is open; elapsed time would never be visible, and the pipe never queues more than one request. Each MCP call opens its own pipe connection, so the MCP server passes along the client name it gets at `initialize`.
- Native WPF in a status-card layout, bound to C# view models. The view is XAML embedded in the runtime and loaded with no code-behind, so the per-version runtime builds need no WPF markup compilation. Session logic stays out of the views, so a view can be replaced later (for example a WebView2 log, or the RFC's Tier 5 host and theme) without touching it.
- Update the UI through the WPF dispatcher only.
- Keep the strings in an English resource dictionary that follows the user's pyRevit locale setting, so translations can be added later.
- Add `require_session` to the agent section of the Settings window, and turn it on by default.

**Depends on:** 1.1. **Done when:** an in-Revit test button runs start → pause → resume → end, and hiding the pane pauses the session.

### 1.3 — Permission toggles (deferred)

Per-session permissions that the host enforces. Deferred: no other phase depends on it. Until it lands, Pause and End are the session's controls and the config policy decides what a run may change.

- Toggles: Read (`get_context`, `inspect_elements`, `run_query`, `run_automation`), Modify (off / ask / auto), Highlight elements (`show_elements`, `navigate_revit_link`), Capture view.
- The config supplies each new session's starting values. The session's values win, even over a config `readonly`, and a config change mid-session affects only the next session.
- Enforce in the host when Revit picks up the request and again at commit, as the policy is today, never in the UI alone.
- Changing a toggle applies to the next request, including requests already queued.
- Label honestly: queries run Python with your Windows permissions, and rollback protects the model, not your files.

**Depends on:** 1.2. **Done when:** a test flips Modify off while a modify request is queued, and that request is rejected.

### 1.4 — Activity log

Every agent action is readable: what it said, what happened, and the code behind it.

- MCP schema: the existing `title` (≤ 120 characters) becomes required on `run_query`, `run_modify`, `inspect_elements`, `show_elements`, `navigate_revit_link` and `capture_view`, plus an optional `reason` (≤ 300). `run_automation` takes its title from the automation. The MCP server refuses a missing, blank or overlong title; the host only trims, because the CLI and in-Revit callers send what they have. `run_modify`'s title stays the undo name.
- Run records gain the session id, reason and active document.
- The log keeps this Revit session's requests in memory (the latest 200). Run rows keep a summary and point to their run record on disk; other requests aren't written anywhere.
- Log rows, grouped by session: title, mode, status, change counts by category, duration and who approved. Expanding a row shows the code (plain monospace text), output, errors and engine.
- Element ids in the log select and zoom to the element through the existing show logic.
- Lookups that reach Revit (`lookup_revit_api`, `get_context`) sit behind a filter. `lookup_pyrevit_api`, `list_skills`, `get_skill`, `list_automation` and `get_run` run inside the CLI and never reach the host, so they don't appear.
- Flag rows where a run touched another document, a modify run changed nothing, or the host warned about a lost commit.

**Depends on:** 1.2. **Done when:** a scripted session's log matches its run records one for one.

### 1.5 — Change awareness and cross-document guard

The agent doesn't act on a stale picture, and other documents can't change silently.

- Between requests, track the user's edits to the bound document (counts, up to 20 sample ids per kind, transaction names, undo and redo), view switches and selection changes. Attach a `since_last_call` summary to the response of the agent's next model request, then start over. Ignore the host's own work, such as `show_elements` isolation, runs and the approval preview: nothing is recorded while the host handles a request. A new session starts with nothing to report. The MCP server keeps the summary in compact run results, and `run_automation` carries over the one its internal `get_context` received.
- The selection is compared, when the next request arrives, with the one the last request left behind, on every Revit version. `UIApplication.SelectionChanged` exists only from Revit 2023, and when Revit raises it for the host's own selection changes isn't something to rely on. A selection changed and changed back isn't reported, which is what the agent needs.
- During runs, #3684's guard already holds a group on every other open document, rolls back changes there, and fails the run with `other_document_modified`. This phase flags that run in the log and pauses the session. Requests are then refused with `paused_by_host`, whose message names the document; the panel says why the session paused, and only the user can resume it. A document the run opened from disk counts too, since the guard treats it as already open.
- When the guard can't roll back another document (`rollback_incomplete`), the log names the document to close without saving.
- Update the skills: re-read context whenever `since_last_call` is non-empty.

**Depends on:** 1.1, 1.4. **Done when:** tests cover each tracked event, and a script that edits a second open document fails and pauses the session.

### 1.6 — Move a session to another document

The user can keep one agent session across documents on purpose, never by accident.

Behaviour:

- While a session is open and another document is active, the panel offers "Move session to <document>" in place of Start. The panel decides by title; the move itself compares documents by reference on Revit's main thread and refuses with `already_bound` when the active document is the bound one. Two open documents with the same title hide the button; that's accepted.
- Switching documents in Revit alone still gets `wrong_document`, whose message now says the user can move the session in the panel or switch back. The agent can't move a session: no pipe request, CLI command or MCP tool does it.
- A move keeps the session id, its start time and its state. A paused session stays paused, including one paused by the host. Like start and resume, a move is refused with `session_locked` while a run executes, and with `session_inactive` when there is no session.
- Element ids belong to one document, so a notification alone isn't enough: a run the agent sends with the old document's ids could hit unrelated elements in the new one. After a move, every model request except `get_context` is refused with `session_moved`, naming both documents. The gate checks when a request arrives and again when Revit picks it up, so requests queued before the move are refused too. A paused session refuses with its pause code first, so the handshake waits until the user resumes.
- A successful `get_context` ends the handshake. Its response carries `since_last_call.session_moved` with the old and new document.
- Change awareness starts over on the new document. Closing the old document no longer ends the session; closing the new one does. This needs no new code, because the closing watch follows the bound document.

Implementation:

- Session tracker (no Revit types): `Move(document, title, now)` records the document history and sets the pending handshake. `Describe` adds `documents` (in order) and `awaiting_context`. The dequeue check takes the request kind, so `context` passes during the handshake.
- `AgentSessions.Move(UIApplication)`: main thread only, needs an active document. It moves the session, resets change awareness on the new document, then records the move for the next summary.
- Request handler: passes the request kind to the gate, and ends the handshake after a successful `get_context`.
- Panel: Move button and label, posted through the backend's `PostToRevit`, and a "Moved from A.rvt" note under the document line. While another document, or none, is active, an amber on-hold line says the session waits until the user switches back or moves it. The state stays Active or Paused: the agent gets `wrong_document`, and nothing needs resuming.
- Log: one group per session, its header naming the session's current document, plus a visible marker row where each move happened ("You moved the session from A.rvt to B.rvt."). Each row already records its own document, so element links still select in the right file.
- MCP server: `run_automation`'s internal `get_context` must not end the handshake on the agent's behalf. When that context reports `session_moved`, the server refuses with `session_moved` and passes the summary on, without running.
- Skills: on `session_moved`, call `get_context`, drop every id from the old document, and tell the user the agent now works in the new one.

**Depends on:** 1.1, 1.2, 1.5. **Done when:** unit tests cover the move, its refusals, the handshake for every request kind, the panel button and on-hold notice, the log header and marker, and the `run_automation` refusal; and an in-Revit test moves the session to the second scratch document, sees a run refused with `session_moved`, gets the move from `get_context`, runs against the new document, and checks that closing the old document leaves the session open while closing the new one ends it.

### 1.7 — Docs and rollout

- Add a session panel section to `docs/agent-runtime.md`.
- Add `require_session` to the configuration table.
- Upgrade note: with `require_session` on by default, agents get `session_inactive` until the user starts a session in the panel. An agent can call `request_session` to ask.
- A manual checklist with a real MCP client, in the style of #3709's.

**Depends on:** 1.1, 1.2, 1.4, 1.5 and 1.6. **Done when:** docs are reviewed and the manual checklist passes.

## Plan 1 — Risks and open questions

The panel is built in C# rather than Python; the biggest risk is users trusting descriptions more than they should.

| Risk | Mitigation |
| --- | --- |
| A Python panel depends on the RFC's Tier 5 work for CPython | Build the panel in C# beside the agent host; it needs no Python forms at all |
| Revit freezes, panel included, during long runs | Teach agents to work in small steps within `timeout_s`. Agent code doesn't use `pyrevit.forms`: the skills forbid it, and `ProgressBar` needs the RFC's Tier 5 under CPython |
| Users read descriptions as guarantees | Show host observations beside every description; descriptions are claims, not a security boundary |
| Agent runs and user edits share one undo stack | Say so in the docs; each agent run stays a single undo entry |
| Revit hides the pane on its Home screen, or the user closes it by accident | Hiding pauses the session instead of ending it; the agent gets `paused_by_host` and the user resumes in the panel |
| Log noise from many small calls | Group by session and hide lookups by default |
| An agent with shell access starts its own session | Only a click in the panel starts or resumes a session; `request_session` only asks |
| Run code changes the session or turns the gate off | Session changes are refused while a run executes, and `require_session` is read only at load. Like the policy, sessions guard against mistakes, not a hostile script |
| Once 1.3 lands, a session loosens an admin's config `readonly` | Accepted: the session wins. An admin lock remains an open question in the runtime docs |

Open questions:

- [x] C# or Python for the panel? C#, in the Runtime project beside the agent host.
- [ ] Should an idle session pause itself, e.g. after 30 minutes without requests?
- [ ] Should `request_session` take a document, so an agent can ask the user to move the session there (1.6)?
- [x] Should guard groups on every open document replace detection-only for cross-document changes? Already done in #3684.
- [x] Revit 2021–2022 have no selection-changed event (it arrived in 2023). Should the host compare the selection while Revit is idle, or skip selection tracking there? Neither: every version compares the selection when the next request arrives, so no event or idle polling is needed.
- [x] Does `description` replace `run_modify`'s `title`, which is also the undo name, or sit beside it? Neither: `title` stays and becomes required on every model tool.
- [x] Only `run` requests write run records today. Should `inspect_elements`, `show_elements` and `capture_view` get records too, so the log matches records one for one? No: the log keeps this Revit session in memory, and only runs write records.

## Plan 2 — Forms in the panel: goals

The agent can ask a question that waits in the panel; the user clicks Answer, a standard pyRevit form opens, and the agent gets element ids or values back.

Goals:

- **An `ask_user` tool** with a small, fixed set of forms.
- **Data only from the agent.** The host owns every line of form code.
- **Nothing blocks.** A waiting question holds neither Revit's main thread nor a pipe connection.
- **Provenance.** Every form says it comes from the agent, and why it's asking.
- **Checked answers.** Answers are validated against the model when the user submits them.

Not in this plan:

- **Agent-defined forms or XAML.**
- **Changes to the public `pyrevit.forms` API**, which the RFC freezes until its final phase.
- **CPython forms.** Those follow the RFC's tiers.
- **Zooming to an element while choosing it in a list.** That needs a forms hook (see Later).

## Plan 2 — Phases

Six phases. All of Plan 2 needs Plan 1's session model and panel; the forms themselves are today's pyRevit forms, wrapped by host-owned adapters.

### 2.0 — Form catalog and contract

Define what the agent can ask for, before building anything.

| Kind | Rendered with | Agent sends | Agent gets back |
| --- | --- | --- | --- |
| `choose_elements` | `forms.SelectFromList`, multi-select | element ids (≤ 200), optional note per item, min / max | chosen element ids |
| `pick_in_model` | pyRevit pick helpers inside `forms.WarningBar` | category as an `OST_` name, min / max | picked element ids |
| `choose_option` | `forms.CommandSwitchWindow` | message, 2–8 option labels | the chosen label |
| `confirm` | `forms.alert` with Yes / No | message | yes or no |
| `text` | `forms.ask_for_string` | prompt, optional default | the entered text |

- Every answer carries a status: answered, cancelled, dismissed, expired or stale.
- For element items, the agent sends only ids and an optional note. The host reads each element's mark, type and level from the model and builds the label itself.
- Categories use `OST_` names only; #3709 found that localized category names fail in non-English Revit.
- `ask_user` is one MCP tool whose `kind` field selects the form, with that form's fields alongside.

**Depends on:** Plan 1.1. **Done when:** the JSON schema exists, with tests for valid and invalid inputs of each kind.

### 2.1 — Question queue

Questions wait in the host, never in a held-open call.

- The host keeps pending questions per session: id, kind, spec, description, reason, created and expiry time.
- `ask_user` queues the question. The MCP server then checks the host every 2–3 seconds for about 20 seconds.
- Answered in that window → the result comes back in the same call. Otherwise the tool returns `pending` and a question id.
- `get_answer(question_id)` fetches the answer later.
- Each check is a short pipe request, so no connection stays open. Ending the session cancels its pending questions.
- Questions and answers go into the run records.

**Depends on:** 2.0, Plan 1.1. **Done when:** tests cover a fast answer, a slow answer through `get_answer`, expiry, and cancellation on session end.

### 2.2 — Question cards in the panel

- A card per pending question at the top of the panel: description, reason, kind, item count and age.
- Buttons: Answer and Dismiss. Answer is disabled while a run is executing or Revit has a dialog open.
- A visible indicator when a question arrives, such as a count in the panel header.

**Depends on:** 2.1, Plan 1.2. **Done when:** an in-Revit test shows, answers and dismisses a question.

### 2.3 — Form adapters

Clicking Answer runs a host-owned adapter that opens the standard form.

- Answer → ExternalEvent → the host runs the adapter script through its existing script executor, on IronPython until the RFC's Tier 4 brings list forms to CPython.
- Each adapter builds items that carry both a label and an element id, calls the form, and maps the result back to ids.
- A closed window is `cancelled`, kept distinct from an empty selection.
- Provenance for now: "Agent asks: …" in each form's title or message, because the forms have no header slot yet.
- Picking in the model runs outside any transaction group; the adapter is host-owned and read-only.
- Agent-supplied text is always shown as plain text.

**Depends on:** 2.2. **Done when:** one in-Revit test per kind passes, including the cancel path.

### 2.4 — Answer validation

- On submit, check that each element still exists, is in the bound document and matches the expected category. Otherwise return `stale` with the failing ids.
- After answering, briefly highlight the chosen elements so the user sees what they picked.

**Depends on:** 2.3. **Done when:** a test that deletes an element between asking and answering gets `stale`.

### 2.5 — Agent guidance and logging

- Skill text: when to ask versus decide, to always use `ask_user` rather than calling `pyrevit.forms` in run code, and how to handle `pending` (tell the user, then call `get_answer`).
- Optional default: during agent runs, the runner makes `pyrevit.forms` raise "use ask\_user". This is a guard rail, not a security boundary.
- Questions and answers appear in the activity log, inside their session group.

**Depends on:** 2.3, Plan 1.4. **Done when:** a scripted MCP session runs query doors → ask the user → modify with the answer passed in `inputs`.

## Plan 2 — Risks and open questions

The main remaining weakness is that agent code can still draw its own windows; provenance labels and the log are the real defense.

| Risk | Mitigation |
| --- | --- |
| Agent run code imports WPF and imitates a form or the approval prompt | Provenance text on every host form, the log, and the optional `pyrevit.forms` guard rail; not fully preventable in-process |
| The agent's turn ends while a question is pending | Skill text tells the agent to say it's waiting; the user returns to the chat to continue |
| Modal forms freeze Revit while open | The user opened the form deliberately, so this is expected |
| Adapters pinned to IronPython while the runtime defaults to CPython | Host-owned adapters choose their own engine; revisit when the RFC's Tier 4 lands |
| Lists too long to scan | Cap at 200 items; past that, the agent uses `pick_in_model` |

Open questions:

- [ ] Default question expiry: 15 minutes?
- [ ] Several pending questions: answer in order, or any order?
- [ ] Can a submitted answer be withdrawn before the agent reads it?
- [ ] Should a dismissed question tell the agent why, via an optional comment?
- [ ] How does `ask_user` relate to the "forms agent mode" that `docs/agent-runtime.md` plans for Phase 3, where `forms` prompts read `agent.inputs` and return `needs_input`?

## Later — A forms spec layer, aligned with RFC #3567

Once the RFC's Phase 2 split lands, propose an additive spec layer in `pyrevit.forms`; Plan 2's adapters then shrink to "pass the spec through."

- **Timing.** RFC Phase 2 promises zero behavior change and an identical public API, so the spec layer comes after it as a new module, such as `forms.show_spec(spec)`. Existing calls are untouched.
- **What it adds.** A serializable spec in and a status plus ids out; an optional provenance header; element-aware items with a selection-changed hook, so choosing an item can zoom to it.
- **Why the RFC benefits.** A thread comment asks that the standard forms stay renderer-agnostic, so a backend like WebView2 can come later. A spec layer is that seam, which makes it a general proposal rather than an agent-only one.
- **CPython.** List forms follow the RFC's Tier 4. If the panel were ever moved to Python, it would follow Tier 5's C# window host.
- **A partial test case for Tier 5.** RFC Phase 3 names a modeless window driving Revit through ExternalEvent as the likeliest deadlock. The agent panel exercises the ExternalEvent and Dispatcher half of that path daily. It is C#, so it never takes Python's interpreter lock, the part the RFC worries about most.
