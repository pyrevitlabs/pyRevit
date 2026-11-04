using System;
using System.IO;
using System.Text.RegularExpressions;

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
        private static readonly Regex TitleBreaks = new Regex(@"[\p{Cc}\p{Cf}\p{Zl}\p{Zp}]+");

        public string Script { get; private set; }

        /// <summary>
        /// The agent's one-line name for the run, shown in the approval prompt.
        /// </summary>
        /// <remarks>
        /// Invariant: holds no line breaks or other control and format characters, so a title
        /// can't fake the change counts printed below it in the prompt.
        /// </remarks>
        public string Title { get; private set; }
        public AgentRunMode Mode { get; private set; }
        public AgentEngine Engine { get; private set; }
        public string InputsJson { get; private set; }
        public string Workspace { get; private set; }

        /// <summary>
        /// The JSON-RPC <c>id</c> the client sent, kept in the run record so a caller that lost
        /// the answer can find what became of its request. Set by the request handler.
        /// </summary>
        public string RequestId { get; set; }

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
            if (!string.IsNullOrWhiteSpace(workspace) && (!Path.IsPathRooted(workspace) || IsNetworkOrDevicePath(workspace) || !Directory.Exists(workspace)))
                throw new AgentException("invalid_params", "'workspace' must be the absolute path of an existing local folder.");
            var timeoutSeconds = parameters.Value<double?>("timeout_s") ?? DefaultTimeoutSeconds;
            if (double.IsNaN(timeoutSeconds) || timeoutSeconds <= 0 || timeoutSeconds > MaxTimeoutSeconds)
                throw new AgentException("invalid_params", $"'timeout_s' must be more than 0 and at most {MaxTimeoutSeconds}.");
            return new AgentRunRequest {
                Script = script,
                Title = TitleBreaks.Replace(parameters.Value<string>("title") ?? "Agent run", " ").Trim(),
                Mode = ParseMode(parameters.Value<string>("mode")),
                Engine = ParseEngine(parameters.Value<string>("engine")),
                InputsJson = inputs == null || inputs.Type == JTokenType.Null
                    ? "{}"
                    : inputs.ToString(Formatting.None),
                Workspace = string.IsNullOrWhiteSpace(workspace) ? null : Path.GetFullPath(workspace),
                TimeoutSeconds = timeoutSeconds,
            };
        }

        /// <remarks>
        /// Checked before the folder is touched: looking up a UNC path connects to that host
        /// and sends it the user's Windows credentials.
        /// </remarks>
        private static bool IsNetworkOrDevicePath(string path) {
            return path.Length >= 2 && IsSeparator(path[0]) && IsSeparator(path[1]);
        }

        private static bool IsSeparator(char character) {
            return character == Path.DirectorySeparatorChar || character == Path.AltDirectorySeparatorChar;
        }

        public JObject ToJson() {
            return new JObject {
                ["title"] = Title,
                ["mode"] = ModeName,
                ["engine"] = Engine == AgentEngine.CPython ? "cpython" : "ironpython",
                ["inputs"] = JToken.Parse(InputsJson),
                ["workspace"] = Workspace,
                ["timeout_s"] = TimeoutSeconds,
                ["request_id"] = RequestId,
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
