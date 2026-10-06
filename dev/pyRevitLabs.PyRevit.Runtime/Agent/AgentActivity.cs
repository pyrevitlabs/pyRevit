using System;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// One model request as the agent panel shows it. Immutable; <see cref="AgentActivity"/>
    /// replaces it as the request moves on.
    /// </summary>
    internal sealed class AgentRequestRecord {
        public AgentRequestRecord(long id, string kind, string title, DateTime arrivedUtc) {
            Id = id;
            Kind = kind;
            Title = title;
            ArrivedUtc = arrivedUtc;
        }

        public long Id { get; }

        /// <summary>
        /// What was asked: <c>query</c>, <c>dry_run</c>, <c>modify</c>, <c>context</c>,
        /// <c>inspect</c>, <c>show</c> or <c>capture</c>.
        /// </summary>
        public string Kind { get; }

        public string Title { get; }
        public DateTime ArrivedUtc { get; }
        public bool Started { get; private set; }
        public DateTime? FinishedUtc { get; private set; }

        /// <summary>
        /// How it ended: <c>ok</c>, a run decision such as <c>committed</c>, or an error type.
        /// </summary>
        public string Outcome { get; private set; }

        public AgentRequestRecord AsStarted() {
            var copy = (AgentRequestRecord)MemberwiseClone();
            copy.Started = true;
            return copy;
        }

        public AgentRequestRecord AsFinished(string outcome, DateTime finishedUtc) {
            var copy = (AgentRequestRecord)MemberwiseClone();
            copy.Started = true;
            copy.Outcome = outcome;
            copy.FinishedUtc = finishedUtc;
            return copy;
        }
    }

    /// <summary>
    /// What agents are doing right now, for the agent panel: the request waiting for or running in
    /// Revit, the last request that finished, the MCP client that last called, and whether the
    /// approval prompt is open. Pure logic with no Revit dependency.
    /// </summary>
    /// <remarks>
    /// Only model requests are recorded, the ones that pass the session gate; lookups and pings
    /// would hide the request that matters. Every member is safe to call from any thread.
    /// <see cref="Changed"/> is raised on the thread that made the change, after the lock is
    /// released.
    /// </remarks>
    internal sealed class AgentActivity {
        public const int MaxClientLength = 80;

        private readonly object sync = new object();
        private long nextId;
        private AgentRequestRecord current;
        private AgentRequestRecord last;
        private string client;
        private bool awaitingApproval;

        public event Action Changed;

        /// <summary>
        /// The request that has arrived and not finished, or null.
        /// </summary>
        public AgentRequestRecord Current {
            get {
                lock (sync)
                    return current;
            }
        }

        public AgentRequestRecord Last {
            get {
                lock (sync)
                    return last;
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

        public AgentRequestRecord Arrive(string kind, string title, DateTime nowUtc) {
            AgentRequestRecord record;
            lock (sync)
                current = record = new AgentRequestRecord(++nextId, kind, title, nowUtc);
            OnChanged();
            return record;
        }

        public void Start(AgentRequestRecord record) {
            lock (sync) {
                if (current == null || current.Id != record.Id)
                    return;
                current = current.AsStarted();
            }
            OnChanged();
        }

        public void Finish(AgentRequestRecord record, string outcome, DateTime nowUtc) {
            lock (sync) {
                last = record.AsFinished(outcome, nowUtc);
                if (current != null && current.Id == record.Id)
                    current = null;
                awaitingApproval = false;
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

        private void OnChanged() {
            Changed?.Invoke();
        }
    }
}
