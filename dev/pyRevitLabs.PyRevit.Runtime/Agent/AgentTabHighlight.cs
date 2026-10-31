using System;
using System.Collections.Generic;
using System.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    internal interface IAgentTabHighlightVisuals {
        bool Apply(long documentKey, string tooltip);
        void Restore(long documentKey);
        void Forget(long documentKey);
    }

    /// <summary>
    /// Serial main-thread coordinator. Visibility lasts at least 1500 monotonic milliseconds
    /// from the first successful paint; overlapping and consecutive leases share that paint.
    /// Visual failures never escape into the agent run.
    /// </summary>
    internal sealed class AgentTabHighlight : IDisposable {
        internal sealed class Lease {
            internal long DocumentKey;
            internal string Title;
            internal bool Active = true;
            internal bool Approval;
        }

        private sealed class DocumentState {
            internal readonly List<Lease> Leases = new List<Lease>();
            internal long? PaintedAt;
            internal long Generation;
            internal string Tooltip;
        }

        private readonly Func<long> clock;
        private readonly Action<int, Action> schedule;
        private readonly IAgentTabHighlightVisuals visuals;
        private readonly Action<Exception> logDisabled;
        private readonly Dictionary<long, DocumentState> documents = new Dictionary<long, DocumentState>();
        private long generation;
        private int failures;
        private bool disabled;
        private bool disposed;

        internal AgentTabHighlight(Func<long> clock, Action<int, Action> schedule,
            IAgentTabHighlightVisuals visuals, Action<Exception> logDisabled) {
            this.clock = clock;
            this.schedule = schedule;
            this.visuals = visuals;
            this.logDisabled = logDisabled;
        }

        internal Lease Begin(long documentKey, string title) {
            if (disabled || disposed)
                return null;
            var lease = new Lease { DocumentKey = documentKey, Title = title };
            if (!documents.TryGetValue(documentKey, out var state)) {
                state = new DocumentState();
                documents.Add(documentKey, state);
            }
            state.Generation = ++generation;
            state.Leases.Add(lease);
            Paint(documentKey, state);
            return lease;
        }

        internal void AwaitApproval(Lease lease) {
            if (lease == null || !lease.Active || disabled || disposed)
                return;
            lease.Approval = true;
            if (documents.TryGetValue(lease.DocumentKey, out var state))
                Paint(lease.DocumentKey, state);
        }

        internal void End(Lease lease) {
            if (lease == null || !lease.Active)
                return;
            lease.Active = false;
            if (disabled || disposed || !documents.TryGetValue(lease.DocumentKey, out var state))
                return;
            state.Leases.Remove(lease);
            if (state.Leases.Count > 0) {
                Paint(lease.DocumentKey, state);
                return;
            }
            Finish(lease.DocumentKey, state.Generation = ++generation);
        }

        private void Finish(long documentKey, long callbackGeneration) {
            if (disposed || disabled || !documents.TryGetValue(documentKey, out var state)
                || state.Generation != callbackGeneration || state.Leases.Count != 0)
                return;
            var remaining = state.PaintedAt.HasValue ? 1500 - (clock() - state.PaintedAt.Value) : 0;
            if (remaining <= 0) {
                Remove(documentKey);
                return;
            }
            Attempt(() => schedule((int)remaining, () => Finish(documentKey, callbackGeneration)));
        }

        internal void Refresh() {
            if (disabled || disposed)
                return;
            foreach (var entry in documents.ToArray())
                Paint(entry.Key, entry.Value);
        }

        private void Paint(long key, DocumentState state) {
            if (state.Leases.Count > 0) {
                var lease = state.Leases[state.Leases.Count - 1];
                state.Tooltip = "Agent: " + lease.Title + (lease.Approval ? " (awaiting approval)" : string.Empty);
            }
            Attempt(() => {
                if (visuals.Apply(key, state.Tooltip)) {
                    if (!state.PaintedAt.HasValue)
                        state.PaintedAt = clock();
                    failures = 0;
                }
            });
        }

        private void Remove(long key) {
            Attempt(() => visuals.Restore(key));
            documents.Remove(key);
            Attempt(() => visuals.Forget(key));
        }

        internal void VisualFailed(Exception exception) {
            Attempt(() => { throw exception; });
        }

        private void Attempt(Action action) {
            try {
                action();
            }
            catch (Exception exception) {
                failures++;
                foreach (var key in documents.Keys.ToArray()) {
                    try { visuals.Restore(key); }
                    catch { }
                }
                if (failures >= 3) {
                    disabled = true;
                    foreach (var key in documents.Keys.ToArray()) {
                        try { visuals.Forget(key); }
                        catch { }
                    }
                    documents.Clear();
                    try { logDisabled(exception); }
                    catch { }
                }
            }
        }

        /// <summary>Removes only owned visual values and invalidates pending callbacks.</summary>
        public void Dispose() {
            if (disposed)
                return;
            disposed = true;
            foreach (var key in documents.Keys.ToArray()) {
                try { visuals.Restore(key); }
                catch { }
                try { visuals.Forget(key); }
                catch { }
            }
            documents.Clear();
        }
    }
}
