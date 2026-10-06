using System.Collections.Generic;
using System.Linq;

using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Events;
using Autodesk.Revit.UI;
using Autodesk.Revit.UI.Events;

using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Watches Revit for what the user changes in the session's document between an agent's
    /// calls, and builds the <c>since_last_call</c> summary from <see cref="Awareness"/>.
    /// </summary>
    /// <remarks>
    /// Edits come from <c>DocumentChanged</c> and view switches from <c>ViewActivated</c>. The
    /// selection is compared, when the next request arrives, with the one the last request left
    /// behind, on every Revit version: <c>SelectionChanged</c> exists only from Revit 2023, and
    /// when it is raised for the host's own selection changes is not something to rely on.
    /// Invariant: only the session's document is watched, and nothing is recorded while the
    /// host handles a request; see <see cref="AgentAwareness"/>.
    /// </remarks>
    internal static class AgentAwarenessWatch {
        internal static readonly AgentAwareness Awareness = new AgentAwareness();

        private const int MaxSelectionIds = 200;
        private static readonly object sync = new object();
        private static bool attached;
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
            uiApp.ViewActivated += OnViewActivated;
        }

        /// <summary>
        /// Forgets earlier changes when a session starts, so its first call reports nothing.
        /// </summary>
        public static void Restart(UIApplication app) {
            Awareness.Clear();
            RememberSelection(app);
        }

        /// <summary>
        /// What the user changed since the agent's last successful model request, or null.
        /// Call on the main thread before the request's own work.
        /// </summary>
        public static JObject SinceLastCall(UIApplication app) {
            if (AgentSessions.Tracker.BoundDocument == null)
                return null;
            var uidoc = app.ActiveUIDocument;
            CompareSelection(uidoc);
            return Awareness.Peek(() => DescribeView(uidoc), () => DescribeSelection(uidoc));
        }

        /// <summary>
        /// Starts over after a request succeeded, from the selection the request leaves behind.
        /// </summary>
        public static void Reset(UIApplication app) {
            Awareness.Clear();
            RememberSelection(app);
        }

        private static void RememberSelection(UIApplication app) {
            selectionBaseline = SelectionIds(app.ActiveUIDocument);
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

        private static void OnViewActivated(object sender, ViewActivatedEventArgs e) {
            if (!Awareness.IsSuppressed && AgentSessions.Tracker.BoundDocument != null)
                Awareness.RecordViewChange();
        }

        private static void CompareSelection(UIDocument uidoc) {
            if (uidoc == null || !IsBound(uidoc.Document))
                return;
            if (!SelectionIds(uidoc).SetEquals(selectionBaseline))
                Awareness.RecordSelectionChange();
        }

        private static HashSet<long> SelectionIds(UIDocument uidoc) {
            if (uidoc == null)
                return new HashSet<long>();
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
