using System;
using System.IO;

using pyRevitLabs.Json;
using pyRevitLabs.Json.Linq;
using pyRevitLabs.PyRevit;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    internal enum AgentEngine {
        IronPython,
        CPython,
    }

    /// <summary>
    /// A validated <c>run</c> request. Parsing happens on the pipe thread, so a malformed
    /// request never occupies the Revit main thread.
    /// </summary>
    internal sealed class AgentRunRequest {
        public string Script { get; private set; }
        public string Title { get; private set; }
        public string Reason { get; private set; }
        public AgentRunMode Mode { get; private set; }
        public AgentEngine Engine { get; private set; }
        public string InputsJson { get; private set; }
        public string Workspace { get; private set; }

        /// <summary>
        /// Seconds the script may run before the runner stops it. Covers script execution
        /// only, not waiting to start or the approval prompt.
        /// </summary>
        public double TimeoutSeconds { get; private set; }

        public const double DefaultTimeoutSeconds = 300;
        public const double MaxTimeoutSeconds = 3600;

        public string ModeName {
            get {
                switch (Mode) {
                    case AgentRunMode.DryRun: return "dry_run";
                    case AgentRunMode.Modify: return "modify";
                    default: return "query";
                }
            }
        }

        public static AgentRunRequest FromJson(JObject parameters) {
            var script = parameters.Value<string>("script");
            if (string.IsNullOrWhiteSpace(script))
                throw new AgentException("invalid_params", "'script' is required.");

            var inputs = parameters["inputs"];
            var workspace = parameters.Value<string>("workspace");
            if (!string.IsNullOrWhiteSpace(workspace) && (!Path.IsPathRooted(workspace) || !Directory.Exists(workspace)))
                throw new AgentException("invalid_params", "'workspace' must be the absolute path of an existing folder.");
            var timeoutSeconds = parameters.Value<double?>("timeout_s") ?? DefaultTimeoutSeconds;
            if (double.IsNaN(timeoutSeconds) || timeoutSeconds <= 0 || timeoutSeconds > MaxTimeoutSeconds)
                throw new AgentException("invalid_params", $"'timeout_s' must be more than 0 and at most {MaxTimeoutSeconds}.");
            return new AgentRunRequest {
                Script = script,
                Title = AgentRequestText.Title(parameters) ?? "Agent run",
                Reason = AgentRequestText.Reason(parameters),
                Mode = ParseMode(parameters.Value<string>("mode")),
                Engine = ParseEngine(parameters.Value<string>("engine")),
                InputsJson = inputs == null || inputs.Type == JTokenType.Null
                    ? "{}"
                    : inputs.ToString(Formatting.None),
                Workspace = string.IsNullOrWhiteSpace(workspace) ? null : Path.GetFullPath(workspace),
                TimeoutSeconds = timeoutSeconds,
            };
        }

        public JObject ToJson() {
            return new JObject {
                ["title"] = Title,
                ["reason"] = Reason,
                ["mode"] = ModeName,
                ["engine"] = Engine == AgentEngine.CPython ? "cpython" : "ironpython",
                ["inputs"] = JToken.Parse(InputsJson),
                ["workspace"] = Workspace,
                ["timeout_s"] = TimeoutSeconds,
            };
        }

        private static AgentRunMode ParseMode(string mode) {
            switch ((mode ?? "query").ToLowerInvariant()) {
                case "query": return AgentRunMode.Query;
                case "dry_run": return AgentRunMode.DryRun;
                case "modify": return AgentRunMode.Modify;
                default:
                    throw new AgentException("invalid_params", "'mode' must be query, dry_run or modify.");
            }
        }

        private static AgentEngine ParseEngine(string engine) {
            switch ((engine ?? PyRevitConfigs.GetAgentEngine()).ToLowerInvariant()) {
                case "ironpython": return AgentEngine.IronPython;
                case "cpython": return AgentEngine.CPython;
                default:
                    throw new AgentException("invalid_params", "'engine' must be ironpython or cpython.");
            }
        }
    }

    /// <summary>
    /// Reads the agent's own words about a request, its <c>title</c> and <c>reason</c>, for the
    /// agent log and the run record.
    /// </summary>
    /// <remarks>
    /// The MCP server refuses a missing or overlong title. The host only trims and cuts,
    /// because the CLI and in-Revit callers send what they have.
    /// </remarks>
    internal static class AgentRequestText {
        public const int MaxTitleLength = 120;
        public const int MaxReasonLength = 300;

        public static string Title(JObject parameters) {
            return Read(parameters, "title", MaxTitleLength);
        }

        public static string Reason(JObject parameters) {
            return Read(parameters, "reason", MaxReasonLength);
        }

        private static string Read(JObject parameters, string name, int maxLength) {
            var text = ((parameters[name] as JValue)?.Value as string)?.Trim();
            if (string.IsNullOrEmpty(text))
                return null;
            return text.Length <= maxLength ? text : text.Substring(0, maxLength);
        }
    }
}
