using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;

using pyRevitLabs.Json.Linq;

namespace pyRevitCLI {
    /// <summary>
    /// One entry of an automation marker's <c>inputs</c> declaration, such as
    /// <c>"element: element"</c> or <c>"title_on_sheet: boolean?"</c>.
    /// </summary>
    /// <remarks>
    /// Mirrors <c>parse_inputs</c> and <c>validate_inputs</c> in <c>pyrevitlib/pyrevit_automation.py</c>,
    /// which check the same inputs again inside Revit.
    /// </remarks>
    internal sealed class AutomationInput {
        public const int MaxTextLength = 256;

        public static readonly string[] Types = { "string", "number", "integer", "boolean", "element", "scalar" };

        private static readonly Regex Spec = new Regex(@"^\s*(?<name>[A-Za-z_][A-Za-z0-9_]*)\s*:\s*(?<type>[a-z]+)\s*(?<optional>\?)?\s*$", RegexOptions.Compiled);

        public string Name { get; private set; }
        public string Type { get; private set; }
        public bool Required { get; private set; }

        /// <summary>
        /// Parses a declaration, throwing <c>invalid_automation_marker</c> for a malformed entry,
        /// an unknown type or a name declared twice.
        /// </summary>
        public static List<AutomationInput> ParseAll(IEnumerable<string> specs) {
            var inputs = new List<AutomationInput>();
            foreach (var spec in specs) {
                var match = Spec.Match(spec ?? string.Empty);
                if (!match.Success || !Types.Contains(match.Groups["type"].Value))
                    throw new AgentClientException("invalid_automation_marker", $"Automation input '{spec}' must look like 'name: type' with a type of {string.Join(", ", Types)}.");
                var name = match.Groups["name"].Value;
                if (inputs.Any(input => input.Name == name))
                    throw new AgentClientException("invalid_automation_marker", $"Automation input '{name}' is declared twice.");
                inputs.Add(new AutomationInput {
                    Name = name,
                    Type = match.Groups["type"].Value,
                    Required = !match.Groups["optional"].Success,
                });
            }
            return inputs;
        }

        public JObject ToJson() {
            return new JObject {
                ["name"] = Name,
                ["type"] = Type,
                ["required"] = Required,
            };
        }

        /// <summary>
        /// Checks an input object against a declaration and returns it unchanged.
        /// </summary>
        public static JObject Validate(List<AutomationInput> declared, JToken input) {
            var inputs = input as JObject
                ?? throw new AgentClientException("invalid_params", "'inputs' must be an object.");
            var unknown = inputs.Properties()
                .Select(property => property.Name)
                .Where(name => declared.All(spec => spec.Name != name))
                .OrderBy(name => name, StringComparer.Ordinal)
                .ToList();
            if (unknown.Count > 0) {
                var accepted = declared.Count == 0 ? "nothing" : string.Join(", ", declared.Select(spec => spec.Name).OrderBy(name => name, StringComparer.Ordinal));
                throw new AgentClientException("invalid_params", $"'inputs' accepts only {accepted} (got {string.Join(", ", unknown)}).");
            }
            foreach (var spec in declared) {
                var value = inputs[spec.Name];
                if (value == null || value.Type == JTokenType.Null) {
                    if (spec.Required)
                        throw new AgentClientException("invalid_params", $"'inputs.{spec.Name}' is required.");
                    if (value != null)
                        throw new AgentClientException("invalid_params", $"'inputs.{spec.Name}' must be left out rather than null.");
                    continue;
                }
                spec.Check(value);
            }
            return inputs;
        }

        private void Check(JToken value) {
            switch (Type) {
                case "string":
                    CheckText(value);
                    return;
                case "boolean":
                    if (value.Type != JTokenType.Boolean)
                        throw Invalid("must be true or false");
                    return;
                case "integer":
                    if (!IsInt64(value))
                        throw Invalid("must be an integer");
                    return;
                case "element":
                    if (!IsInt64(value))
                        throw Invalid("must be an element id");
                    return;
                case "number":
                    if (!IsNumber(value))
                        throw Invalid("must be a finite number");
                    return;
                case "scalar":
                    if (value.Type == JTokenType.String)
                        CheckText(value);
                    else if (value.Type != JTokenType.Boolean && !IsNumber(value))
                        throw Invalid("must be a string, a finite number or a boolean");
                    return;
                default:
                    throw Invalid("has an unknown type");
            }
        }

        private void CheckText(JToken value) {
            if (value.Type != JTokenType.String)
                throw Invalid("must be a string");
            var text = value.Value<string>();
            if (string.IsNullOrWhiteSpace(text) || text.Length > MaxTextLength)
                throw Invalid($"must be non-empty and contain at most {MaxTextLength} characters");
        }

