using System;
using System.Diagnostics;
using System.Linq;

using pyRevitLabs.Json;
using pyRevitLabs.Json.Linq;
using pyRevitLabs.NLog;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Maps JSON-RPC 2.0 request lines from the pipe to agent operations.
    /// </summary>
    /// <remarks>
    /// Runs on the pipe thread. Anything that touches the Revit API must go through
    /// <see cref="AgentDispatcher.Invoke"/>, except a request made in-process through
    /// <see cref="AgentHost.HandleRequest"/>, which already runs on the Revit main thread and
    /// executes the work directly. Errors reach the client as JSON-RPC errors whose
    /// <c>data.type</c> carries the <see cref="AgentException.Code"/> and whose other <c>data</c>
    /// fields come from <see cref="AgentException.Details"/> (for example <c>outcome</c>).
    /// Only a line that is not JSON is a <c>parse_error</c>; a parameter of the wrong JSON type is
    /// <c>invalid_params</c>, and any other failure is an <c>internal_error</c> with <c>outcome</c>
    /// <c>unknown</c>, since the work may already have run.
    /// </remarks>
    internal static class AgentRequestHandler {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();
        private static readonly TimeSpan DefaultStartTimeout = TimeSpan.FromSeconds(30);
        private const double MaxStartTimeoutSeconds = 3600;

        public static string Handle(string line) {
            JToken id = null;
            string method = null;
            var loadAtStart = AgentHost.SessionLoad;
            JObject request;
            try {
                request = AgentRequestLine.Parse(line);
            }
            catch (JsonException ex) {
                return Failure(null, -32700, ex.Message, "parse_error");
            }

            try {
                id = request["id"];
                method = (request["method"] as JValue)?.Value as string ?? string.Empty;
                var parameters = request["params"] as JObject ?? new JObject();
                return Success(id, Dispatch(method, parameters, id));
            }
            catch (AgentException ex) {
                return Failure(id, -32000, ex.Message, ex.Code, ex.Details);
            }
            catch (Exception ex) {
                logger.Error(ex, "Agent request failed");
                return Failure(id, -32603, "The agent request failed inside Revit; the pyRevit log has the details.",
                    "internal_error", new JObject { ["outcome"] = "unknown" });
            }
            finally {
                if (method != null)
                    AgentHost.NoteRequest(method, loadAtStart);
            }
        }

        private static JToken Dispatch(string method, JObject parameters, JToken id) {
            AgentHost.RefreshConfigIfChanged();
            if (method != "ping")
                RequireEnabled();
            switch (method) {
                case "ping":
                    return new JObject {
                        ["pong"] = true,
                        ["pid"] = Process.GetCurrentProcess().Id,
                        ["pipe"] = AgentHost.PipeName,
                        ["revit_version"] = AgentHost.RevitVersion,
                    };
                case "get_context":
                    return InvokeCapturingDialogs((app, _) => AgentContext.Describe(app), parameters);
                case "run":
                    var runRequest = ParseParameters(() => AgentRunRequest.FromJson(parameters));
                    AgentScripting.EnsureAvailable(runRequest.Engine, AgentHost.RevitVersion);
                    RefuseNestedCPython(runRequest);
                    runRequest.RequestId = RequestIdOf(id);
                    return InvokeRunOnMainThread(runRequest, parameters);
                case "inspect_elements":
                    var ids = ParseParameters(() => AgentInspector.ParseIds(parameters));
                    var includeParameters = AgentParams.Get<bool?>(parameters, "parameters") ?? true;
                    return InvokeCapturingDialogs((app, _) => AgentInspector.Inspect(app, ids, includeParameters), parameters);
                case "show":
                    var showRequest = ParseParameters(() => AgentPresenter.Parse(parameters));
                    return InvokeCapturingDialogs((app, dialogs) => AgentPresenter.Show(app, showRequest, dialogs), parameters);
                case "capture":
                    var captureRequest = ParseParameters(() => AgentCapture.Parse(parameters));
                    return InvokeCapturingDialogs((app, _) => AgentCapture.Capture(app, captureRequest), parameters);
                case "lookup_api":
                    var query = AgentParams.Get<string>(parameters, "name");
                    return AgentApiLookup.Lookup(query);
                default:
                    throw new AgentException("method_not_found", "Unknown method: " + method);
            }
        }

        /// <summary>
        /// Runs a request's parameter parsing, turning a value of the wrong JSON type that
        /// <see cref="AgentParams"/> didn't catch, such as an array item, into <c>invalid_params</c>.
        /// </summary>
        /// <remarks>
        /// Only for parsing that happens before any work starts: once the request has run, these
        /// conversion errors no longer mean the parameters were wrong.
        /// </remarks>
        private static T ParseParameters<T>(Func<T> parse) {
            try {
                return parse();
            }
            catch (Exception ex) when (ex is FormatException || ex is InvalidCastException || ex is OverflowException) {
                throw new AgentException("invalid_params", "A parameter has the wrong JSON type or is out of range.");
            }
        }

        /// <summary>
        /// The client's JSON-RPC id as the text it sent: a string id unescaped, a number as written.
        /// </summary>
        internal static string RequestIdOf(JToken id) {
            if (id == null || id.Type == JTokenType.Null)
                return null;
            return id.Type == JTokenType.String ? id.Value<string>() : id.ToString(Formatting.None);
        }

        /// <summary>
        /// Refuses a CPython run requested in-process while a CPython script is already executing.
        /// </summary>
        /// <remarks>
        /// CPython has one interpreter per process, so the agent run would execute nested inside the
        /// caller's script on the same thread, and that crashed Revit outright. A pipe request never
        /// nests, since it runs from Revit's idle callback.
        /// </remarks>
        private static void RefuseNestedCPython(AgentRunRequest request) {
            if (request.Engine != AgentEngine.CPython || AgentHost.InlineApplication == null)
                return;
            var cpythonRunning = ScriptEngineManager.ActiveEngineDict
                .Any(entry => entry.Value > 0 && entry.Key.Split(':').ElementAtOrDefault(1) == ScriptEngineType.CPython.ToString());
            if (cpythonRunning)
                throw new AgentException(
                    "nested_cpython",
                    "A CPython agent run can't start from inside a CPython script. Use engine 'ironpython', or call from an IronPython command.");
        }

        /// <summary>
        /// Refuses work once <c>[agent] enabled</c> is off, so disabling the agent from outside
        /// Revit stops it at the next request instead of the next pyRevit reload.
        /// </summary>
        /// <remarks>
        /// Checked again on the main thread just before the work starts, so a request queued
        /// before the agent was disabled never runs.
        /// </remarks>
        private static void RequireEnabled() {
            if (AgentHost.IsEnabled())
                return;
            var disabled = new AgentException("agent_disabled",
                "The pyRevit agent is disabled in the pyRevit settings, so the request was not run.");
            disabled.Details["outcome"] = "not_run";
            throw disabled;
        }

        /// <summary>
        /// Runs a fixed, non-script request on the main thread with Revit dialogs closed and
        /// reported, so a dialog Revit opens mid-request can't hang the call.
        /// </summary>
        /// <remarks>
        /// Dismissed dialogs are added to an object result as <c>dialogs</c>. <c>run</c> doesn't
        /// use this: its guard captures dialogs itself.
        /// </remarks>
        private static JToken InvokeCapturingDialogs(
            Func<Autodesk.Revit.UI.UIApplication, AgentDialogCapture, JToken> work, JObject parameters) {
            return InvokeOnMainThread(app => {
                using (var dialogs = new AgentDialogCapture(app)) {
                    var result = work(app, dialogs);
                    if (dialogs.Dialogs.Count > 0 && result is JObject response)
                        response["dialogs"] = dialogs.Dialogs;
                    return result;
                }
            }, parameters);
        }

        /// <summary>
        /// Runs a <c>run</c> request on the main thread. A request refused as <c>revit_busy</c>
        /// or <c>document_changed</c> never ran, and leaves a <c>not_run</c> record so the caller
        /// can confirm that later.
        /// </summary>
        private static JToken InvokeRunOnMainThread(AgentRunRequest request, JObject parameters) {
            try {
                return InvokeOnMainThread(app => AgentRunService.Execute(app, request), parameters);
            }
            catch (AgentException ex) when (ex.Details.Value<string>("outcome") == "not_run") {
                AgentRunService.RecordNotRun(request, ex);
                throw;
            }
        }

        private static JToken InvokeOnMainThread(
            Func<Autodesk.Revit.UI.UIApplication, JToken> work, JObject parameters) {
            var startTimeoutSeconds = AgentParams.Get<double?>(parameters, "start_timeout_s");
            if (startTimeoutSeconds.HasValue
                && (double.IsNaN(startTimeoutSeconds.Value) || startTimeoutSeconds.Value <= 0 || startTimeoutSeconds.Value > MaxStartTimeoutSeconds))
                throw new AgentException("invalid_params",
                    $"'start_timeout_s' must be more than 0 and at most {MaxStartTimeoutSeconds}.");
            var inline = AgentHost.InlineApplication;
            if (inline != null)
                return work(inline);
            var dispatcher = AgentHost.Dispatcher
                ?? throw new AgentException("host_not_ready", "The agent host is not started.");
            var startTimeout = startTimeoutSeconds.HasValue
                ? TimeSpan.FromSeconds(startTimeoutSeconds.Value)
                : DefaultStartTimeout;
            return dispatcher.Invoke(app => {
                AgentHost.RefreshConfigIfChanged();
                RequireEnabled();
                return work(app);
            }, startTimeout);
        }

        private static string Success(JToken id, JToken result) {
            return new JObject {
                ["jsonrpc"] = "2.0",
                ["id"] = id,
                ["result"] = result,
            }.ToString(Formatting.None);
        }

        private static string Failure(JToken id, int code, string message, string type, JObject details = null) {
            var data = new JObject { ["type"] = type };
            if (details != null)
                foreach (var property in details.Properties())
                    data[property.Name] = property.Value;
            return new JObject {
                ["jsonrpc"] = "2.0",
                ["id"] = id,
                ["error"] = new JObject {
                    ["code"] = code,
                    ["message"] = message,
                    ["data"] = data,
                },
            }.ToString(Formatting.None);
        }
    }
}
