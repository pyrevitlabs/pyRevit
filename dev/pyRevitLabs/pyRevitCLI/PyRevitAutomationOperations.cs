using System;
using System.Collections.Generic;
using System.Linq;

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
        }

        private static readonly Dictionary<string, Operation> Operations = new Dictionary<string, Operation>(StringComparer.OrdinalIgnoreCase) {
            ["pyrevit.units.parse-length"] = new Operation {
                Id = "pyrevit.units.parse-length",
                Title = "Normalize length",
                Source = "from pyrevit.revit import units\nresult = {'value': units.parse_length(inputs['value'])}\n",
            },
            ["pyrevit.units.parse-slope"] = new Operation {
                Id = "pyrevit.units.parse-slope",
                Title = "Normalize slope",
                Source = "from pyrevit.revit import units\nresult = {'value': units.parse_slope(inputs['value'])}\n",
            },
        };

        /// <summary>
        /// Resolves a reviewed operation and validates its bounded input object.
        /// </summary>
        public static JObject Resolve(string id, JToken input) {
            if (string.IsNullOrWhiteSpace(id))
                throw new AgentClientException("invalid_params", "'id' is required.");
            Operation operation;
            if (!Operations.TryGetValue(id, out operation))
                throw new AgentClientException("unknown_automation_id", $"'{id}' is not an invocable automation operation.");

            var inputs = input as JObject
                ?? throw new AgentClientException("invalid_params", "'inputs' must be an object.");
            if (inputs.Properties().Any(property => property.Name != "value"))
                throw new AgentClientException("invalid_params", "'inputs' accepts only 'value'.");
            var value = inputs["value"];
            if (value == null || (value.Type != JTokenType.Integer && value.Type != JTokenType.Float && value.Type != JTokenType.String))
                throw new AgentClientException("invalid_params", "'inputs.value' must be a number or string.");
            if (value.Type == JTokenType.String && value.Value<string>().Length > 256)
                throw new AgentClientException("invalid_params", "'inputs.value' must contain at most 256 characters.");

            return new JObject {
                ["id"] = operation.Id,
                ["title"] = operation.Title,
                ["source"] = operation.Source,
                ["inputs"] = inputs,
            };
        }
    }
}
