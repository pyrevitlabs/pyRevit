using System.Collections.Generic;
using System.Linq;

using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Events;
using Autodesk.Revit.UI;

using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Watches Revit for what the user changes in the session's document between an agent's
    /// calls, and builds the <c>since_last_call</c> summary from <see cref="Awareness"/>.
    /// </summary>
    /// <remarks>
    /// Edits come from <c>DocumentChanged</c>. The active view and the selection are compared,
    /// when the next request arrives, with the ones the last request left behind in the session's
    /// document, on every Revit version. Events would report a round trip to another document as
    /// a view change, <c>SelectionChanged</c> exists only from Revit 2023, and when Revit raises
    /// either for the host's own changes is not something to rely on.
    /// Invariant: only the session's document is watched, and nothing is recorded while the
    /// host handles a request; see <see cref="AgentAwareness"/>.
    /// </remarks>
    internal static class AgentAwarenessWatch {
        internal static readonly AgentAwareness Awareness = new AgentAwareness();

        private const int MaxSelectionIds = 200;
        private static readonly object sync = new object();
        private static bool attached;
        private static HashSet<long> selectionBaseline = new HashSet<long>();
        private static long? viewBaseline;

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
            RememberViewAndSelection(app.ActiveUIDocument);
        }

        /// <summary>
        /// What the user changed since the agent's last successful model request, or null.
        /// Call on the main thread before the request's own work.
        /// </summary>
        public static JObject SinceLastCall(UIApplication app) {
            if (AgentSessions.Tracker.BoundDocument == null)
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
        }

        /// <remarks>
        /// Only from the session's document, so a request made while another document is active
        /// keeps the earlier baseline.
        /// </remarks>
        private static void RememberViewAndSelection(UIDocument uidoc) {
            if (uidoc == null || !IsBound(uidoc.Document))
                return;
            viewBaseline = ActiveViewId(uidoc);
            selectionBaseline = SelectionIds(uidoc);
        }

        private static bool IsBound(Document document) {
            var bound = AgentSessions.Tracker.BoundDocument as Document;
            return bound != null && AgentDocuments.IsSame(bound, document);
        }

        private static void OnDocumentChanged(object sender, DocumentChangedEventArgs e) {
            if (Awareness.IsSuppressed || IsRollback(e.Operation) || !IsBound(e.GetDocument()))
                return;
            Awareness.RecordEdit(
                e.GetAddedElementIds().Select(AgentIds.ToValue),
                e.GetModifiedElementIds().Select(AgentIds.ToValue),
                e.GetDeletedElementIds().Select(AgentIds.ToValue),
                e.GetTransactionNames(),
                OperationName(e.Operation));
        }

        private static void CompareViewAndSelection(UIDocument uidoc) {
            if (uidoc == null || !IsBound(uidoc.Document))
                return;
            if (ActiveViewId(uidoc) != viewBaseline)
                Awareness.RecordViewChange();
            if (!SelectionIds(uidoc).SetEquals(selectionBaseline))
                Awareness.RecordSelectionChange();
        }

        private static long? ActiveViewId(UIDocument uidoc) {
            var view = uidoc.ActiveView;
            return view == null ? (long?)null : AgentIds.ToValue(view.Id);
        }

        private static HashSet<long> SelectionIds(UIDocument uidoc) {
            return new HashSet<long>(uidoc.Selection.GetElementIds().Select(AgentIds.ToValue));
        }

        private static bool IsRollback(UndoOperation operation) {
            return operation == UndoOperation.TransactionRolledBack || operation == UndoOperation.TransactionGroupRolledBack;
        }

        private static string OperationName(UndoOperation operation) {
            switch (operation) {
                case UndoOperation.TransactionUndone: return "undo";
                case UndoOperation.TransactionRedone: return "redo";
                default: return "commit";
            }
        }

        private static JToken DescribeView(UIDocument uidoc) {
            var view = uidoc?.ActiveView;
            if (view == null)
                return JValue.CreateNull();
            return new JObject {
                ["id"] = AgentIds.ToValue(view.Id),
                ["name"] = view.Name,
                ["type"] = view.ViewType.ToString(),
                ["document"] = uidoc.Document.Title,
            };
        }

        private static JToken DescribeSelection(UIDocument uidoc) {
            if (uidoc == null)
                return JValue.CreateNull();
            var ids = uidoc.Selection.GetElementIds();
            return new JObject {
                ["count"] = ids.Count,
                ["ids"] = new JArray(ids.Take(MaxSelectionIds).Select(AgentIds.ToValue)),
            };
        }
    }
}
