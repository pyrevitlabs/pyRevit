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
    /// <item>After a move, every model request except a context read is refused with
    /// <c>session_moved</c> until the agent reads the context, because element ids from the old
    /// document don't apply in the new one.</item>
    /// <item>Nothing that loosens the gate (starting, resuming, making sessions optional) succeeds
    /// while an agent run executes, so run code can't grant itself access. Pausing and ending
    /// always succeed.</item>
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

        /// <returns>The new session's id.</returns>
        /// <exception cref="AgentException">
        /// <c>session_active</c> when a session is already active or paused, or
        /// <c>session_locked</c> while an agent run executes.
        /// </exception>
        public string Start(object document, string title, DateTime nowUtc) {
            if (document == null)
                throw new ArgumentNullException(nameof(document));
            string id;
            lock (sync) {
                RefuseWhileRunExecutes("An agent session can't be started while an agent run executes.");
                if (state != AgentSessionState.Inactive)
                    throw new AgentException("session_active",
                        $"An agent session is already active on '{documentTitle}'. End it before starting another.");
                state = AgentSessionState.Active;
                id = sessionId = Guid.NewGuid().ToString("N").Substring(0, 12);
                boundDocument = document;
                documentTitle = title;
                documents.Clear();
                documents.Add(title);
                movedFrom = null;
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
                if (movedFrom == null)
                    movedFrom = documentTitle;
                from = movedFrom;
                boundDocument = document;
                documentTitle = title;
                documents.Add(title);
            }
            OnChanged();
            return from;
        }

        /// <summary>
        /// Records that the agent read the context, which ends the handshake after a move.
        /// </summary>
        public void ContextRead() {
            lock (sync) {
                if (movedFrom == null)
                    return;
                movedFrom = null;
            }
            OnChanged();
        }

        /// <summary>
        /// Pauses an active session. Pausing a paused one changes nothing, so a pause by the host
        /// keeps its reason even when an agent or run code pauses again.
        /// </summary>
        /// <exception cref="AgentException"><c>session_inactive</c> when there is no session.</exception>
        public void Pause() {
            lock (sync) {
                if (state == AgentSessionState.Inactive)
                    throw new AgentException("session_inactive", "There is no agent session to pause.");
                if (state == AgentSessionState.Paused)
                    return;
                state = AgentSessionState.Paused;
            }
            OnChanged();
        }

        /// <summary>
        /// Pauses the session on the host's own account, for example after a run changed another
        /// document, so the agent's next refusal is <c>paused_by_host</c> and says why. A pause by
        /// the user becomes a pause by the host; an earlier pause by the host keeps its reason.
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
                pausedCause = null;
                pausedReason = null;
            }
            OnChanged();
        }

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
        /// <exception cref="AgentException">
        /// <c>paused_by_user</c>, <c>paused_by_host</c>, <c>session_moved</c> or <c>session_inactive</c>.
        /// </exception>
        public void CheckOnArrival(bool readsContext) {
            lock (sync)
                CheckStateLocked(readsContext);
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
        /// <exception cref="AgentException">
        /// <c>paused_by_user</c>, <c>paused_by_host</c>, <c>session_moved</c>, <c>session_inactive</c> or
        /// <c>wrong_document</c>.
        /// </exception>
        public void CheckOnDequeue(Func<object, bool> isBoundDocumentActive, string activeTitle, bool readsContext) {
            lock (sync) {
                CheckStateLocked(readsContext);
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
                    ["started"] = isOpen ? startedUtc.ToString("o") : null,
                    ["paused_cause"] = state == AgentSessionState.Paused ? pausedCause : null,
                    ["paused_reason"] = state == AgentSessionState.Paused ? pausedReason : null,
                    ["pending_request"] = pendingRequest?.DeepClone(),
                    ["declined_request"] = lastDeclined?.DeepClone(),
                    ["last_ended"] = lastEnded?.DeepClone(),
                };
            }
        }

        private void CheckStateLocked(bool readsContext) {
            if (state == AgentSessionState.Paused && pausedReason != null)
                throw new AgentException("paused_by_host",
                    $"The agent session is paused because {pausedReason} Tell the user; only they can resume the session in Revit.");
            if (state == AgentSessionState.Paused)
                throw new AgentException("paused_by_user",
                    "The user paused the agent session in Revit. Tell the user you are waiting, and try again after they resume it.");
            if (state == AgentSessionState.Active && movedFrom != null && !readsContext)
                throw new AgentException("session_moved",
                    $"The user moved the agent session from '{movedFrom}' to '{documentTitle}'. Element ids from '{movedFrom}' "
                    + $"don't apply in '{documentTitle}'. Call get_context before anything else.");
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

        private bool EndLocked(string reason, DateTime nowUtc) {
            if (state == AgentSessionState.Inactive)
                return false;
            lastEnded = new JObject {
                ["id"] = sessionId,
                ["document"] = documentTitle,
                ["reason"] = reason,
                ["ended"] = nowUtc.ToString("o"),
            };
            state = AgentSessionState.Inactive;
            sessionId = null;
            boundDocument = null;
            documentTitle = null;
            documents.Clear();
            movedFrom = null;
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
