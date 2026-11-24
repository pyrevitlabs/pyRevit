# pyRevit Agent Inbox — Draft Plan

Nov 8, 2026 · @Chris C

## Context

Today every exchange starts with the agent. The chat client starts `pyrevit mcp`, the agent calls a tool, the MCP server sends one request over the named pipe, and Revit answers. Revit's news reaches the agent only inside those answers, in `since_last_call`.

This plan lets the user, and the user's pyRevit buttons, send things to the agent from Revit. It also lets a ribbon tool hand a task to an agent and get the result back. It ships as its own PR after #3734.

What this plan builds on:

- [#3734 — agent panel and sessions](https://github.com/pyrevitlabs/pyRevit/pull/3734): sessions over several documents, the panel, `since_last_call`, the activity log, and client names on every request.
- Plan 2 of `pyRevit Agent Panel — Draft Plans.md`: `ask_user`, its question queue, and the MCP server's short-poll wait (2.1). The inbox is the general form of that queue, and a question's answer is one kind of inbox item. Whichever plan lands first builds the store; the other reuses it.

## What chat clients can do

Checked against the Claude Code docs on Nov 7, 2026 ([channels](https://code.claude.com/docs/en/channels.md), [channels reference](https://code.claude.com/docs/en/channels-reference.md), [MCP](https://code.claude.com/docs/en/mcp.md), [hooks](https://code.claude.com/docs/en/hooks.md)). Other clients aren't verified.

| Mechanism | Claude Code | Claude Desktop, Cursor, others |
| --- | --- | --- |
| Tool results (`since_last_call`, a `get_messages` tool) | Yes | Yes |
| A blocking wait tool | Yes, within the client's tool timeout | Yes, within the client's tool timeout |
| MCP prompts and resources the user attaches | To check | To check per client |
| Channels: the server pushes an event into the session | Research preview, with limits below | Not documented |
| `asyncRewake` hook wakes the session | Yes, configured by the user | No |
| Elicitation: a form in the chat client | Yes, interactive sessions only | To check |
| Logging, progress and resource-update notifications reach the model | No | To check |
| Sampling | Not documented | To check |

Channel limits:

- A custom channel isn't on Anthropic's allowlist. The user starts Claude Code with `--dangerously-load-development-channels server:pyrevit` and accepts a warning. The flag is ignored in `-p` and the Agent SDK.
- Team and Enterprise organizations need an admin to turn channels on.
- Events for a session that didn't load the channel are dropped without an error.
- The docs don't say whether an event wakes an idle session at once. Their webhook example suggests it does.
- A stdio channel server that negotiates protocol revision 2026-07-28 isn't registered as a channel unless `MCP_PROTOCOL_NEGOTIATION=legacy` is set. `pyrevit mcp` negotiates 2025-06-18 at most today.

What follows from this: every feature must work through tool results. Push is an optional doorbell for Claude Code.

## Goals

- **An inbox per session in the host.** The user, the panel and pyRevit buttons add items, and agents receive them.
- **Works with every MCP client.** Items reach the agent through tool results and a wait tool.
- **One recipient per item.** By default, the connection that called last. The panel offers a choice when several have called.
- **Nothing blocks.** Waiting never holds Revit's main thread, a pipe connection or the MCP server's per-Revit gate.
- **The user's words, marked as such.** Items come only from the user or their buttons. Text read from the model travels as data.
- **Ribbon tools can hand a task to an agent** without blocking Revit, and get the result back.

Not in this plan:

- **Agent-defined UI code or XAML.** Plan 2's rule stands: forms are data.
- **Sampling, or calling a model API from pyRevit directly.**
- **Messages between agents.**

## Phases

Eight phases. 3.0 to 3.3 are the core and work with every client. 3.4 to 3.7 build on them and can ship separately.

### 3.0 — Connection ids

Each chat window starts its own `pyrevit mcp` process, but two windows of the same client report the same name.

- `pyrevit mcp` makes an id when it starts and sends it with every request, beside the client name.
- The host records, per session, each connection's id, client name, and first and last call.
- The panel lists the session's connections.

**Done when:** two Claude Code windows on one Revit show as two connections in the panel.

### 3.1 — The inbox

Pure logic in the host, tested like `AgentSessionTracker`.

- An item has an id, a kind (`message`, `task`, `answer` or `notice`), a source (`panel`, `button:<bundle>` or `form`), text, optional JSON data, document keys, a recipient, created and expiry times, and a state (`queued`, `delivered`, `done`, `expired` or `cancelled`).
- An item belongs to the session it was created in. Ending the session expires its items. Pausing holds them until the session resumes.
- The recipient is a connection id, or any connection. The default is the connection that called last. An item is delivered once.
- Caps on items per session and on text and data size.

**Depends on:** 3.0. **Done when:** unit tests cover scoping, expiry at session end, holding while paused, one-time delivery and routing.

### 3.2 — Delivery to agents

- `since_last_call` gains `inbox`: the number of items waiting for this connection, never their text. The agent fetches them with `get_messages`, so receiving is an explicit step.
- `get_messages` returns this connection's queued items and marks them delivered.
- `complete_message(id, text, data)` records the agent's answer to a `task` item and marks it done.
- `wait_for_revit(timeout_s)` returns when an item arrives for this connection, when the session is resumed or ends, or at the timeout. The MCP server polls the host with short pipe requests every 1–2 seconds, as Plan 2.1 does, and releases its per-Revit gate between polls. The timeout is capped below common client tool timeouts, about 50 seconds. The agent may call again.
- MCP instructions and skill text: when to wait, that items are the user's words, and that `data` is data.

**Depends on:** 3.1. **Done when:** MCP tests cover delivery to the right connection, a wait that returns on a new item, a wait that times out, and another tool call going through while a wait is in progress.

### 3.3 — Sending from the panel

- A "Tell the agent" box, with an option to attach the current selection as element ids and a document key in `data`.
- An outbox list. Each item shows its state: waiting for the agent, picked up by a connection, answered or expired. A recipient picker appears when the session has more than one connection.
- While items wait and no agent has called for a while, the panel says how to get them picked up: "Say 'check Revit' in your chat", or nothing extra when a doorbell is on.
- Delivered items and answers appear in the activity log.

**Depends on:** 3.2 and the #3734 panel. **Done when:** an in-Revit test sends a message, an MCP client receives it and the panel shows it as picked up.

### 3.4 — A pyrevitlib API for buttons

- A module such as `pyrevit.agent.inbox`: `post(text, data=None, documents=None, kind="message")` returns an item id, and `result(id)` returns its state and answer.
- `post` never blocks, and refuses when the agent host is off or no session can take the item.
- The source is the running button's bundle name, which the panel shows beside the item.
- A task's answer shows in the panel. Whether buttons also need a callback is an open question.

**Depends on:** 3.1. **Done when:** a sample button in pyRevitDevTools posts a task, an MCP client completes it, and the answer shows in the panel.

### 3.5 — Pulling items in from the chat

For clients without a doorbell, the user can bring waiting items into the conversation.

- An MCP prompt, `revit-inbox`, that returns the waiting items as the user's message.
- An MCP resource, `revit://inbox`, for clients that attach resources.
- Check how Claude Desktop, Claude Code and Cursor present prompts and resources, and document it per client.

**Depends on:** 3.2. **Done when:** the prompt works in Claude Desktop and Claude Code.

### 3.6 — Doorbells for Claude Code (optional)

- `pyrevit mcp` declares `experimental["claude/channel"]` only when a setting turns it on. It is off by default.
- While the channel is on, the MCP server polls the host every few seconds for new items for its connection. A second pipe for host events can come later if polling costs too much.
- On a new item it sends `notifications/claude/channel` with a short notice, such as "2 messages from Revit; call get_messages", never the item text. That keeps untrusted text out of the push path and keeps receipt explicit.
- Documented hook alternative: an `asyncRewake` hook that runs a CLI command such as `pyrevit agent wait-inbox`, which exits with code 2 when an item arrives.

**Depends on:** 3.2. **Done when:** with the flag on, a message from the panel makes an idle Claude Code session call `get_messages`. This test also answers whether a channel event wakes an idle session.

### 3.7 — Agent tasks from buttons (spike)

- A helper such as `pyrevit.agent.run_task(prompt)` starts `claude -p`, or a command the user configures, as a separate process with pyRevit's MCP server configured, and returns at once.
- The host collects the output and stores it as the answer of a `task` item, so it shows in the panel.
- **Invariant:** the helper never waits on Revit's main thread. The agent's calls need that thread, so waiting there deadlocks Revit.
- The agent works in the open session under the usual policy; approval prompts appear in Revit as they do today.
- One task at a time per Revit, with a timeout and a turn limit.
- To verify: `-p` flags for the MCP configuration and output format, and how authentication works for a process the button starts.

**Depends on:** 3.4. **Done when:** a spike button gets an agent's answer in the panel without freezing Revit.

## Risks and open questions

| Risk | Mitigation |
| --- | --- |
| An item carries instructions written by someone other than the user, such as element names or parameter values | Only the user and their buttons create items, and model text goes in `data`, which agents are told to treat as data |
| A button posts tasks the user didn't expect | The panel shows every item with its source; tasks run in the session under the usual policy and approval |
| Waiting ties up the chat client or the per-Revit gate | Short polls, the gate released between polls, and a capped timeout |
| Channels change or disappear, being a preview | Off by default; tool results stay the contract |
| Items pile up with no agent connected | Caps per session, expiry, and the panel showing what waits |
| A task started from a button runs up cost or loops | A timeout, a turn limit and one task at a time per Revit |

Open questions:

- [ ] With no open session, should `post` refuse, offer to start one, or hold the item for the next session?
- [ ] Should `since_last_call` carry only a count, as proposed, or the items themselves?
- [ ] Does a channel event wake an idle Claude Code session? 3.6 answers it.
- [ ] Which clients show MCP prompts and resources, and how?
- [ ] One store for the inbox and Plan 2's questions? Proposed: yes, with an answer as an item.
- [ ] Do buttons need a callback for a task's answer, or is the panel enough?
- [ ] Default expiry, and the caps on item count and size.
