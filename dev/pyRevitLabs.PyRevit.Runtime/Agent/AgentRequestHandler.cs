using System;
using System.Diagnostics;

using pyRevitLabs.Json;
using pyRevitLabs.Json.Linq;
using pyRevitLabs.NLog;
using pyRevitLabs.PyRevit;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Maps JSON-RPC 2.0 request lines from the pipe to agent operations.
    /// </summary>
    /// <remarks>
    /// Runs on the pipe thread. Anything that touches the Revit API must go through
    /// <see cref="AgentDispatcher.Invoke"/>. Errors reach the client as JSON-RPC errors whose
    /// <c>data.type</c> carries the <see cref="AgentException.Code"/>.
    /// </remarks>
    internal static class AgentRequestHandler {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();
        private static readonly TimeSpan DefaultStartTimeout = TimeSpan.FromSeconds(30);

        public static string Handle(string line) {
            JToken id = null;
            try {
                var request = JObject.Parse(line);
                id = request["id"];
                var method = request.Value<string>("method") ?? string.Empty;
                var parameters = request["params"] as JObject ?? new JObject();
                return Success(id, Dispatch(method, parameters));
            }
            catch (AgentException ex) {
                return Failure(id, -32000, ex.Message, ex.Code);
            }
            catch (JsonException ex) {
                return Failure(id, -32700, ex.Message, "parse_error");
            }
            catch (Exception ex) {
                logger.Error(ex, "Agent request failed");
                return Failure(id, -32603, ex.Message, "internal_error");
            }
        }

        private static JToken Dispatch(string method, JObject parameters) {
            AgentHost.RefreshConfigIfChanged();
            switch (method) {
                case "ping":
                    return new JObject {
                        ["pong"] = true,
                        ["pid"] = Process.GetCurrentProcess().Id,
                        ["pipe"] = AgentHost.PipeName,
                        ["revit_version"] = AgentHost.RevitVersion,
                    };
                case "get_context":
                    return InvokeOnMainThread(AgentContext.Describe, parameters);
                case "run":
                    var runRequest = AgentRunRequest.FromJson(parameters);
                    EnforcePolicy(runRequest);
                    return InvokeOnMainThread(app => AgentRunService.Execute(app, runRequest), parameters);
                case "inspect_elements":
                    var ids = AgentInspector.ParseIds(parameters);
                    var includeParameters = parameters.Value<bool?>("parameters") ?? true;
                    return InvokeOnMainThread(app => AgentInspector.Inspect(app, ids, includeParameters), parameters);
                case "show":
                    var showRequest = AgentPresenter.Parse(parameters);
                    return InvokeOnMainThread(app => AgentPresenter.Show(app, showRequest), parameters);
                case "lookup_api":
                    var query = parameters.Value<string>("name");
                    return AgentApiLookup.Lookup(query);
                default:
                    throw new AgentException("method_not_found", "Unknown method: " + method);
            }
        }

        private static void EnforcePolicy(AgentRunRequest request) {
            if (request.Mode == AgentRunMode.Modify
                && PyRevitConfigs.GetAgentPolicy() == PyRevitConsts.ConfigsAgentPolicyReadOnly)
                throw new AgentException(
                    "policy_readonly",
                    "The pyRevit agent policy is 'readonly': modify runs are disabled. Use query or dry_run.");
        }

        private static JToken InvokeOnMainThread(
            Func<Autodesk.Revit.UI.UIApplication, JToken> work, JObject parameters) {
            var dispatcher = AgentHost.Dispatcher
                ?? throw new AgentException("host_not_ready", "The agent host is not started.");
            var startTimeoutSeconds = parameters.Value<double?>("start_timeout_s");
            var startTimeout = startTimeoutSeconds.HasValue
                ? TimeSpan.FromSeconds(startTimeoutSeconds.Value)
                : DefaultStartTimeout;
            return dispatcher.Invoke(work, startTimeout);
        }

        private static string Success(JToken id, JToken result) {
            return new JObject {
                ["jsonrpc"] = "2.0",
                ["id"] = id,
                ["result"] = result,
            }.ToString(Formatting.None);
        }

        private static string Failure(JToken id, int code, string message, string type) {
            return new JObject {
                ["jsonrpc"] = "2.0",
                ["id"] = id,
                ["error"] = new JObject {
                    ["code"] = code,
                    ["message"] = message,
                    ["data"] = new JObject { ["type"] = type },
                },
            }.ToString(Formatting.None);
        }
    }
}
