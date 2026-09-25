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
        }

        public static Request Parse(JObject parameters) {
            var action = (parameters.Value<string>("action") ?? "select").ToLowerInvariant();
            if (!Actions.Contains(action))
                throw new AgentException("invalid_params", "'action' must be one of: " + string.Join(", ", Actions) + ".");

            var request = new Request { Action = action, Zoom = parameters.Value<bool?>("zoom") ?? false };

            if (parameters["ids"] is JArray ids) {
                if (ids.Count > MaxIds)
                    throw new AgentException("invalid_params", $"At most {MaxIds} ids per call.");
                try {
                    request.Ids.AddRange(ids.Select(id => id.Value<long>()));
                }
                catch (Exception) {
                    throw new AgentException("invalid_params", "'ids' must contain integer element ids.");
                }
            }

            if (parameters["categories"] is JArray categories) {
                foreach (var token in categories) {
                    var name = token.Value<string>() ?? string.Empty;
                    var enumName = name.StartsWith("OST_", StringComparison.OrdinalIgnoreCase) ? name : "OST_" + name;
                    if (!Enum.TryParse(enumName, true, out BuiltInCategory category))
                        throw new AgentException("invalid_params", $"Unknown category '{name}'. Use BuiltInCategory names such as OST_Windows.");
                    request.Categories.Add(category);
                }
            }

            if (action != "reset" && request.Ids.Count == 0 && request.Categories.Count == 0)
                throw new AgentException("invalid_params", "Pass 'ids' and/or 'categories'.");

            return request;
        }

        public static JToken Show(UIApplication app, Request request) {
            var uidoc = app.ActiveUIDocument
                ?? throw new AgentException("no_active_document", "Revit has no active document.");
            var doc = uidoc.Document;
            var view = uidoc.ActiveView;
            if (doc.IsModifiable)
                throw new AgentException("revit_busy", "Another transaction is open in the active document.");

            var response = new JObject {
                ["action"] = request.Action,
                ["view"] = view == null ? null : new JObject {
                    ["id"] = AgentIds.ToValue(view.Id),
                    ["name"] = view.Name,
                    ["type"] = view.ViewType.ToString(),
                },
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
            response["count"] = targets.Count;
            if (missing.Count > 0)
                response["missing_ids"] = new JArray(missing.Take(100));

            if (targets.Count == 0) {
                response["note"] = "Nothing to show: no matching elements in the active view.";
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

            if (request.Zoom)
                uidoc.ShowElements(targets);
            uidoc.RefreshActiveView();
            return response;
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
            using (var transaction = new Transaction(doc, name)) {
                transaction.Start();
                change();
                transaction.Commit();
            }
        }
    }
}
