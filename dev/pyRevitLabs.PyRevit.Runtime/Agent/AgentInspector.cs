using System;
using System.Collections.Generic;
using System.Linq;

using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Describes elements for the <c>inspect_elements</c> method, so an agent can learn an
    /// element's parameters without writing a script first.
    /// </summary>
    /// <remarks>
    /// Read-only: never opens a transaction. Numeric parameter values are reported both as
    /// Revit displays them and raw in internal units (feet, radians). An element Revit can't
    /// describe gets an <c>error</c> entry instead of failing the whole batch. When any of those
    /// errors is a memory access error, the response carries one <c>note</c> saying how many, not
    /// one per element: Revit 2024 raised it for every Material Asset in a batch.
    /// </remarks>
    internal static class AgentInspector {
        private const int MaxElements = 50;

        public static List<ElementId> ParseIds(JObject parameters) {
            var ids = parameters["ids"] as JArray;
            if (ids == null || ids.Count == 0)
                throw new AgentException("invalid_params", "'ids' must be a non-empty array of element ids.");
            if (ids.Count > MaxElements)
                throw new AgentException(
                    "invalid_params",
                    string.Format("At most {0} elements can be inspected per call.", MaxElements));

            return AgentParams.ElementIds(ids, "ids").Select(AgentIds.FromValue).ToList();
        }

        public static JToken Inspect(UIApplication app, List<ElementId> ids, bool includeParameters) {
            var uidoc = app.ActiveUIDocument
                ?? throw new AgentException("no_active_document", "Revit has no active document.");
            var doc = uidoc.Document;
            var elements = new JArray();
            var memoryErrors = 0;
            foreach (var id in ids)
                elements.Add(DescribeOrReportError(doc, id, includeParameters, ref memoryErrors));
            var response = new JObject {
                ["document"] = DocumentReference(doc),
                ["elements"] = elements,
            };
            if (memoryErrors > 0)
                response["note"] = string.Format(
                    "Revit hit a memory access error reading {0} of these elements and may be unstable; save your work before continuing.",
                    memoryErrors);
            return response;
        }

        private static JObject DescribeOrReportError(Document doc, ElementId id, bool includeParameters, ref int memoryErrors) {
            try {
                return Describe(doc, id, includeParameters);
            }
            catch (Exception ex) {
                var entry = new JObject { ["id"] = AgentIds.ToValue(id), ["found"] = true };
                try {
                    var element = doc.GetElement(id);
                    entry["class"] = element.GetType().Name;
                    entry["name"] = SafeName(element);
                    entry["category"] = element.Category?.Name;
                }
                catch (Exception) {
                }
                entry["error"] = ex.Message;
                if (ex is AccessViolationException)
                    memoryErrors++;
                return entry;
            }
        }

        private static JObject Describe(Document doc, ElementId id, bool includeParameters) {
            var element = doc.GetElement(id);
            if (element == null)
                return new JObject { ["id"] = AgentIds.ToValue(id), ["found"] = false };

            var description = new JObject {
                ["id"] = AgentIds.ToValue(id),
                ["found"] = true,
                ["unique_id"] = element.UniqueId,
                ["class"] = element.GetType().Name,
                ["category"] = element.Category?.Name,
                ["name"] = SafeName(element),
                ["type"] = DescribeReference(doc, element.GetTypeId()),
                ["level"] = DescribeReference(doc, element.LevelId),
                ["owner_view"] = DescribeReference(doc, element.OwnerViewId),
                ["workset"] = DescribeWorkset(doc, element),
                ["location"] = DescribeLocation(element.Location),
                ["bounding_box"] = DescribeBoundingBox(element.get_BoundingBox(null)),
                ["link"] = new JObject {
                    ["destination"] = "element",
                    ["document"] = DocumentReference(doc),
                    ["ids"] = new JArray(AgentIds.ToValue(id)),
                },
            };

            if (includeParameters)
                description["parameters"] = DescribeParameters(element);

            return description;
        }

        private static JObject DocumentReference(Document doc) {
            return new JObject {
                ["title"] = doc.Title,
                ["path"] = doc.PathName,
            };
        }

        private static JArray DescribeParameters(Element element) {
            var parameters = new List<Parameter>();
            foreach (Parameter parameter in element.Parameters)
                parameters.Add(parameter);

            return new JArray(
                parameters
                    .OrderBy(parameter => parameter.Definition?.Name, StringComparer.OrdinalIgnoreCase)
                    .Select(DescribeParameter));
        }

        private static JObject DescribeParameter(Parameter parameter) {
            var description = new JObject {
                ["name"] = parameter.Definition?.Name,
                ["storage"] = parameter.StorageType.ToString(),
                ["display"] = SafeValueString(parameter),
                ["value"] = RawValue(parameter),
                ["read_only"] = parameter.IsReadOnly,
            };

            if (parameter.Definition is InternalDefinition internalDefinition
                && internalDefinition.BuiltInParameter != BuiltInParameter.INVALID)
                description["builtin"] = internalDefinition.BuiltInParameter.ToString();

            if (parameter.IsShared)
                description["shared_guid"] = parameter.GUID.ToString();

            return description;
        }

        private static JToken RawValue(Parameter parameter) {
            if (!parameter.HasValue)
                return null;
            switch (parameter.StorageType) {
                case StorageType.Double: return parameter.AsDouble();
                case StorageType.Integer: return parameter.AsInteger();
                case StorageType.String: return parameter.AsString();
                case StorageType.ElementId: return AgentIds.ToValue(parameter.AsElementId());
                default: return null;
            }
        }

        private static string SafeValueString(Parameter parameter) {
            try {
                return parameter.AsValueString() ?? parameter.AsString();
            }
            catch (Exception) {
                return null;
            }
        }

        private static JToken DescribeReference(Document doc, ElementId id) {
            if (id == null || id == ElementId.InvalidElementId)
                return null;
            return new JObject {
                ["id"] = AgentIds.ToValue(id),
                ["name"] = SafeName(doc.GetElement(id)),
            };
        }

        private static JToken DescribeWorkset(Document doc, Element element) {
            if (!doc.IsWorkshared)
                return null;
            var workset = doc.GetWorksetTable().GetWorkset(element.WorksetId);
            return workset?.Name;
        }

        private static JToken DescribeLocation(Location location) {
            if (location is LocationPoint point) {
                return new JObject {
                    ["point"] = ToArray(point.Point),
                    ["rotation"] = SafeRotation(point),
                };
            }
            if (location is LocationCurve curve) {
                return new JObject {
                    ["start"] = ToArray(curve.Curve.GetEndPoint(0)),
                    ["end"] = ToArray(curve.Curve.GetEndPoint(1)),
                    ["length"] = curve.Curve.Length,
                };
            }
            return null;
        }

        private static JToken SafeRotation(LocationPoint point) {
            try {
                return point.Rotation;
            }
            catch (Exception) {
                return null;
            }
        }

        private static JToken DescribeBoundingBox(BoundingBoxXYZ box) {
            if (box == null)
                return null;
            return new JObject {
                ["min"] = ToArray(box.Min),
                ["max"] = ToArray(box.Max),
            };
        }

        private static JArray ToArray(XYZ point) {
            return new JArray(point.X, point.Y, point.Z);
        }

        private static string SafeName(Element element) {
            if (element == null)
                return null;
            try {
                return element.Name;
            }
            catch (Exception) {
                return null;
            }
        }
    }
}
