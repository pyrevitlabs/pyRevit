using System;
using System.IO;

using pyRevitLabs.Json;
using pyRevitLabs.Json.Linq;
using pyRevitLabs.PyRevit;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    internal enum AgentRunMode {
        Query,
        DryRun,
        Modify,
    }

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
        public AgentRunMode Mode { get; private set; }
        public AgentEngine Engine { get; private set; }
        public string InputsJson { get; private set; }
        public string Workspace { get; private set; }

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
            return new AgentRunRequest {
                Script = script,
                Title = parameters.Value<string>("title") ?? "Agent run",
                Mode = ParseMode(parameters.Value<string>("mode")),
                Engine = ParseEngine(parameters.Value<string>("engine")),
                InputsJson = inputs == null || inputs.Type == JTokenType.Null
                    ? "{}"
                    : inputs.ToString(Formatting.None),
                Workspace = string.IsNullOrWhiteSpace(workspace) ? null : Path.GetFullPath(workspace),
            };
        }

        public JObject ToJson() {
            return new JObject {
                ["title"] = Title,
                ["mode"] = ModeName,
                ["engine"] = Engine == AgentEngine.CPython ? "cpython" : "ironpython",
                ["inputs"] = JToken.Parse(InputsJson),
                ["workspace"] = Workspace,
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
}