        /// <summary>
        /// True for a JSON integer that fits in Int64; a larger one parses as a BigInteger.
        /// </summary>
        private static bool IsInt64(JToken value) {
            var raw = (value as JValue)?.Value;
            return value.Type == JTokenType.Integer && (raw is long || raw is int);
        }

        private static bool IsNumber(JToken value) {
            if (IsInt64(value))
                return true;
            if (value.Type != JTokenType.Float)
                return false;
            var number = value.Value<double>();
            return !double.IsNaN(number) && !double.IsInfinity(number);
        }

        private AgentClientException Invalid(string problem) {
            return new AgentClientException("invalid_params", $"'inputs.{Name}' {problem}.");
        }
    }

    /// <summary>
    /// Reviewed Python automation operations that can run through the guarded agent host.
    /// </summary>
    /// <remarks>
    /// An operation is invocable when it is hand-wired below, or when its marker in
    /// pyrevitlib or rpw declares <c>inputs</c> on a module-level <c>query</c> or <c>pure</c>
    /// function that opens no transaction. Hand-wired entries take precedence. Marked operations
    /// run through a fixed script; the function to call travels in the run's inputs, and
    /// <c>pyrevit.agent._operations</c> checks the live marker again before calling it.
    /// </remarks>
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

        /// <summary>
        /// The script every marked operation runs; <c>inputs</c> carries the operation and its inputs.
        /// </summary>
        internal const string MarkedOperationSource =
            "from pyrevit.agent import _operations\n"
            + "result = _operations.invoke(inputs['operation'], inputs['inputs'], doc)\n";

        private const int MaxTitleLength = 80;

        private static readonly Regex ModuleName = new Regex(@"^(?:pyrevit|rpw)(?:\.[A-Za-z_][A-Za-z0-9_]*)+$", RegexOptions.Compiled);
        private static readonly Regex FunctionName = new Regex(@"^[A-Za-z][A-Za-z0-9_]*$", RegexOptions.Compiled);

        public static bool IsInvocable(string id) {
            return !string.IsNullOrWhiteSpace(id)
                && (Operations.ContainsKey(id) || PyRevitLibraryIndex.FindAutomation(id) is LibrarySymbol symbol && IsMarkedInvocable(symbol));
        }

        /// <summary>
        /// Whether run_automation can run this marked symbol, either hand-wired or from its marker.
        /// </summary>
        internal static bool IsInvocable(LibrarySymbol symbol) {
            return symbol?.Automation != null
                && (Operations.ContainsKey(symbol.Automation.Id) || IsMarkedInvocable(symbol));
        }

        /// <summary>
        /// A marked operation runs from its marker when it declares inputs on a module-level
        /// query or pure function of pyrevitlib or rpw that opens no transaction.
        /// </summary>
        internal static bool IsMarkedInvocable(LibrarySymbol symbol) {
            var automation = symbol?.Automation;
            return automation?.Inputs != null
                && symbol.Kind == "function"
                && symbol.Owner == null
                && (automation.Mode == "query" || automation.Mode == "pure")
                && automation.Transaction == "none"
                && ModuleName.IsMatch(symbol.Module ?? string.Empty)
                && FunctionName.IsMatch(symbol.Name ?? string.Empty);
        }

        /// <summary>
        /// Resolves a reviewed operation and validates its bounded input object.
        /// </summary>
        public static JObject Resolve(string id, JToken input) {
            if (string.IsNullOrWhiteSpace(id))
                throw new AgentClientException("invalid_params", "'id' is required.");
            Operation operation;
            if (!Operations.TryGetValue(id, out operation)) {
                var symbol = PyRevitLibraryIndex.FindAutomation(id);
                if (symbol != null && IsMarkedInvocable(symbol))
                    return ResolveMarked(symbol, input);
                if (symbol != null)
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

        private static JObject ResolveMarked(LibrarySymbol symbol, JToken input) {
            var automation = symbol.Automation;
            var inputs = AutomationInput.Validate(automation.Inputs, input);
            var title = automation.PlainEnglish.Trim().TrimEnd('.');
            if (title.Length > MaxTitleLength)
                title = title.Substring(0, MaxTitleLength - 3).TrimEnd() + "...";

            return new JObject {
                ["id"] = automation.Id,
                ["title"] = title,
                ["source"] = MarkedOperationSource,
                ["requires_document"] = automation.Context == "document",
                ["inputs"] = new JObject {
                    ["operation"] = new JObject {
                        ["id"] = automation.Id,
                        ["module"] = symbol.Module,
                        ["function"] = symbol.Name,
                    },
                    ["inputs"] = inputs,
                },
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
