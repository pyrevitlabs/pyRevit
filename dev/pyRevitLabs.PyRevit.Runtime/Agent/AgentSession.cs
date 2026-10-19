using System;
using System.Collections.Generic;

using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    internal enum AgentSessionState {
        Inactive,
        Active,
        Paused,
    }

    internal static class AgentSessionEndReasons {
        public const string EndedInRevit = "ended_in_revit";
        public const string EndedByClient = "ended_by_client";
        public const string DocumentClosed = "document_closed";
        public const string HostStopped = "host_stopped";
    }

    internal static class AgentSessionPauseCauses {
        public const string OtherDocument = "other_document";
        public const string PanelHidden = "panel_hidden";
        public const string Agent = "agent";
    }

    /// <summary>
    /// The user's consent for agents to work on one document: the session state machine and the
    /// gate that every model request passes. Pure logic with no Revit dependency;
    /// <see cref="AgentSessions"/> connects it to Revit.
    /// </summary>
    /// <remarks>
    /// A session goes inactive → active ⇄ paused → inactive. Ending one returns to inactive and
    /// remembers why, so the next refusal can tell the agent. The user can move an open session
    /// to another document; it keeps its id, start time and state.
    /// Invariants:
    /// <list type="bullet">
    /// <item>While <see cref="Required"/> is true, no model request passes without an active
    /// session.</item>
    /// <item>Whether or not sessions are required, a paused session refuses model requests, and an
    /// active one refuses requests made while another document is active.</item>
    /// <item>After a move, or once a session starts on a document other than the one the agent
    /// last read the context in, every model request except a context read is refused with
    /// <c>session_moved</c> until the agent reads the context, because element ids from the old
    /// document don't apply in the new one. Each such change advances the
    /// <see cref="Generation"/>, and a request from a client that last read an older one is
    /// refused the same way, so one client reading the context doesn't end another's wait.</item>
    /// <item>Nothing that loosens the gate succeeds while an agent run executes, so run code can't
    /// grant itself access: starting, resuming, moving, making sessions optional, or ending a
    /// session while sessions aren't required. Pausing always succeeds, and so does ending while
    /// sessions are required.</item>
    /// <item>While sessions aren't required, an agent can't end a session over the pipe either,
    /// because that would let agents work in any document.</item>
    /// </list>
    /// The bound document is an opaque reference; callers decide what counts as the same document.
    /// Every member is safe to call from any thread. <see cref="Changed"/> is raised on the thread
    /// that made the change, after the tracker's lock is released.
    /// </remarks>
    internal sealed class AgentSessionTracker {
        public const int MaxReasonLength = 300;

        private readonly object sync = new object();
        private AgentSessionState state = AgentSessionState.Inactive;
        private bool required;
        private int runsExecuting;
        private string sessionId;
        private object boundDocument;
        private string documentTitle;
        private readonly List<string> documents = new List<string>();
        private string movedFrom;
        private object movedFromDocument;
        private bool startedElsewhere;
        private object lastDocument;
        private string lastDocumentTitle;
        private int generation;
        private DateTime startedUtc;
        private JObject pendingRequest;
        private JObject lastDeclined;
        private string pausedCause;
        private string pausedReason;
        private JObject lastEnded;

        public event Action Changed;

        public bool Required {
            get {
                lock (sync)
                    return required;
            }
        }

        public AgentSessionState State {
            get {
                lock (sync)
                    return state;
            }
        }

        public object BoundDocument {
            get {
                lock (sync)
                    return boundDocument;
            }
        }

        /// <summary>The id of the active or paused session, or null when there is none.</summary>
        public string SessionId {
            get {
                lock (sync)
                    return state == AgentSessionState.Inactive ? null : sessionId;
            }
        }

        /// <summary>
        /// The active or paused session's id and document title, read together; both null when
        /// there is no session.
        /// </summary>
        public (string Id, string Document) CurrentSession {
            get {
                lock (sync)
                    return state == AgentSessionState.Inactive ? (null, null) : (sessionId, documentTitle);
            }
        }

        /// <summary>
        /// Counts the changes of document that invalidate the agent's element ids: moves, and
        /// sessions started on another document than the one the agent last read the context in.
        /// It only grows, for the life of the process.
        /// </summary>
        public int Generation {
            get {
                lock (sync)
                    return generation;
            }
        }

        /// <summary>
        /// The document the agent last read the context in, while the open session waits for it
        /// to read the context again; otherwise null.
        /// </summary>
        public string AwaitingContextFrom {
            get {
                lock (sync)
                    return state == AgentSessionState.Inactive ? null : movedFrom;
            }
        }

        /// <exception cref="AgentException">
        /// <c>session_locked</c> when making sessions optional while an agent run executes.
        /// </exception>
        public void SetRequired(bool value) {
            lock (sync) {
                if (required == value)
                    return;
                if (!value)
                    RefuseWhileRunExecutes("Agent sessions can't be made optional while an agent run executes.");
                required = value;
            }
            OnChanged();
        }

        /// <summary>
        /// Starts a session bound to <paramref name="document"/>. When an earlier session left the
        /// agent with element ids from another document, the new one waits for the agent to read
        /// the context, as after a move.
        /// </summary>
        /// <param name="isThisDocument">
        /// Whether the document the agent last read the context in is <paramref name="document"/>;
        /// called under the tracker's lock. Without it, only the same reference counts.
        /// </param>
        /// <returns>The new session's id.</returns>
        /// <exception cref="AgentException">
        /// <c>session_active</c> when a session is already active or paused, or
        /// <c>session_locked</c> while an agent run executes.
        /// </exception>
        public string Start(object document, string title, DateTime nowUtc, Func<object, bool> isThisDocument = null) {
            if (document == null)
                throw new ArgumentNullException(nameof(document));
            string id;
            lock (sync) {
                RefuseWhileRunExecutes("An agent session can't be started while an agent run executes.");
                if (state != AgentSessionState.Inactive)
                    throw new AgentException("session_active",
                        $"An agent session is already active on '{documentTitle}'. End it before starting another.");
                var isStartDocument = isThisDocument ?? (candidate => ReferenceEquals(candidate, document));
                var elsewhere = lastDocument != null && !isStartDocument(lastDocument);
                state = AgentSessionState.Active;
                id = sessionId = Guid.NewGuid().ToString("N").Substring(0, 12);
                boundDocument = document;
                documentTitle = title;
                documents.Clear();
                documents.Add(title);
                movedFrom = elsewhere ? lastDocumentTitle : null;
                movedFromDocument = elsewhere ? lastDocument : null;
                startedElsewhere = elsewhere;
                if (elsewhere)
                    generation++;
                lastDocument = null;
                lastDocumentTitle = null;
                startedUtc = nowUtc;
                pendingRequest = null;
                lastDeclined = null;
            }
            OnChanged();
            return id;
        }

        /// <summary>
        /// Moves the open session to another document, keeping its id, start time and state.
        /// Until the agent reads the context, every other model request is refused with
        /// <c>session_moved</c>.
        /// </summary>
        /// <remarks>
        /// The caller has checked that <paramref name="document"/> isn't the bound one; the tracker
        /// can't compare documents.
        /// </remarks>
        /// <returns>
        /// The document the agent last read the context in: the previous one, or the first of
        /// several moves the agent hasn't caught up with.
        /// </returns>
        /// <exception cref="AgentException">
        /// <c>session_inactive</c> when there is no session, or <c>session_locked</c> while an
        /// agent run executes.
        /// </exception>
        public string Move(object document, string title, DateTime nowUtc) {
            if (document == null)
                throw new ArgumentNullException(nameof(document));
            string from;
            lock (sync) {
                RefuseWhileRunExecutes("An agent session can't be moved while an agent run executes.");
                if (state == AgentSessionState.Inactive)
                    throw new AgentException("session_inactive", "There is no agent session to move.");
                if (movedFrom == null) {
                    movedFrom = documentTitle;
                    movedFromDocument = boundDocument;
                }
                startedElsewhere = false;
                generation++;
                from = movedFrom;
                boundDocument = document;
                documentTitle = title;
                documents.Add(title);
            }
            OnChanged();
            return from;
        }

        /// <summary>
        /// Follows the bound document to the title it was saved under. The caller has checked that
        /// the saved document is the bound one.
        /// </summary>
        /// <returns>False when there is no session or the title didn't change.</returns>
        public bool Retitle(string title) {
            lock (sync) {
                if (state == AgentSessionState.Inactive || string.IsNullOrEmpty(title) || title == documentTitle)
                    return false;
                documentTitle = title;
                documents[documents.Count - 1] = title;
            }
            OnChanged();
            return true;
        }

        /// <summary>
        /// Records that the agent read the context, which ends the handshake after a move or a
        /// session started elsewhere. With no session open, the document it read in is the one
        /// the next session's document is compared with.
        /// </summary>
        /// <param name="activeDocument">
        /// The active document the context described, or null when none was active, which keeps
        /// the document the agent read in before.
        /// </param>
        public void ContextRead(object activeDocument, string activeTitle) {
            lock (sync) {
                if (state == AgentSessionState.Inactive) {
                    if (activeDocument != null) {
                        lastDocument = activeDocument;
                        lastDocumentTitle = activeTitle;
                    }
                    return;
                }
                if (movedFrom == null)
                    return;
                movedFrom = null;
                movedFromDocument = null;
                startedElsewhere = false;
            }
            OnChanged();
        }

        /// <summary>
        /// Pauses an active session for code running in Revit: the user's pause, or, while an
        /// agent run executes, a pause by its code, which the next refusal reports as the agent's.
        /// Pausing a paused one changes nothing, so a pause keeps whose it was.
        /// </summary>
        /// <exception cref="AgentException"><c>session_inactive</c> when there is no session.</exception>
        public void Pause() {
            bool paused;
            lock (sync)
                paused = runsExecuting > 0
                    ? PauseLocked(AgentSessionPauseCauses.Agent, "code in an agent run paused it.")
                    : PauseLocked(null, null);
            if (paused)
                OnChanged();
        }

        /// <summary>
        /// Pauses an active session for an agent that asked over the pipe, so its next refusal is
        /// <c>paused_by_agent</c> rather than a pause the user made. Pausing a paused one changes
        /// nothing.
        /// </summary>
        /// <exception cref="AgentException"><c>session_inactive</c> when there is no session.</exception>
        public void PauseForAgent() {
            bool paused;
            lock (sync)
                paused = PauseLocked(AgentSessionPauseCauses.Agent, "an agent paused it.");
            if (paused)
                OnChanged();
        }

        /// <summary>
        /// Pauses the session on the host's own account, for example after a run changed another
        /// document, so the agent's next refusal is <c>paused_by_host</c> and says why. A pause by
        /// the user becomes a pause by the host; an earlier pause by the host or an agent keeps its
        /// reason.
        /// </summary>
        /// <param name="cause">One of <see cref="AgentSessionPauseCauses"/>, for the panel.</param>
        /// <param name="reason">Why, for the agent, as a sentence fragment that follows "because".</param>
        /// <returns>False when there is no session, or the host has already paused it.</returns>
        public bool PauseByHost(string cause, string reason) {
            lock (sync) {
                if (state == AgentSessionState.Inactive || pausedReason != null)
                    return false;
                state = AgentSessionState.Paused;
                pausedCause = cause;
                pausedReason = reason;
            }
            OnChanged();
            return true;
        }

        /// <summary>
        /// Resumes the session. That answers an agent's pending request, and a decline the user
        /// made while it was paused no longer applies.
        /// </summary>
        /// <exception cref="AgentException">
        /// <c>session_inactive</c> when there is no session, or <c>session_locked</c> while an
        /// agent run executes.
        /// </exception>
        public void Resume() {
            lock (sync) {
                RefuseWhileRunExecutes("An agent session can't be resumed while an agent run executes.");
                if (state == AgentSessionState.Inactive)
                    throw new AgentException("session_inactive", "There is no agent session to resume.");
                state = AgentSessionState.Active;
                pendingRequest = null;
                lastDeclined = null;
                pausedCause = null;
                pausedReason = null;
            }
            OnChanged();
        }

        /// <summary>
        /// Ends the session for one of the host's own reasons, such as the host stopping.
        /// </summary>
        /// <returns>False when there was no session to end.</returns>
        public bool End(string reason, DateTime nowUtc) {
            bool ended;
            lock (sync)
                ended = EndLocked(reason, nowUtc);
            if (ended)
                OnChanged();
            return ended;
        }

        /// <summary>
        /// Ends the session for code running in Revit: the agent panel, or any script.
        /// </summary>
        /// <returns>False when there was no session to end.</returns>
        /// <exception cref="AgentException">
        /// <c>session_locked</c> while an agent run executes and sessions aren't required.
        /// </exception>
        public bool EndInRevit(DateTime nowUtc) {
            bool ended;
            lock (sync) {
                if (!required && state != AgentSessionState.Inactive)
                    RefuseWhileRunExecutes(
                        "Agent sessions aren't required in this Revit, so the session can't be ended while an agent run executes: "
                        + "that would let agents work in any open document.");
                ended = EndLocked(AgentSessionEndReasons.EndedInRevit, nowUtc);
            }
            if (ended)
                OnChanged();
            return ended;
        }

        /// <summary>
        /// Ends the session for an agent that asked over the pipe.
        /// </summary>
        /// <returns>False when there was no session to end.</returns>
        /// <exception cref="AgentException"><c>session_locked</c> while sessions aren't required.</exception>
        public bool EndForAgent(DateTime nowUtc) {
            bool ended;
            lock (sync) {
                if (!required && state != AgentSessionState.Inactive)
                    throw new AgentException("session_locked",
                        "Agent sessions aren't required in this Revit, so ending this one would let agents work in any open "
                        + "document. Only the user can end it, in the agent panel. Pause it if you need to stop.");
                ended = EndLocked(AgentSessionEndReasons.EndedByClient, nowUtc);
            }
            if (ended)
                OnChanged();
            return ended;
        }

        /// <summary>
        /// Ends the session only while it is still bound to <paramref name="document"/>, so a
        /// late notice about a closed document can't end a newer session.
        /// </summary>
        public bool EndIfBoundTo(object document, string reason, DateTime nowUtc) {
            bool ended;
            lock (sync)
                ended = ReferenceEquals(boundDocument, document) && EndLocked(reason, nowUtc);
            if (ended)
                OnChanged();
            return ended;
        }

        /// <summary>
        /// Records an agent's request for a session, replacing an earlier one.
        /// </summary>
        /// <returns>False when a session is already active, so there is nothing to request.</returns>
        /// <exception cref="AgentException"><c>invalid_params</c> when the reason is too long.</exception>
        public bool Request(string reason, DateTime nowUtc) {
            var trimmed = reason?.Trim();
            if (trimmed != null && trimmed.Length > MaxReasonLength)
                throw new AgentException("invalid_params", $"'reason' must be at most {MaxReasonLength} characters.");
            lock (sync) {
                if (state == AgentSessionState.Active)
                    return false;
                pendingRequest = new JObject {
                    ["reason"] = string.IsNullOrEmpty(trimmed) ? JValue.CreateNull() : new JValue(trimmed),
                    ["requested"] = nowUtc.ToString("o"),
                };
                lastDeclined = null;
            }
            OnChanged();
            return true;
        }

        /// <summary>
        /// Declines the pending request, so the agent's next refusal says the user said no.
        /// </summary>
        /// <returns>False when no request is pending.</returns>
        public bool Decline(DateTime nowUtc) {
            lock (sync) {
                if (pendingRequest == null)
                    return false;
                lastDeclined = (JObject)pendingRequest.DeepClone();
                lastDeclined["declined"] = nowUtc.ToString("o");
                pendingRequest = null;
            }
            OnChanged();
            return true;
        }

        /// <summary>
        /// Marks an agent run as executing until the returned scope is disposed.
        /// </summary>
        public IDisposable BeginRun() {
            lock (sync)
                runsExecuting++;
            return new RunScope(this);
        }

        /// <summary>
        /// The gate when a request arrives, before it waits for Revit.
        /// </summary>
        /// <param name="readsContext">Whether the request is <c>get_context</c>, which passes during a move's handshake.</param>
        /// <param name="contextGeneration">
        /// The <see cref="Generation"/> the request's client last read in the context, when it says.
        /// </param>
        /// <exception cref="AgentException">
        /// <c>paused_by_user</c>, <c>paused_by_host</c>, <c>paused_by_agent</c>, <c>session_moved</c> or <c>session_inactive</c>.
        /// </exception>
        public void CheckOnArrival(bool readsContext, int? contextGeneration = null) {
            lock (sync)
                CheckStateLocked(readsContext, contextGeneration);
        }

        /// <summary>
        /// The gate when Revit picks the request up, which also catches a pause or a document
        /// switch while the request was queued.
        /// </summary>
        /// <param name="isBoundDocumentActive">
        /// Whether the bound document is the active one; called under the tracker's lock, on the
        /// thread that may compare documents.
        /// </param>
        /// <param name="activeTitle">Title of the active document, or null when none is active.</param>
        /// <param name="readsContext">Whether the request is <c>get_context</c>, which passes during a move's handshake.</param>
        /// <param name="contextGeneration">
        /// The <see cref="Generation"/> the request's client last read in the context, when it says.
        /// </param>
        /// <exception cref="AgentException">
        /// <c>paused_by_user</c>, <c>paused_by_host</c>, <c>paused_by_agent</c>, <c>session_moved</c>, <c>session_inactive</c> or
        /// <c>wrong_document</c>.
        /// </exception>
        public void CheckOnDequeue(
            Func<object, bool> isBoundDocumentActive, string activeTitle, bool readsContext, int? contextGeneration = null) {
            lock (sync) {
                CheckStateLocked(readsContext, contextGeneration);
                if (state != AgentSessionState.Active || isBoundDocumentActive(boundDocument))
                    return;
                var active = activeTitle == null ? "no document is active" : $"'{activeTitle}' is the active document";
                throw new AgentException("wrong_document",
                    $"The agent session is bound to '{documentTitle}', but {active} in Revit. "
                    + $"Ask the user to switch back to '{documentTitle}', or to move the session to the active document in the agent panel.");
            }
        }

        public JObject Describe() {
            lock (sync) {
                var isOpen = state != AgentSessionState.Inactive;
                return new JObject {
                    ["required"] = required,
                    ["state"] = StateName(state),
                    ["id"] = isOpen ? sessionId : null,
                    ["document"] = isOpen ? documentTitle : null,
                    ["documents"] = isOpen ? new JArray(documents) : null,
                    ["awaiting_context"] = isOpen && movedFrom != null,
                    ["generation"] = generation,
                    ["started"] = isOpen ? startedUtc.ToString("o") : null,
                    ["paused_cause"] = state == AgentSessionState.Paused ? pausedCause : null,
                    ["paused_reason"] = state == AgentSessionState.Paused ? pausedReason : null,
                    ["pending_request"] = pendingRequest?.DeepClone(),
                    ["declined_request"] = lastDeclined?.DeepClone(),
                    ["last_ended"] = lastEnded?.DeepClone(),
                };
            }
        }

        private void CheckStateLocked(bool readsContext, int? contextGeneration) {
            if (state == AgentSessionState.Paused && pausedCause == AgentSessionPauseCauses.Agent)
                throw new AgentException("paused_by_agent",
                    $"The agent session is paused because {pausedReason} Only the user can resume it, in Revit: tell them, "
                    + "and try again after they do.");
            if (state == AgentSessionState.Paused && pausedReason != null)
                throw new AgentException("paused_by_host",
                    $"The agent session is paused because {pausedReason} Tell the user; only they can resume the session in Revit.");
            if (state == AgentSessionState.Paused)
                throw new AgentException("paused_by_user",
                    "The user paused the agent session in Revit. Tell the user you are waiting, and try again after they resume it.");
            if (state == AgentSessionState.Active && movedFrom != null && !readsContext)
                throw new AgentException("session_moved", startedElsewhere
                    ? $"The user started a new agent session on '{documentTitle}'. You last read the context in '{movedFrom}', "
                        + $"and its element ids don't apply in '{documentTitle}'. Call get_context before anything else."
                    : $"The user moved the agent session from '{movedFrom}' to '{documentTitle}'. Element ids from '{movedFrom}' "
                        + $"don't apply in '{documentTitle}'. Call get_context before anything else.");
            if (state == AgentSessionState.Active && !readsContext && contextGeneration.HasValue && contextGeneration.Value != generation)
                throw new AgentException("session_moved",
                    $"The agent session is now on '{documentTitle}', and you haven't read the context there. Element ids from "
                    + "the document you last read don't apply in it. Call get_context before anything else.");
            if (state != AgentSessionState.Inactive || !required)
                return;
            if (lastDeclined != null)
                throw new AgentException("session_inactive",
                    "The user declined your request for an agent session in Revit. Ask them in the conversation "
                    + "before you call request_session again.");
            var ended = lastEnded != null && lastEnded.Value<string>("reason") == AgentSessionEndReasons.DocumentClosed
                ? $"The agent session ended because its document '{lastEnded.Value<string>("document")}' was closed. "
                : string.Empty;
            throw new AgentException("session_inactive",
                ended + "No agent session is active in this Revit. Ask the user to start one in Revit; "
                + "request_session tells them you are asking.");
        }

        private bool PauseLocked(string cause, string reason) {
            if (state == AgentSessionState.Inactive)
                throw new AgentException("session_inactive", "There is no agent session to pause.");
            if (state == AgentSessionState.Paused)
                return false;
            state = AgentSessionState.Paused;
            pausedCause = cause;
            pausedReason = reason;
            return true;
        }

        private bool EndLocked(string reason, DateTime nowUtc) {
            if (state == AgentSessionState.Inactive)
                return false;
            lastEnded = new JObject {
                ["id"] = sessionId,
                ["document"] = documentTitle,
                ["reason"] = reason,
                ["ended"] = nowUtc.ToString("o"),
            };
            lastDocument = movedFromDocument ?? boundDocument;
            lastDocumentTitle = movedFrom ?? documentTitle;
            state = AgentSessionState.Inactive;
            sessionId = null;
            boundDocument = null;
            documentTitle = null;
            documents.Clear();
            movedFrom = null;
            movedFromDocument = null;
            startedElsewhere = false;
            pausedCause = null;
            pausedReason = null;
            return true;
        }

        private void RefuseWhileRunExecutes(string message) {
            if (runsExecuting > 0)
                throw new AgentException("session_locked", message);
        }

        private void EndRun() {
            lock (sync)
                runsExecuting--;
        }

        private void OnChanged() {
            Changed?.Invoke();
        }

        private static string StateName(AgentSessionState value) {
            switch (value) {
                case AgentSessionState.Active: return "active";
                case AgentSessionState.Paused: return "paused";
                default: return "inactive";
            }
        }

        private sealed class RunScope : IDisposable {
            private AgentSessionTracker tracker;

            public RunScope(AgentSessionTracker tracker) {
                this.tracker = tracker;
            }

            public void Dispose() {
                tracker?.EndRun();
                tracker = null;
            }
        }
    }

    /// <summary>
    /// The per-request permission check at the gate.
    /// </summary>
    /// <remarks>
    /// The config policy is its only input until sessions get their own permission toggles.
    /// </remarks>
    internal static class AgentPermissions {
        /// <exception cref="AgentException"><c>policy_readonly</c> for a modify run under <c>readonly</c>.</exception>
        public static void CheckRun(AgentRunMode mode, AgentPolicy policy) {
            if (mode == AgentRunMode.Modify && policy == AgentPolicy.ReadOnly)
                throw new AgentException(
                    "policy_readonly",
                    "The pyRevit agent policy is 'readonly': modify runs are disabled. Use query or dry_run.");
        }
    }
}
