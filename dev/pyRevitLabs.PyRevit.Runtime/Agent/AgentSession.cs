using System;
using System.Collections.Generic;
using System.Linq;

using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    internal enum AgentSessionState {
        Inactive,
        Active,
        Paused,
    }

    /// <summary>How agent sessions start, from <c>[agent] session_start</c>.</summary>
    internal enum AgentSessionStart {
        /// <summary>Only the user starts a session, in the agent panel.</summary>
        User,

        /// <summary>The first model request starts a session on every open document.</summary>
        Auto,
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
    /// A document in an agent session: an opaque reference, the key agents name it by, and its
    /// title. Immutable.
    /// </summary>
    internal sealed class AgentSessionDocument {
        public AgentSessionDocument(object document, string key, string title) {
            Document = document ?? throw new ArgumentNullException(nameof(document));
            Key = key;
            Title = title;
        }

        public object Document { get; }
        public string Key { get; }
        public string Title { get; }

        public AgentSessionDocument WithTitle(string title) {
            return new AgentSessionDocument(Document, Key, title);
        }
    }

    /// <summary>
    /// The user's consent for agents to work in a set of documents: the session state machine and
    /// the gate that every model request passes. Pure logic with no Revit dependency;
    /// <see cref="AgentSessions"/> connects it to Revit.
    /// </summary>
    /// <remarks>
    /// A session goes inactive → active ⇄ paused → inactive. Ending one returns to inactive and
    /// remembers why, so the next refusal can tell the agent. With
    /// <see cref="AgentSessionStart.User"/> the user starts a session on the documents they choose
    /// and can add more; with <see cref="AgentSessionStart.Auto"/> the first model request starts
    /// one that covers every open document, including ones opened later.
    /// Invariants:
    /// <list type="bullet">
    /// <item>No model request passes without an active session.</item>
    /// <item>A paused session refuses model requests, and an active one refuses requests that name
    /// a document outside it with <c>document_not_in_session</c>. A request names its document by
    /// key, and element ids are always read in that document, so ids from one document never
    /// reach another.</item>
    /// <item>While sessions start automatically, only the host can end one, so Pause is the only
    /// way to stop agents: ending a session would only let the next request start another.</item>
    /// <item>Nothing that loosens the gate succeeds while an agent run executes, so run code can't
    /// grant itself access: starting or resuming a session, adding a document to it, or making
    /// sessions start automatically. Pausing always succeeds.</item>
    /// </list>
    /// Documents are opaque references; callers decide what counts as the same document.
    /// Every member is safe to call from any thread. <see cref="Changed"/> is raised on the thread
    /// that made the change, after the tracker's lock is released.
    /// </remarks>
    internal sealed class AgentSessionTracker {
        public const int MaxReasonLength = 300;

        private readonly object sync = new object();
        private readonly List<AgentSessionDocument> documents = new List<AgentSessionDocument>();
        private AgentSessionState state = AgentSessionState.Inactive;
        private AgentSessionStart startMode = AgentSessionStart.User;
        private bool startedAutomatically;
        private int runsExecuting;
        private string sessionId;
        private DateTime startedUtc;
        private JObject pendingRequest;
        private JObject lastDeclined;
        private string pausedCause;
        private string pausedReason;
        private JObject lastEnded;

        public event Action Changed;

        public AgentSessionStart StartMode {
            get {
                lock (sync)
                    return startMode;
            }
        }

        public AgentSessionState State {
            get {
                lock (sync)
                    return state;
            }
        }

        /// <summary>Whether the open session started automatically; false when there is none.</summary>
        public bool StartedAutomatically {
            get {
                lock (sync)
                    return state != AgentSessionState.Inactive && startedAutomatically;
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
        /// The active or paused session's id and the titles of its documents, read together; both
        /// null when there is no session.
        /// </summary>
        public (string Id, string Document) CurrentSession {
            get {
                lock (sync)
                    return state == AgentSessionState.Inactive ? (null, null) : (sessionId, TitlesLocked());
            }
        }

        /// <summary>The open session's documents; empty when there is none.</summary>
        public IReadOnlyList<AgentSessionDocument> Documents {
            get {
                lock (sync)
                    return state == AgentSessionState.Inactive ? new AgentSessionDocument[0] : documents.ToArray();
            }
        }

        /// <summary>
        /// Whether a document is in the open session. Every document is in a session that started
        /// automatically.
        /// </summary>
        /// <param name="isDocument">
        /// Whether a session document is the one asked about; called under the tracker's lock.
        /// </param>
        public bool Contains(Func<object, bool> isDocument) {
            lock (sync)
                return state != AgentSessionState.Inactive
                    && (startedAutomatically || documents.Any(entry => isDocument(entry.Document)));
        }

        /// <exception cref="AgentException">
        /// <c>session_locked</c> when making sessions start automatically while an agent run
        /// executes.
        /// </exception>
        public void SetStartMode(AgentSessionStart mode) {
            lock (sync) {
                if (startMode == mode)
                    return;
                if (mode == AgentSessionStart.Auto)
                    RefuseWhileRunExecutes("Agent sessions can't be made to start automatically while an agent run executes.");
                startMode = mode;
            }
            OnChanged();
        }

        /// <summary>
        /// Starts a session the user chose, on <paramref name="chosen"/>.
        /// </summary>
        /// <returns>The new session's id.</returns>
        /// <exception cref="ArgumentException">No document is chosen.</exception>
        /// <exception cref="AgentException">
        /// <c>session_active</c> when a session is already active or paused, or
        /// <c>session_locked</c> while an agent run executes.
        /// </exception>
        public string Start(IEnumerable<AgentSessionDocument> chosen, DateTime nowUtc) {
            var list = chosen?.ToList() ?? throw new ArgumentNullException(nameof(chosen));
            if (list.Count == 0)
                throw new ArgumentException("A session needs at least one document.", nameof(chosen));
            string id;
            lock (sync) {
                RefuseWhileRunExecutes("An agent session can't be started while an agent run executes.");
                if (state != AgentSessionState.Inactive)
                    throw new AgentException("session_active",
                        $"An agent session is already active on {NamesLocked()}. End it before starting another.");
                id = OpenLocked(list, automatic: false, nowUtc);
            }
            OnChanged();
            return id;
        }

        /// <summary>
        /// Starts a session on every open document, when sessions start automatically and none is
        /// open. A paused session stays paused.
        /// </summary>
        /// <param name="open">The open documents; documents opened later join through
        /// <see cref="AddDocument"/>.</param>
        /// <returns>Whether a session started.</returns>
        public bool StartAutomatically(IEnumerable<AgentSessionDocument> open, DateTime nowUtc) {
            lock (sync) {
                if (startMode != AgentSessionStart.Auto || state != AgentSessionState.Inactive)
                    return false;
                OpenLocked(open?.ToList() ?? new List<AgentSessionDocument>(), automatic: true, nowUtc);
            }
            OnChanged();
            return true;
        }

        /// <summary>
        /// Adds a document to the open session: one the user chose, or one the host adds on the
        /// session's behalf, such as a document opened while a session that started automatically
        /// is open.
        /// </summary>
        /// <returns>False when a document with the same key is already in the session.</returns>
        /// <exception cref="AgentException">
        /// <c>session_inactive</c> when there is no session, or <c>session_locked</c> when the user's
        /// add happens while an agent run executes.
        /// </exception>
        public bool AddDocument(AgentSessionDocument document, bool byUser) {
            if (document == null)
                throw new ArgumentNullException(nameof(document));
            lock (sync) {
                if (byUser)
                    RefuseWhileRunExecutes("A document can't be added to the agent session while an agent run executes.");
                if (state == AgentSessionState.Inactive)
                    throw new AgentException("session_inactive", "There is no agent session to add a document to.");
                if (documents.Any(entry => entry.Key == document.Key))
                    return false;
                documents.Add(document);
            }
            OnChanged();
            return true;
        }

        /// <summary>
        /// Removes a document from the open session. Removing its last document ends the session
        /// with <paramref name="reasonIfLast"/>.
        /// </summary>
        /// <param name="isDocument">Whether a session document is the one to remove; called under the tracker's lock.</param>
        /// <returns>The removed document, or null when it wasn't in the session.</returns>
        public AgentSessionDocument RemoveDocument(Func<object, bool> isDocument, string reasonIfLast, DateTime nowUtc) {
            AgentSessionDocument removed;
            lock (sync) {
                if (state == AgentSessionState.Inactive)
                    return null;
                removed = documents.FirstOrDefault(entry => isDocument(entry.Document));
                if (removed == null)
                    return null;
                if (documents.Count == 1)
                    EndLocked(reasonIfLast, nowUtc);
                else
                    documents.Remove(removed);
            }
            OnChanged();
            return removed;
        }

        /// <summary>
        /// Follows a session document to the title it was saved under.
        /// </summary>
        /// <returns>False when the document isn't in the session or the title didn't change.</returns>
        public bool Retitle(Func<object, bool> isDocument, string title) {
            lock (sync) {
                if (state == AgentSessionState.Inactive || string.IsNullOrEmpty(title))
                    return false;
                var index = documents.FindIndex(entry => isDocument(entry.Document));
                if (index < 0 || documents[index].Title == title)
                    return false;
                documents[index] = documents[index].WithTitle(title);
            }
            OnChanged();
            return true;
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
        /// <c>session_locked</c> while sessions start automatically.
        /// </exception>
        public bool EndInRevit(DateTime nowUtc) {
            bool ended;
            lock (sync) {
                RefuseWhileSessionsStartAutomatically();
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
        /// <exception cref="AgentException"><c>session_locked</c> while sessions start automatically.</exception>
        public bool EndForAgent(DateTime nowUtc) {
            bool ended;
            lock (sync) {
                RefuseWhileSessionsStartAutomatically();
                ended = EndLocked(AgentSessionEndReasons.EndedByClient, nowUtc);
            }
            if (ended)
                OnChanged();
            return ended;
        }

        /// <summary>
        /// Records an agent's request for a session, replacing an earlier one.
        /// </summary>
        /// <returns>
        /// False when there is nothing to request: a session is active, or none is and the next
        /// model request starts one.
        /// </returns>
        /// <exception cref="AgentException"><c>invalid_params</c> when the reason is too long.</exception>
        public bool Request(string reason, DateTime nowUtc) {
            var trimmed = reason?.Trim();
            if (trimmed != null && trimmed.Length > MaxReasonLength)
                throw new AgentException("invalid_params", $"'reason' must be at most {MaxReasonLength} characters.");
            lock (sync) {
                if (state == AgentSessionState.Active
                    || (state == AgentSessionState.Inactive && startMode == AgentSessionStart.Auto))
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
        /// The gate when a request arrives, before it waits for Revit. While sessions start
        /// automatically, a request with no session open passes, and Revit starts one when it
        /// picks the request up.
        /// </summary>
        /// <exception cref="AgentException">
        /// <c>paused_by_user</c>, <c>paused_by_host</c>, <c>paused_by_agent</c> or <c>session_inactive</c>.
        /// </exception>
        public void CheckOnArrival() {
            lock (sync)
                CheckStateLocked();
        }

        /// <summary>
        /// The gate when Revit picks the request up, which also catches a pause while the request
        /// was queued, and checks that the document the request names is in the session.
        /// </summary>
        /// <remarks>
        /// Callers start a session that starts automatically first, with
        /// <see cref="StartAutomatically"/>.
        /// </remarks>
        /// <param name="isTarget">
        /// Whether a document is the one the request names; called under the tracker's lock, on the
        /// thread that may compare documents.
        /// </param>
        /// <param name="targetTitle">
        /// Title of the document the request names, or null when it names none, as a context read
        /// doesn't.
        /// </param>
        /// <exception cref="AgentException">
        /// <c>paused_by_user</c>, <c>paused_by_host</c>, <c>paused_by_agent</c>, <c>session_inactive</c> or
        /// <c>document_not_in_session</c>.
        /// </exception>
        public void CheckOnDequeue(Func<object, bool> isTarget, string targetTitle) {
            lock (sync) {
                CheckStateLocked();
                if (state != AgentSessionState.Active || targetTitle == null || startedAutomatically
                    || documents.Any(entry => isTarget(entry.Document)))
                    return;
                throw new AgentException("document_not_in_session",
                    $"The agent session covers {NamesLocked()}, and '{targetTitle}' isn't part of it. Work in the session's "
                    + $"documents (their keys are in get_context), or ask the user to add '{targetTitle}' to the session in "
                    + "the agent panel.");
            }
        }

        public JObject Describe() {
            lock (sync) {
                var isOpen = state != AgentSessionState.Inactive;
                return new JObject {
                    ["start"] = startMode == AgentSessionStart.Auto ? "auto" : "user",
                    ["state"] = StateName(state),
                    ["id"] = isOpen ? sessionId : null,
                    ["automatic"] = isOpen && startedAutomatically,
                    ["documents"] = isOpen
                        ? new JArray(documents.Select(entry => new JObject { ["key"] = entry.Key, ["title"] = entry.Title }))
                        : null,
                    ["started"] = isOpen ? startedUtc.ToString("o") : null,
                    ["paused_cause"] = state == AgentSessionState.Paused ? pausedCause : null,
                    ["paused_reason"] = state == AgentSessionState.Paused ? pausedReason : null,
                    ["pending_request"] = pendingRequest?.DeepClone(),
                    ["declined_request"] = lastDeclined?.DeepClone(),
                    ["last_ended"] = lastEnded?.DeepClone(),
                };
            }
        }

        private string OpenLocked(List<AgentSessionDocument> opened, bool automatic, DateTime nowUtc) {
            state = AgentSessionState.Active;
            sessionId = Guid.NewGuid().ToString("N").Substring(0, 12);
            startedAutomatically = automatic;
            documents.Clear();
            documents.AddRange(opened);
            startedUtc = nowUtc;
            pendingRequest = null;
            lastDeclined = null;
            return sessionId;
        }

        private void CheckStateLocked() {
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
            if (state != AgentSessionState.Inactive || startMode == AgentSessionStart.Auto)
                return;
            if (lastDeclined != null)
                throw new AgentException("session_inactive",
                    "The user declined your request for an agent session in Revit. Ask them in the conversation "
                    + "before you call request_session again.");
            var ended = lastEnded != null && lastEnded.Value<string>("reason") == AgentSessionEndReasons.DocumentClosed
                ? $"The agent session ended because its last document '{lastEnded.Value<string>("document")}' was closed. "
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
                ["document"] = TitlesLocked(),
                ["reason"] = reason,
                ["ended"] = nowUtc.ToString("o"),
            };
            state = AgentSessionState.Inactive;
            sessionId = null;
            startedAutomatically = false;
            documents.Clear();
            pausedCause = null;
            pausedReason = null;
            return true;
        }

        private string TitlesLocked() {
            return string.Join(", ", documents.Select(entry => entry.Title));
        }

        private string NamesLocked() {
            return documents.Count == 0 ? "no document" : string.Join(", ", documents.Select(entry => "'" + entry.Title + "'"));
        }

        private void RefuseWhileRunExecutes(string message) {
            if (runsExecuting > 0)
                throw new AgentException("session_locked", message);
        }

        private void RefuseWhileSessionsStartAutomatically() {
            if (startMode == AgentSessionStart.Auto && state != AgentSessionState.Inactive)
                throw new AgentException("session_locked",
                    "Agent sessions start automatically in this Revit, so ending this one would only let the next request "
                    + "start another. Pause it to stop agents.");
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
