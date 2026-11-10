using System;
using System.Collections.Generic;
using System.Linq;

using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Serves <c>show_elements</c>: selects, zooms to, or temporarily isolates or hides
    /// elements in the active view so an agent can show the user what it found.
    /// </summary>
    /// <remarks>
    /// Runs without the approval prompt because it is a fixed operation, not agent-written
    /// code, and it only touches presentation. Selection and zoom need no transaction.
    /// Temporary hide/isolate does, so it runs in its own small transaction; that state is
    /// not saved with the model and <c>reset</c> clears it.
    /// Invariant: nothing here may change model elements. Anything that does belongs in a
    /// <c>run</c> with approval.
    /// </remarks>
    internal static class AgentPresenter {
        private const int MaxIds = 20000;
        private static readonly string[] Actions = { "select", "isolate", "hide", "reset" };

        public sealed class Request {
            public string Action;
            public List<long> Ids = new List<long>();
            public List<BuiltInCategory> Categories = new List<BuiltInCategory>();
            public bool Zoom;
            public string DocumentTitle;
            public string DocumentPath;
        }

        public static Request Parse(JObject parameters) {
            var action = (AgentParams.Get<string>(parameters, "action") ?? "select").ToLowerInvariant();
            if (!Actions.Contains(action))
                throw new AgentException("invalid_params", "'action' must be one of: " + string.Join(", ", Actions) + ".");

            var request = new Request { Action = action, Zoom = AgentParams.Get<bool?>(parameters, "zoom") ?? false };

            if (parameters["ids"] is JArray ids) {
                if (ids.Count > MaxIds)
                    throw new AgentException("invalid_params", $"At most {MaxIds} ids per call.");
                request.Ids.AddRange(AgentParams.ElementIds(ids, "ids"));
            }

            if (parameters["categories"] is JArray categories) {
                foreach (var token in categories) {
                    var name = token.Value<string>() ?? string.Empty;
                    var enumName = name.StartsWith("OST_", StringComparison.OrdinalIgnoreCase) ? name : "OST_" + name;
                    if (!AgentSelectors.TryParseMember(enumName, out BuiltInCategory category))
                        throw new AgentException("invalid_params", $"Unknown category '{name}'. Use BuiltInCategory names such as OST_Windows.");
                    request.Categories.Add(category);
                }
            }

            if (action != "reset" && request.Ids.Count == 0 && request.Categories.Count == 0)
                throw new AgentException("invalid_params", "Pass 'ids' and/or 'categories'.");

            if (parameters["document"] is JObject document) {
                request.DocumentTitle = document.Value<string>("title");
                request.DocumentPath = document.Value<string>("path");
                if (string.IsNullOrEmpty(request.DocumentTitle) && string.IsNullOrEmpty(request.DocumentPath))
                    throw new AgentException("invalid_params", "'document' must name the source document.");
            }

            return request;
        }

        /// <summary>
        /// Applies the request to the active view.
        /// </summary>
        /// <remarks>
        /// Zooming can make Revit open a dialog, such as "Unable to find a suitable view" when
        /// no open view can show the elements. <paramref name="dialogs"/> closes it; the response
        /// then carries <c>zoomed: false</c> and a <c>zoom_failed</c> error with Revit's message,
        /// while the selection or isolation already applied stays in place.
        /// Ids the active view doesn't show are listed in <c>not_in_view_ids</c>. Isolate and hide
        /// also leave them out of <c>count</c>; select keeps them, so <c>zoom</c> can still open
        /// another view that shows them. A temporary view change Revit rolls back fails with
        /// <c>show_failed</c> instead of reporting success. <c>view</c> is the view the action
        /// applied to; when zooming makes Revit open another view, <c>active_view</c> names it.
        /// </remarks>
        public static JToken Show(UIApplication app, Request request, AgentDialogCapture dialogs) {
            var uidoc = app.ActiveUIDocument;
            var linksDocument = request.Action != "reset"
                && (!string.IsNullOrEmpty(request.DocumentTitle) || !string.IsNullOrEmpty(request.DocumentPath));
            if (linksDocument && (uidoc == null || !MatchesDocument(uidoc.Document, request)))
                throw new AgentException("stale_link", "The link belongs to a different or closed document. Activate its document, then inspect the elements again.");
            if (uidoc == null)
                throw new AgentException("no_active_document", "Revit has no active document.");
            var doc = uidoc.Document;
            var view = uidoc.ActiveView;
            if (doc.IsModifiable)
                throw AgentException.NotRun("Another transaction is open in the active document.");

            var response = new JObject {
                ["action"] = request.Action,
                ["view"] = DescribeView(view),
            };

            if (request.Action == "reset") {
                var wasActive = view != null && view.IsTemporaryHideIsolateActive();
                if (wasActive)
                    InTransaction(doc, "Agent: reset temporary hide/isolate",
                        () => view.DisableTemporaryViewMode(TemporaryViewMode.TemporaryHideIsolate));
                response["reset"] = wasActive;
                uidoc.RefreshActiveView();
                return response;
            }

            var missing = new List<long>();
            var targets = ResolveTargets(doc, view, request, missing);
            if (request.Ids.Count > 0 && targets.Count > 0 && view != null && !view.IsTemplate && view.CanUseTemporaryVisibilityModes()) {
                var inView = new HashSet<ElementId>(new FilteredElementCollector(doc, view.Id)
                    .WherePasses(new ElementIdSetFilter(targets))
                    .ToElementIds());
                var notInView = targets.Where(id => !inView.Contains(id)).ToList();
                if (notInView.Count > 0) {
                    response["not_in_view_ids"] = new JArray(notInView.Take(100).Select(AgentIds.ToValue));
                    if (request.Action != "select")
                        targets = targets.Where(inView.Contains).ToList();
                    if (request.Action != "select" && view.IsTemporaryHideIsolateActive())
                        response["note"] = "Some elements are not shown in the active view, possibly hidden by its temporary hide/isolate; "
                            + "call action 'reset' first to include them.";
                }
            }
            response["count"] = targets.Count;
            if (missing.Count > 0)
                response["missing_ids"] = new JArray(missing.Take(100));

            if (targets.Count == 0) {
                response["note"] = "Nothing to show: no matching elements in the active view."
                    + (response["note"] == null ? string.Empty : " " + response.Value<string>("note"));
                return response;
            }

            switch (request.Action) {
                case "select":
                    uidoc.Selection.SetElementIds(targets);
                    break;
                case "isolate":
                case "hide":
                    if (view == null || view.IsTemplate || !view.CanUseTemporaryVisibilityModes())
                        throw new AgentException("view_not_supported",
                            $"The active view ({view?.Name}) does not support temporary hide/isolate. Use action 'select', or open a plan, section, elevation or 3D view.");
                    InTransaction(doc, $"Agent: {request.Action} {targets.Count} elements", () => {
                        if (request.Action == "isolate")
                            view.IsolateElementsTemporary(targets);
                        else
                            view.HideElementsTemporary(targets);
                    });
                    break;
            }

            if (request.Zoom) {
                Zoom(uidoc, targets, dialogs, response);
                var activeAfterZoom = app.ActiveUIDocument?.ActiveView;
                if (activeAfterZoom != null && (view == null || !activeAfterZoom.Id.Equals(view.Id)))
                    response["active_view"] = DescribeView(activeAfterZoom);
            }
            uidoc.RefreshActiveView();
            return response;
        }

        private static JObject DescribeView(View view) {
            return view == null ? null : new JObject {
                ["id"] = AgentIds.ToValue(view.Id),
                ["name"] = view.Name,
                ["type"] = view.ViewType.ToString(),
            };
        }

        private static bool MatchesDocument(Document document, Request request) {
            if (string.IsNullOrEmpty(request.DocumentTitle) && string.IsNullOrEmpty(request.DocumentPath))
                return true;
            if (!string.IsNullOrEmpty(request.DocumentPath)
                && !string.Equals(document.PathName, request.DocumentPath, StringComparison.OrdinalIgnoreCase))
                return false;
            return string.IsNullOrEmpty(request.DocumentTitle)
                || string.Equals(
                    document.Title,
                    request.DocumentTitle,
                    string.IsNullOrEmpty(request.DocumentPath)
                        ? StringComparison.Ordinal
                        : StringComparison.OrdinalIgnoreCase);
        }

        private static void Zoom(UIDocument uidoc, ICollection<ElementId> targets, AgentDialogCapture dialogs, JObject response) {
            var shownBefore = dialogs.Shown;
            var recordedBefore = dialogs.Dialogs.Count;
            uidoc.ShowElements(targets);
            var zoomed = dialogs.Shown == shownBefore;
            response["zoomed"] = zoomed;
            if (!zoomed)
                response["zoom_error"] = new JObject {
                    ["type"] = "zoom_failed",
                    ["message"] = "Revit could not zoom to the elements: "
                        + ((dialogs.Dialogs.Count > recordedBefore ? dialogs.Dialogs[recordedBefore].Value<string>("message") : null)
                            ?? "it showed a dialog, which was closed.")
                        + " Open a view that shows them, then call again.",
                };
        }

        private static List<ElementId> ResolveTargets(Document doc, View view, Request request, List<long> missing) {
            var targets = new List<ElementId>();
            var seen = new HashSet<long>();

            foreach (var value in request.Ids) {
                var id = AgentIds.FromValue(value);
                if (doc.GetElement(id) == null) {
                    missing.Add(value);
                    continue;
                }
                if (seen.Add(value))
                    targets.Add(id);
            }

            foreach (var category in request.Categories) {
                var collector = view != null && !view.IsTemplate
                    ? new FilteredElementCollector(doc, view.Id)
                    : new FilteredElementCollector(doc);
                foreach (var id in collector.OfCategory(category).WhereElementIsNotElementType().ToElementIds()) {
                    if (seen.Add(AgentIds.ToValue(id)))
                        targets.Add(id);
                }
            }

            return targets;
        }

        private static void InTransaction(Document doc, string name, Action change) {
            if (doc.IsReadOnly)
                throw new AgentException("document_read_only", "Temporary hide/isolate needs a transaction, which a read-only document doesn't allow.");
            using (var transaction = new Transaction(doc, name)) {
                if (transaction.Start() != TransactionStatus.Started)
                    throw new AgentException("show_failed", "Revit did not start the transaction for the temporary view change.");
                change();
                var status = transaction.Commit();
                if (status == TransactionStatus.RolledBack)
                    throw new AgentException("show_failed", "Revit rolled back the temporary view change; the view is unchanged.");
                if (status != TransactionStatus.Committed)
                    throw new AgentException("show_failed",
                        $"Revit did not confirm the temporary view change (status {status}); check the view before relying on it.");
            }
        }
    }
}
