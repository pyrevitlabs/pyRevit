using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;

using pyRevitLabs.Json.Linq;

namespace pyRevitCLI {
    /// <summary>
    /// Reviewed Python automation operations that can run through the guarded agent host.
    /// </summary>
    internal static class PyRevitAutomationOperations {
        private sealed class Operation {
            public string Id { get; set; }
            public string Title { get; set; }
            public string Source { get; set; }
            public bool RequiresDocument { get; set; }
            public Func<JObject, JObject> ValidateInputs { get; set; }
        }

        private static readonly Regex BuiltInCategoryName = new Regex("^OST_[A-Za-z0-9_]{1,124}$");

        private static readonly Dictionary<string, Operation> Operations = new Dictionary<string, Operation>(StringComparer.OrdinalIgnoreCase) {
            ["pyrevit.units.parse-length"] = new Operation {
                Id = "pyrevit.units.parse-length",
                Title = "Normalize length",
                Source = "from pyrevit.revit import units\nresult = {'value': units.parse_length(inputs['value'])}\n",
                ValidateInputs = inputs => ValidateSingleInput(inputs, "value", false),
            },
            ["pyrevit.units.parse-slope"] = new Operation {
                Id = "pyrevit.units.parse-slope",
                Title = "Normalize slope",
                Source = "from pyrevit.revit import units\nresult = {'value': units.parse_slope(inputs['value'])}\n",
                ValidateInputs = inputs => ValidateSingleInput(inputs, "value", false),
            },
            ["pyrevit.levels.resolve"] = new Operation {
                Id = "pyrevit.levels.resolve",
                Title = "Resolve level",
                Source = "from pyrevit.revit.db import query\nresult = {'level': query.find_level(inputs['name'], doc=doc)}\n",
                RequiresDocument = true,
                ValidateInputs = inputs => ValidateSingleInput(inputs, "name", true),
            },
            ["pyrevit.elements.by-category"] = new Operation {
                Id = "pyrevit.elements.by-category",
                Title = "Find elements by category",
                Source = "from pyrevit.revit.db import query\nelements = list(query.get_elements_by_categories(inputs['categories'], doc=doc))\nlimited = elements[:inputs['limit']]\nunknown = [name for name in inputs['categories'] if query.get_category(name, doc=doc) is None]\nresult = {'elements': limited, 'total': len(elements), 'truncated': len(elements) > len(limited), 'unknown_categories': unknown}\n",
                RequiresDocument = true,
                ValidateInputs = ValidateCategoryCollection,
            },
        };

        public static bool IsInvocable(string id) {
            return !string.IsNullOrWhiteSpace(id) && Operations.ContainsKey(id);
        }

        /// <summary>
        /// Resolves a reviewed operation and validates its bounded input object.
        /// </summary>
        public static JObject Resolve(string id, JToken input) {
            if (string.IsNullOrWhiteSpace(id))
                throw new AgentClientException("invalid_params", "'id' is required.");
            Operation operation;
            if (!Operations.TryGetValue(id, out operation)) {
                if (PyRevitLibraryIndex.IsMarkedAutomation(id))
                    throw new AgentClientException("automation_not_exposed", $"'{id}' is listed by list_automation but cannot be run through run_automation. Call it from a run_query or run_modify script instead.");
                throw new AgentClientException("unknown_automation_id", $"'{id}' is not an invocable automation operation.");
            }

            var inputs = input as JObject
                ?? throw new AgentClientException("invalid_params", "'inputs' must be an object.");
            inputs = operation.ValidateInputs(inputs);

            return new JObject {
                ["id"] = operation.Id,
                ["title"] = operation.Title,
                ["source"] = operation.Source,
                ["requires_document"] = operation.RequiresDocument,
                ["inputs"] = inputs,
            };
        }

        private static JObject ValidateSingleInput(JObject inputs, string name, bool stringOnly) {
            if (inputs.Properties().Any(property => property.Name != name))
                throw new AgentClientException("invalid_params", $"'inputs' accepts only '{name}'.");
            var value = inputs[name];
            if (value == null || (value.Type != JTokenType.Integer && value.Type != JTokenType.Float && value.Type != JTokenType.String))
                throw new AgentClientException("invalid_params", $"'inputs.{name}' must be a number or string.");
            if (stringOnly && value.Type != JTokenType.String)
                throw new AgentClientException("invalid_params", $"'inputs.{name}' must be a string.");
            if (value.Type == JTokenType.String && (value.Value<string>().Length > 256 || string.IsNullOrWhiteSpace(value.Value<string>())))
                throw new AgentClientException("invalid_params", $"'inputs.{name}' must be non-empty and contain at most 256 characters.");
            return inputs;
        }

        private static JObject ValidateCategoryCollection(JObject inputs) {
            if (inputs.Properties().Any(property => property.Name != "categories" && property.Name != "limit"))
                throw new AgentClientException("invalid_params", "'inputs' accepts only 'categories' and 'limit'.");
            var categories = inputs["categories"] as JArray;
            if (categories == null || categories.Count == 0 || categories.Count > 20 || categories.Any(category => category.Type != JTokenType.String || !BuiltInCategoryName.IsMatch(category.Value<string>())))
                throw new AgentClientException("invalid_params", "'inputs.categories' must contain 1 to 20 BuiltInCategory names such as OST_Walls. Display names like 'Walls' depend on the Revit language.");
            var limit = inputs["limit"];
            if (limit == null) {
                inputs["limit"] = 50;
                return inputs;
            }
            if (limit.Type != JTokenType.Integer || limit.Value<long>() < 1 || limit.Value<long>() > 200)
                throw new AgentClientException("invalid_params", "'inputs.limit' must be an integer from 1 to 200.");
            return inputs;
        }
    }
}
