using System;
using System.Collections.Generic;
using System.Linq;

using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// One model request as the agent panel shows it. Immutable; <see cref="AgentActivity"/>
    /// replaces it as the request moves on.
    /// </summary>
    internal sealed class AgentRequestRecord {
        public AgentRequestRecord(
            long id, string kind, string title, string reason, string sessionId, string sessionDocument, DateTime arrivedUtc) {
            Id = id;
            Kind = kind;
            Title = title;
            Reason = reason;
            SessionId = sessionId;
            SessionDocument = sessionDocument;
            ArrivedUtc = arrivedUtc;
        }

        public long Id { get; }

        /// <summary>
        /// What was asked: <c>query</c>, <c>dry_run</c>, <c>modify</c>, <c>context</c>,
        /// <c>inspect</c>, <c>show</c>, <c>capture</c> or <c>lookup</c>.
        /// </summary>
        public string Kind { get; }

        public string Title { get; }
        public string Reason { get; }

        /// <summary>The session the request arrived in, or null when none was active.</summary>
        public string SessionId { get; }

        /// <summary>Title of that session's document, or null.</summary>
        public string SessionDocument { get; }

        public DateTime ArrivedUtc { get; }
        public bool Started => StartedUtc.HasValue;
        public DateTime? StartedUtc { get; private set; }
        public DateTime? FinishedUtc { get; private set; }

        /// <summary>
        /// How it ended: <c>ok</c>, <c>committed</c>, <c>rejected</c>, or an error type.
        /// </summary>
        public string Outcome { get; private set; }

        /// <summary>
        /// For a run, the summary <see cref="AgentLogDetails.FromRun"/> made of its response;
        /// otherwise null.
        /// </summary>
        public JObject Details { get; private set; }

        /// <summary>
        /// Lookups read context or the API without acting on the model; the log hides them
        /// unless the user asks for them.
        /// </summary>
        public bool IsLookup => Kind == "context" || Kind == "lookup";

        public AgentRequestRecord AsStarted(DateTime startedUtc) {
            var copy = (AgentRequestRecord)MemberwiseClone();
            copy.StartedUtc = startedUtc;
            return copy;
        }

        public AgentRequestRecord AsFinished(string outcome, DateTime finishedUtc, JObject details) {
            var copy = (AgentRequestRecord)MemberwiseClone();
            copy.StartedUtc = StartedUtc ?? finishedUtc;
            copy.Outcome = outcome;
            copy.FinishedUtc = finishedUtc;
            copy.Details = details;
            return copy;
        }
    }

    /// <summary>
    /// What agents have been doing in this Revit session, for the agent panel: the request
    /// waiting for or running in Revit, the last request that finished, the history of
    /// finished requests, the MCP client that last called, and whether the approval prompt is
    /// open. Pure logic with no Revit dependency.
    /// </summary>
    /// <remarks>
    /// Only requests that reach Revit are recorded. The history lives in memory, holds the
    /// latest <see cref="MaxHistory"/> requests and is lost when Revit closes; a run's full
    /// record stays on disk in its run folder. Every member is safe to call from any thread.
    /// <see cref="Changed"/> is raised on the thread that made the change, after the lock is
    /// released.
    /// Invariant: requests in flight are tracked by id, because an in-process request can
    /// arrive while a pipe request waits or runs, for example from a script inside an agent
    /// run. Finishing one never changes another's record or clears its approval prompt.
    /// </remarks>
    internal sealed class AgentActivity {
        public const int MaxClientLength = 80;
        public const int MaxHistory = 200;

        private readonly object sync = new object();
        private readonly List<AgentRequestRecord> history = new List<AgentRequestRecord>();
        private readonly List<AgentRequestRecord> inFlight = new List<AgentRequestRecord>();
        private long nextId;
        private AgentRequestRecord last;
        private string client;
        private bool awaitingApproval;

        public event Action Changed;

        /// <summary>
        /// The request Revit is working on, or else the first one waiting for it; null when none
        /// is in flight. Of requests nested inside one another, the innermost is the one running.
        /// </summary>
        public AgentRequestRecord Current {
            get {
                lock (sync)
                    return inFlight.LastOrDefault(record => record.Started) ?? inFlight.FirstOrDefault();
            }
        }

        /// <summary>
        /// The last request that finished, lookups through the pipe excluded.
        /// </summary>
        public AgentRequestRecord Last {
            get {
                lock (sync)
                    return last;
            }
        }

        /// <summary>
        /// Finished requests, oldest first.
        /// </summary>
        public IReadOnlyList<AgentRequestRecord> History {
            get {
                lock (sync)
                    return history.ToArray();
            }
        }

        public string Client {
            get {
                lock (sync)
                    return client;
            }
        }

        public bool AwaitingApproval {
            get {
                lock (sync)
                    return awaitingApproval;
            }
        }

        /// <summary>
        /// Remembers the name an MCP client gave at <c>initialize</c>. Blank names are ignored and
        /// long ones are cut, because the name comes from the client.
        /// </summary>
        public void NoteClient(string name) {
            var trimmed = name?.Trim();
            if (string.IsNullOrEmpty(trimmed))
                return;
            if (trimmed.Length > MaxClientLength)
                trimmed = trimmed.Substring(0, MaxClientLength);
            lock (sync) {
                if (trimmed == client)
                    return;
                client = trimmed;
            }
            OnChanged();
        }

        public AgentRequestRecord Arrive(
            string kind, string title, string reason, (string Id, string Document) session, DateTime nowUtc) {
            AgentRequestRecord record;
            lock (sync) {
                record = new AgentRequestRecord(++nextId, kind, title, reason, session.Id, session.Document, nowUtc);
                inFlight.Add(record);
            }
            OnChanged();
            return record;
        }

        public void Start(AgentRequestRecord record, DateTime nowUtc) {
            lock (sync) {
                var index = inFlight.FindIndex(candidate => candidate.Id == record.Id);
                if (index < 0)
                    return;
                inFlight[index] = inFlight[index].AsStarted(nowUtc);
            }
            OnChanged();
        }

        /// <remarks>
        /// Only a request that started can have opened the approval prompt, so only finishing
        /// one closes it here; a refusal on arrival leaves it as it is.
        /// </remarks>
        public void Finish(AgentRequestRecord record, string outcome, DateTime nowUtc, JObject details = null) {
            lock (sync) {
                var index = inFlight.FindIndex(candidate => candidate.Id == record.Id);
                var tracked = index < 0 ? record : inFlight[index];
                if (index >= 0)
                    inFlight.RemoveAt(index);
                last = tracked.AsFinished(outcome, nowUtc, details);
                AddToHistory(last);
                if (tracked.Started)
                    awaitingApproval = false;
            }
            OnChanged();
        }

        /// <summary>
        /// Records a lookup the pipe thread answered at once. It goes into the history only, so
        /// the panel's last request stays the last one that touched the model.
        /// </summary>
        public void RecordLookup(string kind, string title, (string Id, string Document) session, string outcome, DateTime nowUtc) {
            lock (sync) {
                var record = new AgentRequestRecord(++nextId, kind, title, null, session.Id, session.Document, nowUtc);
                AddToHistory(record.AsFinished(outcome, nowUtc, null));
            }
            OnChanged();
        }

        public void SetAwaitingApproval(bool value) {
            lock (sync) {
                if (awaitingApproval == value)
                    return;
                awaitingApproval = value;
            }
            OnChanged();
        }

        private void AddToHistory(AgentRequestRecord record) {
            history.Add(record);
            if (history.Count > MaxHistory)
                history.RemoveRange(0, history.Count - MaxHistory);
        }

        private void OnChanged() {
            Changed?.Invoke();
        }
    }
}
