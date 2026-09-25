using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Pipes;
using System.Linq;
using System.Text;

using pyRevitLabs.Common;
using pyRevitLabs.Json;
using pyRevitLabs.Json.Linq;

namespace pyRevitCLI {
    /// <summary>
    /// A running Revit whose pyRevit agent host registered itself under
    /// <c>%APPDATA%\pyRevit\agent\instances</c>.
    /// </summary>
    internal sealed class AgentInstance {
        public int ProcessId { get; set; }
        public string Pipe { get; set; }
        public string RevitVersion { get; set; }
        public string RevitBuild { get; set; }
        public string Started { get; set; }

        public JObject ToJson() {
            return new JObject {
                ["pid"] = ProcessId,
                ["revit_version"] = RevitVersion,
                ["revit_build"] = RevitBuild,
                ["started"] = Started,
            };
        }
    }

    /// <summary>
    /// Error returned by an agent host, or raised while reaching one. <see cref="Code"/> is the
    /// host's stable error type (for example <c>revit_busy</c> or <c>no_active_document</c>).
    /// </summary>
    internal sealed class AgentClientException : Exception {
        public AgentClientException(string code, string message) : base(message) {
            Code = code;
        }

        public string Code { get; }
    }

    /// <summary>
    /// Client side of the agent host's pipe protocol (newline-delimited JSON-RPC 2.0), plus
    /// discovery of running hosts and of recorded runs.
    /// </summary>
    /// <remarks>
    /// Each call opens its own pipe connection. The host serves one connection at a time,
    /// so callers that may overlap (the MCP server) must serialize their calls.
    /// </remarks>
    internal static class PyRevitAgentClient {
        private static readonly Encoding Utf8 = new UTF8Encoding(false);
        private const int ConnectTimeoutMs = 10000;

        public static string AgentDir => Path.Combine(PyRevitLabsConsts.PyRevitPath, "agent");
        public static string InstancesDir => Path.Combine(AgentDir, "instances");
        public static string RunsDir => Path.Combine(AgentDir, "runs");

        /// <summary>
        /// Registered hosts whose Revit process is still alive, newest first. Registration
        /// files left behind by crashed Revit processes are skipped.
        /// </summary>
        public static List<AgentInstance> GetInstances() {
            var instances = new List<AgentInstance>();
            if (!Directory.Exists(InstancesDir))
                return instances;

            foreach (var file in Directory.GetFiles(InstancesDir, "*.json")) {
                try {
                    var data = JObject.Parse(File.ReadAllText(file));
                    var instance = new AgentInstance {
                        ProcessId = data.Value<int>("pid"),
                        Pipe = data.Value<string>("pipe"),
                        RevitVersion = data.Value<string>("revit_version"),
                        RevitBuild = data.Value<string>("revit_build"),
                        Started = data["started"]?.ToString(Formatting.None).Trim('"'),
                    };
                    if (IsAlive(instance.ProcessId))
                        instances.Add(instance);
                }
                catch (Exception) {
                }
            }

            return instances.OrderByDescending(instance => instance.Started).ToList();
        }

        /// <summary>
        /// Picks the target host. <paramref name="selector"/> is a Revit year (e.g. 2024) or a
        /// Revit process id. Without a selector, exactly one running host is required.
        /// </summary>
        /// <exception cref="AgentClientException">
        /// <c>no_revit</c> when nothing matches, <c>ambiguous_revit</c> when several hosts match.
        /// </exception>
        public static AgentInstance Resolve(string selector) {
            var instances = GetInstances();
            if (instances.Count == 0)
                throw new AgentClientException(
                    "no_revit",
                    "No running Revit with the pyRevit agent host was found. Start Revit with "
                    + "'[agent] enabled = true' (pyrevit configs agent enable).");

            var matches = instances;
            if (!string.IsNullOrWhiteSpace(selector)) {
                if (!int.TryParse(selector, out var number))
                    throw new AgentClientException("invalid_params", "Revit selector must be a year or a process id.");
                matches = instances
                    .Where(instance => number >= 2000 && number < 2100
                        ? instance.RevitVersion == selector
                        : instance.ProcessId == number)
                    .ToList();
                if (matches.Count == 0)
                    throw new AgentClientException("no_revit", "No running Revit matches '" + selector + "'.");
            }

            if (matches.Count > 1)
                throw new AgentClientException(
                    "ambiguous_revit",
                    "Several Revit sessions are running; pick one with a year or process id: "
                    + string.Join(", ", matches.Select(m => $"{m.RevitVersion} (pid {m.ProcessId})")));

            return matches[0];
        }

        /// <summary>
        /// Sends one request and waits for its response. There is no read timeout: a modify
        /// run legitimately waits for the user to answer the approval prompt in Revit.
        /// </summary>
        public static JToken Call(AgentInstance instance, string method, JObject parameters = null) {
            var request = new JObject {
                ["jsonrpc"] = "2.0",
                ["id"] = 1,
                ["method"] = method,
                ["params"] = parameters ?? new JObject(),
            };

            string responseLine;
            try {
                using (var pipe = new NamedPipeClientStream(".", instance.Pipe, PipeDirection.InOut)) {
                    pipe.Connect(ConnectTimeoutMs);
                    var writer = new StreamWriter(pipe, Utf8) { AutoFlush = true, NewLine = "\n" };
                    var reader = new StreamReader(pipe, Utf8);
                    writer.WriteLine(request.ToString(Formatting.None));
                    responseLine = reader.ReadLine();
                }
            }
            catch (TimeoutException) {
                throw new AgentClientException(
                    "revit_busy",
                    $"Could not connect to Revit {instance.RevitVersion} (pid {instance.ProcessId}); "
                    + "another client may be using it.");
            }
            catch (IOException ex) {
                throw new AgentClientException("pipe_error", "Connection to Revit failed: " + ex.Message);
            }

            if (responseLine == null)
                throw new AgentClientException("pipe_error", "Revit closed the connection without answering.");

            var response = JObject.Parse(responseLine);
            if (response["error"] is JObject error)
                throw new AgentClientException(
                    error["data"]?.Value<string>("type") ?? "error",
                    error.Value<string>("message"));
            return response["result"];
        }

        /// <summary>
        /// Finds a recorded run folder by its run id (the folder name ends with the id).
        /// </summary>
        public static string FindRunDir(string runId) {
            if (string.IsNullOrWhiteSpace(runId) || !Directory.Exists(RunsDir))
                return null;
            return Directory.GetDirectories(RunsDir, "*-" + runId.Trim()).FirstOrDefault();
        }

        public static List<string> GetRecentRunDirs(int limit) {
            if (!Directory.Exists(RunsDir))
                return new List<string>();
            return Directory.GetDirectories(RunsDir)
                .OrderByDescending(Path.GetFileName, StringComparer.Ordinal)
                .Take(limit)
                .ToList();
        }

        private static bool IsAlive(int processId) {
            try {
                using (var process = Process.GetProcessById(processId))
                    return !process.HasExited;
            }
            catch (Exception) {
                return false;
            }
        }
    }
}
