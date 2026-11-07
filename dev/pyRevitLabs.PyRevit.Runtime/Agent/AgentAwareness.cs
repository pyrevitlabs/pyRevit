using System;
using System.Collections.Generic;
using System.Linq;

using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// What the user changed between an agent's calls: edits to the session's documents, a view
    /// switch, a selection change, and documents that joined or left the session. Pure logic with
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
        private readonly Dictionary<string, string> joined = new Dictionary<string, string>();
        private readonly Dictionary<string, string> left = new Dictionary<string, string>();
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
                joined.Clear();
                left.Clear();
            }
        }

        /// <summary>
        /// Adds one change of the document to the summary. An element that comes back after it
        /// was deleted counts as modified, since it may differ from before, and an element added
        /// and then deleted leaves no trace.
        /// </summary>
        /// <param name="operation">
        /// <c>undo</c> or <c>redo</c> for a transaction the user undid or redid, and <c>rollback</c>
        /// for a transaction group the user rolled back, whose changes cancel the edits its
        /// transactions made and add no operation names; anything else counts as a new edit.
        /// </param>
        public void RecordEdit(
            IEnumerable<long> addedIds, IEnumerable<long> modifiedIds, IEnumerable<long> deletedIds,
            IEnumerable<string> transactionNames, string operation) {
            lock (sync) {
                if (suppressed > 0)
                    return;
                foreach (var id in addedIds) {
                    if (deleted.Remove(id))
                        modified.Add(id);
                    else
                        added.Add(id);
                }
                foreach (var id in deletedIds) {
                    if (!added.Remove(id))
                        deleted.Add(id);
                    modified.Remove(id);
                }
                foreach (var id in modifiedIds)
                    if (!added.Contains(id))
                        modified.Add(id);
                if (operation != "rollback")
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
        /// Records a document that joined the session. A document that left since the last call
        /// and joined again counts as joined.
        /// </summary>
        public void RecordJoined(string key, string title) {
            lock (sync) {
                if (suppressed > 0)
                    return;
                left.Remove(key);
                joined[key] = title;
            }
        }

        /// <summary>
        /// Records a document that left the session, as when it closed. A document that joined
        /// since the last call and left again leaves no trace.
        /// </summary>
        public void RecordLeft(string key, string title) {
            lock (sync) {
                if (suppressed > 0)
                    return;
                if (!joined.Remove(key))
                    left[key] = title;
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
            JObject documents;
            lock (sync) {
                view = viewChanged;
                selection = selectionChanged;
                edits = DescribeEditsLocked();
                documents = DescribeDocumentsLocked();
            }
            if (!view && !selection && edits == null && documents == null)
                return null;
            var summary = new JObject();
            if (documents != null)
                summary["documents"] = documents;
            if (edits != null)
                summary["edits"] = edits;
            if (view)
                summary["active_view"] = describeView();
            if (selection)
                summary["selection"] = describeSelection();
            return summary;
        }

        private JObject DescribeDocumentsLocked() {
            if (joined.Count == 0 && left.Count == 0)
                return null;
            var documents = new JObject();
            if (joined.Count > 0)
                documents["joined"] = Describe(joined);
            if (left.Count > 0)
                documents["left"] = Describe(left);
            return documents;
        }

        private static JArray Describe(Dictionary<string, string> documents) {
            return new JArray(documents.Select(entry => new JObject { ["key"] = entry.Key, ["title"] = entry.Value }));
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
