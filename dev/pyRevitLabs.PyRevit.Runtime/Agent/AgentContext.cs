using System;
using System.Linq;

using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

using pyRevitLabs.Json.Linq;
using pyRevitLabs.PyRevit;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Builds the <c>get_context</c> snapshot an agent reads before writing any script.
    /// </summary>
    internal static class AgentContext {
        private const int MaxSelectionIds = 200;
        private const int MaxLevels = 200;

        /// <remarks>
        /// <c>clone</c> is the clone the session actually loaded, with the engine, path, branch
        /// and commit beside it; the session env's clone name is the fallback, and the value is
        /// null rather than <c>Unknown</c> when neither knows. <c>attached</c> tells the agent
        /// why engine details may be missing.
        /// </remarks>
        private static JObject DescribePyRevit(EnvDictionary env, string revitVersion) {
            var identity = int.TryParse(revitVersion, out var revitYear)
                ? AgentSessionIdentity.Describe(revitYear)
                : new JObject();

            var clone = identity.Value<string>("clone");
            if (string.IsNullOrEmpty(clone) && env.PyRevitClone != "Unknown")
                clone = env.PyRevitClone;
            var description = new JObject {
                ["version"] = env.PyRevitVersion,
                ["clone"] = string.IsNullOrEmpty(clone) ? null : clone,
            };
            identity.Remove("clone");
            description.Merge(identity);
            description["attached"] = identity.Value<bool?>("attached") ?? false;
            return description;
        }

        /// <remarks>
        /// <c>reckless</c> appears only when it is on, so the agent knows its runs have no timeout.
        /// </remarks>
        private static JObject DescribeAgent() {
            var agent = new JObject {
                ["policy"] = AgentRunService.PolicyNameInForce(),
            };
            if (AgentRunService.RecklessInForce())
                agent["reckless"] = true;
            return agent;
        }

        public static JToken Describe(UIApplication app) {
            var env = new EnvDictionary();
            var context = new JObject {
                ["revit"] = new JObject {
                    ["version"] = app.Application.VersionNumber,
                    ["build"] = app.Application.VersionBuild,
                    ["language"] = app.Application.Language.ToString(),
                    ["username"] = app.Application.Username,
                },
                ["pyrevit"] = DescribePyRevit(env, app.Application.VersionNumber),
                ["agent"] = DescribeAgent(),
                ["scripting"] = AgentScripting.Describe(env, app.Application.VersionNumber),
                ["open_documents"] = AgentDocuments.Describe(app),
                ["document"] = null,
                ["active_view"] = null,
                ["selection"] = null,
                ["levels"] = null,
            };

            var uidoc = app.ActiveUIDocument;
            if (uidoc == null)
                return context;

            var doc = uidoc.Document;
            context["document"] = new JObject {
                ["title"] = doc.Title,
                ["path"] = doc.PathName,
                ["is_family"] = doc.IsFamilyDocument,
                ["is_workshared"] = doc.IsWorkshared,
                ["is_read_only"] = doc.IsReadOnly,
                ["is_modified"] = doc.IsModified,
            };

            var view = uidoc.ActiveView;
            if (view != null) {
                context["active_view"] = new JObject {
                    ["id"] = AgentIds.ToValue(view.Id),
                    ["name"] = view.Name,
                    ["type"] = view.ViewType.ToString(),
                };
            }

            var selectedIds = uidoc.Selection.GetElementIds();
            context["selection"] = new JObject {
                ["count"] = selectedIds.Count,
                ["ids"] = new JArray(selectedIds.Take(MaxSelectionIds).Select(AgentIds.ToValue)),
            };

            context["levels"] = new JArray(
                new FilteredElementCollector(doc)
                    .OfClass(typeof(Level))
                    .Cast<Level>()
                    .OrderBy(level => level.Elevation)
                    .Take(MaxLevels)
                    .Select(level => new JObject {
                        ["id"] = AgentIds.ToValue(level.Id),
                        ["name"] = level.Name,
                        ["elevation_ft"] = level.Elevation,
                    })
            );

            return context;
        }
    }

    internal static class AgentIds {
        public static long ToValue(ElementId id) {
#if REVIT2021 || REVIT2022 || REVIT2023
            return id.IntegerValue;
#else
            return id.Value;
#endif
        }

        /// <remarks>
        /// On Revit 2021-2023, whose ids are 32-bit, a value out of that range returns
        /// <see cref="ElementId.InvalidElementId"/>, which matches no element, instead of throwing.
        /// </remarks>
        public static ElementId FromValue(long value) {
#if REVIT2021 || REVIT2022 || REVIT2023
            return value < int.MinValue || value > int.MaxValue
                ? ElementId.InvalidElementId
                : new ElementId((int)value);
#else
            return new ElementId(value);
#endif
        }
    }
}
