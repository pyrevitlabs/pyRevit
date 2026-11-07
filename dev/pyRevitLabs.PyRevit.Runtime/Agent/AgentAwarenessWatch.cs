using System.Collections.Generic;
using System.Linq;

using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Events;
using Autodesk.Revit.UI;

using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Watches Revit for what the user changes in the session's documents between an agent's
    /// calls, and builds the <c>since_last_call</c> summary from <see cref="Awareness"/>.
    /// </summary>
    /// <remarks>
    /// Edits come from <c>DocumentChanged</c>, under the changed document's key. The active view
    /// and the selection are compared, when the next request arrives, with the ones the last
    /// request left behind in a session document, on every Revit version; a view or selection of
    /// another session document counts as changed, even when its ids are the same. Events would report a round trip to another document as
    /// a view change, <c>SelectionChanged</c> exists only from Revit 2023, and when Revit raises
    /// either for the host's own changes is not something to rely on. They are recorded again
    /// when Revit next goes idle after a request, because a view change the request asked for
    /// with <c>RequestViewChange</c> happens only after it returns.
    /// Invariant: only the session's documents are watched, and nothing is recorded while the
    /// host handles a request; see <see cref="AgentAwareness"/>.
    /// </remarks>
    internal static class AgentAwarenessWatch {
        internal static readonly AgentAwareness Awareness = new AgentAwareness();

        private const int MaxSelectionIds = 200;
        private static readonly object sync = new object();
        private static bool attached;
        private static bool idleRecordQueued;
        private static string documentBaseline;
        private static long? viewBaseline;
        private static HashSet<long> selectionBaseline = new HashSet<long>();

        /// <summary>
        /// Subscribes to Revit's events once per process. Must run in a Revit API context.
        /// </summary>
        public static void Attach(UIApplication uiApp) {
            lock (sync) {
                if (attached)
                    return;
                attached = true;
            }
            uiApp.Application.DocumentChanged += OnDocumentChanged;
        }

        /// <summary>
        /// Forgets earlier changes when a session starts, so its first call reports nothing.
        /// </summary>
        public static void Restart(UIApplication app) {
            Awareness.Clear();
            documentBaseline = null;
            viewBaseline = null;
            selectionBaseline = new HashSet<long>();
            RememberViewAndSelection(app.ActiveUIDocument);
        }

        /// <summary>
        /// What the user changed since the agent's last successful model request, or null.
        /// Call on the main thread before the request's own work.
        /// </summary>
        public static JObject SinceLastCall(UIApplication app) {
            if (AgentSessions.Tracker.State == AgentSessionState.Inactive)
                return null;
            var uidoc = app.ActiveUIDocument;
            CompareViewAndSelection(uidoc);
            return Awareness.Peek(() => DescribeView(uidoc), () => DescribeSelection(uidoc));
        }

        /// <summary>
        /// Starts over after a request succeeded, from the view and selection the request leaves
        /// behind.
        /// </summary>
        public static void Reset(UIApplication app) {
            Awareness.Clear();
            RememberViewAndSelection(app.ActiveUIDocument);
            RememberAgainWhenIdle(app);
        }

        /// <summary>
        /// Takes the view and selection a failed request left behind as the new baseline, and
        /// keeps what was recorded. The request's own changes then aren't reported as the user's,
        /// and the user's earlier changes still reach the next request.
        /// </summary>
        public static void Rebaseline(UIApplication app) {
            RememberViewAndSelection(app.ActiveUIDocument);
            RememberAgainWhenIdle(app);
        }

        /// <remarks>
        /// A view or selection change the user makes before Revit goes idle is taken as the
        /// request's own, so it isn't reported; that window is the moment the request returns.
        /// </remarks>
        private static void RememberAgainWhenIdle(UIApplication app) {
            lock (sync) {
                if (idleRecordQueued)
                    return;
                idleRecordQueued = true;
            }
            app.Idling += OnIdlingAfterRequest;
        }

        private static void OnIdlingAfterRequest(object sender, Autodesk.Revit.UI.Events.IdlingEventArgs e) {
            var app = sender as UIApplication;
            if (app != null)
                app.Idling -= OnIdlingAfterRequest;
            lock (sync)
                idleRecordQueued = false;
            RememberViewAndSelection(app?.ActiveUIDocument);
        }

        /// <remarks>
        /// Only from a session document, so a request made while another document is active keeps
        /// the earlier baseline.
        /// </remarks>
        private static void RememberViewAndSelection(UIDocument uidoc) {
            if (uidoc == null || !InSession(uidoc.Document))
                return;
            documentBaseline = AgentDocuments.Keys.KeyOf(uidoc.Document);
            viewBaseline = ActiveViewId(uidoc);
            selectionBaseline = SelectionIds(uidoc);
        }

        private static bool InSession(Document document) {
            return AgentSessions.Tracker.Contains(candidate => AgentDocuments.IsSame(candidate as Document, document));
        }

        private static void OnDocumentChanged(object sender, DocumentChangedEventArgs e) {
            var document = e.GetDocument();
            if (Awareness.IsSuppressed || IsRollback(e.Operation) || !InSession(document))
                return;
            Awareness.RecordEdit(
                AgentDocuments.Keys.KeyOf(document), document.Title,
                e.GetAddedElementIds().Select(AgentIds.ToValue),
                e.GetModifiedElementIds().Select(AgentIds.ToValue),
                e.GetDeletedElementIds().Select(AgentIds.ToValue),
                e.GetTransactionNames(),
                OperationName(e.Operation));
        }

        private static void CompareViewAndSelection(UIDocument uidoc) {
            if (uidoc == null || !InSession(uidoc.Document))
                return;
            var document = AgentDocuments.Keys.KeyOf(uidoc.Document);
            if (AgentAwareness.ViewDiffers(documentBaseline, viewBaseline, document, ActiveViewId(uidoc)))
                Awareness.RecordViewChange();
            if (AgentAwareness.SelectionDiffers(documentBaseline, selectionBaseline, document, SelectionIds(uidoc)))
                Awareness.RecordSelectionChange();
        }

        private static long? ActiveViewId(UIDocument uidoc) {
            var view = uidoc.ActiveView;
            return view == null ? (long?)null : AgentIds.ToValue(view.Id);
        }

        private static HashSet<long> SelectionIds(UIDocument uidoc) {
            return new HashSet<long>(uidoc.Selection.GetElementIds().Select(AgentIds.ToValue));
        }

        /// <remarks>
        /// A transaction rolled back on its own never committed, so nothing of it was recorded. A
        /// transaction group rolled back undoes transactions that did commit, so its changes are
        /// recorded to cancel theirs.
        /// </remarks>
        private static bool IsRollback(UndoOperation operation) {
            return operation == UndoOperation.TransactionRolledBack;
        }

        private static string OperationName(UndoOperation operation) {
            switch (operation) {
                case UndoOperation.TransactionUndone: return "undo";
                case UndoOperation.TransactionRedone: return "redo";
                case UndoOperation.TransactionGroupRolledBack: return "rollback";
                default: return "commit";
            }
        }

        private static JToken DescribeView(UIDocument uidoc) {
            var view = uidoc?.ActiveView;
            if (view == null)
                return JValue.CreateNull();
            return new JObject {
                ["document"] = AgentDocuments.Keys.KeyOf(uidoc.Document),
                ["document_title"] = uidoc.Document.Title,
                ["id"] = AgentIds.ToValue(view.Id),
                ["name"] = view.Name,
                ["type"] = view.ViewType.ToString(),
            };
        }

        private static JToken DescribeSelection(UIDocument uidoc) {
            if (uidoc == null)
                return JValue.CreateNull();
            var ids = uidoc.Selection.GetElementIds();
            return new JObject {
                ["document"] = AgentDocuments.Keys.KeyOf(uidoc.Document),
                ["document_title"] = uidoc.Document.Title,
                ["count"] = ids.Count,
                ["ids"] = new JArray(ids.Take(MaxSelectionIds).Select(AgentIds.ToValue)),
            };
        }
    }
}
