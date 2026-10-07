using System;
using System.Collections.Generic;
using System.Linq;

using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// What the user changed between an agent's calls: edits to the session's document, a view
    /// switch, a selection change and a move of the session to another document. Pure logic with
    /// no Revit dependency;
    /// <see cref="AgentAwarenessWatch"/> feeds it from Revit's events.
    /// </summary>
    /// <remarks>
    /// The agent gets the summary with its next model request as <c>since_last_call</c>, so it
    /// doesn't act on a stale picture of the model.
    /// Invariant: changes the host makes while it handles a request are not the user's. Callers
    /// wrap that work in <see cref="Suppress"/>, and nothing is recorded meanwhile.
    /// View and selection changes are only flagged here; the summary describes the view and
    /// selection as they are when it is built. Every member is safe to call from any thread.
    /// </remarks>
    internal sealed class AgentAwareness {
        public const int MaxSampleIds = 20;
        public const int MaxOperations = 20;

        private readonly object sync = new object();
        private readonly HashSet<long> added = new HashSet<long>();
        private readonly HashSet<long> modified = new HashSet<long>();
        private readonly HashSet<long> deleted = new HashSet<long>();
        private readonly List<string> operations = new List<string>();
        private int undone;
        private int redone;
        private bool viewChanged;
        private bool selectionChanged;
        private string movedFrom;
        private string movedTo;
        private int suppressed;

        public bool IsSuppressed {
            get {
                lock (sync)
                    return suppressed > 0;
            }
        }

        /// <summary>
        /// Stops recording until the returned scope is disposed.
        /// </summary>
        public IDisposable Suppress() {
            lock (sync)
                suppressed++;
            return new SuppressScope(this);
        }

        public void Clear() {
            lock (sync) {
                added.Clear();
                modified.Clear();
                deleted.Clear();
                operations.Clear();
                undone = 0;
                redone = 0;
                viewChanged = false;
                selectionChanged = false;
                movedFrom = null;
                movedTo = null;
            }
        }

        /// <param name="operation">
        /// <c>undo</c> or <c>redo</c> for a transaction the user undid or redid; anything else counts
        /// as a new edit.
        /// </param>
        public void RecordEdit(
            IEnumerable<long> addedIds, IEnumerable<long> modifiedIds, IEnumerable<long> deletedIds,
            IEnumerable<string> transactionNames, string operation) {
            lock (sync) {
                if (suppressed > 0)
                    return;
                foreach (var id in addedIds)
                    added.Add(id);
                foreach (var id in deletedIds) {
                    if (!added.Remove(id))
                        deleted.Add(id);
                    modified.Remove(id);
                }
                foreach (var id in modifiedIds)
                    if (!added.Contains(id))
                        modified.Add(id);
                foreach (var name in transactionNames)
                    if (!string.IsNullOrEmpty(name) && !operations.Contains(name) && operations.Count < MaxOperations)
                        operations.Add(name);
                if (operation == "undo")
                    undone++;
                else if (operation == "redo")
                    redone++;
            }
        }

        public void RecordViewChange() {
            lock (sync)
                if (suppressed == 0)
                    viewChanged = true;
        }

        public void RecordSelectionChange() {
            lock (sync)
                if (suppressed == 0)
                    selectionChanged = true;
        }

        /// <summary>
        /// Records that the user moved the session. Callers clear the earlier changes first, since
        /// they belong to the old document.
        /// </summary>
        /// <param name="from">The document the agent last read the context in.</param>
        public void RecordMove(string from, string to) {
            lock (sync) {
                movedFrom = from;
                movedTo = to;
            }
        }

        /// <summary>
        /// Describes what changed since the last call, or returns null when nothing did. Doesn't
        /// forget it: callers <see cref="Clear"/> once the request that carries it succeeded, so a
        /// refused request doesn't lose it.
        /// </summary>
        /// <param name="describeView">Describes the active view; called only when it changed.</param>
        /// <param name="describeSelection">Describes the selection; called only when it changed.</param>
        public JObject Peek(Func<JToken> describeView, Func<JToken> describeSelection) {
            bool view;
            bool selection;
            JObject edits;
            JObject moved;
            lock (sync) {
                view = viewChanged;
                selection = selectionChanged;
                edits = DescribeEditsLocked();
                moved = movedTo == null ? null : new JObject { ["from"] = movedFrom, ["to"] = movedTo };
            }
            if (!view && !selection && edits == null && moved == null)
                return null;
            var summary = new JObject();
            if (moved != null)
                summary["session_moved"] = moved;
            if (edits != null)
                summary["edits"] = edits;
            if (view)
                summary["active_view"] = describeView();
            if (selection)
                summary["selection"] = describeSelection();
            return summary;
        }

        private JObject DescribeEditsLocked() {
            if (added.Count == 0 && modified.Count == 0 && deleted.Count == 0 && undone == 0 && redone == 0)
                return null;
            var edits = new JObject {
                ["added"] = added.Count,
                ["modified"] = modified.Count,
                ["deleted"] = deleted.Count,
                ["added_ids"] = new JArray(added.Take(MaxSampleIds)),
                ["modified_ids"] = new JArray(modified.Take(MaxSampleIds)),
                ["deleted_ids"] = new JArray(deleted.Take(MaxSampleIds)),
                ["operations"] = new JArray(operations),
            };
            if (undone > 0)
                edits["undone"] = undone;
            if (redone > 0)
                edits["redone"] = redone;
            return edits;
        }

        private void EndSuppress() {
            lock (sync)
                suppressed--;
        }

        private sealed class SuppressScope : IDisposable {
            private AgentAwareness awareness;

            public SuppressScope(AgentAwareness awareness) {
                this.awareness = awareness;
            }

            public void Dispose() {
                awareness?.EndSuppress();
                awareness = null;
            }
        }
    }
}
