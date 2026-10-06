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
    /// <c>data.type</c> carries the <see cref="AgentException.Code"/>.
    /// Invariant: every request that needs the Revit main thread reads or changes the model, so
    /// <see cref="InvokeOnMainThread"/> is the session gate. It checks the session when the
    /// request arrives and again when Revit picks it up. Requests answered on the pipe thread
    /// (<c>ping</c>, <c>lookup_api</c> and the session requests) stay open without a session.
    /// The pipe can request, pause and end a session but never start or resume one.
    /// </remarks>
    internal static class AgentRequestHandler {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();
        private static readonly TimeSpan DefaultStartTimeout = TimeSpan.FromSeconds(30);
        private const double MaxStartTimeoutSeconds = 3600;

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
            AgentHost.Activity.NoteClient((parameters["client"] as JValue)?.Value as string);
            switch (method) {
                case "ping":
                    return new JObject {
                        ["pong"] = true,
                        ["pid"] = Process.GetCurrentProcess().Id,
                        ["pipe"] = AgentHost.PipeName,
                        ["revit_version"] = AgentHost.RevitVersion,
                        ["session"] = AgentSessions.Describe(),
                    };
                case "session_status":
                    return AgentSessions.Describe();
                case "request_session":
                    var requested = AgentSessions.Tracker.Request(parameters.Value<string>("reason"), DateTime.UtcNow);
                    if (requested && AgentHost.InlineApplication == null)
                        AgentPanel.RevealForRequest();
                    return new JObject {
                        ["requested"] = requested,
                        ["session"] = AgentSessions.Describe(),
                    };
                case "pause_session":
                    AgentSessions.Pause();
                    return AgentSessions.Describe();
                case "end_session":
                    AgentSessions.EndByClient();
                    return AgentSessions.Describe();
                case "get_context":
                    return InvokeCapturingDialogs((app, _) => AgentContext.Describe(app), parameters, "context", null);
                case "run":
                    var runRequest = AgentRunRequest.FromJson(parameters);
                    AgentPermissions.CheckRun(runRequest.Mode, AgentRunService.ReadPolicy());
                    AgentScripting.EnsureAvailable(runRequest.Engine, AgentHost.RevitVersion);
                    RefuseNestedCPython(runRequest);
                    return InvokeOnMainThread(
                        app => AgentRunService.Execute(app, runRequest), parameters, runRequest.ModeName, runRequest.Title, runRequest.Mode);
                case "inspect_elements":
                    var ids = AgentInspector.ParseIds(parameters);
                    var includeParameters = parameters.Value<bool?>("parameters") ?? true;
                    return InvokeCapturingDialogs(
                        (app, _) => AgentInspector.Inspect(app, ids, includeParameters), parameters, "inspect", null);
                case "show":
                    var showRequest = AgentPresenter.Parse(parameters);
                    return InvokeCapturingDialogs(
                        (app, dialogs) => AgentPresenter.Show(app, showRequest, dialogs), parameters, "show", showRequest.Action);
                case "capture":
                    var captureRequest = AgentCapture.Parse(parameters);
                    return InvokeCapturingDialogs((app, _) => AgentCapture.Capture(app, captureRequest), parameters, "capture", null);
                case "lookup_api":
                    var query = parameters.Value<string>("name");
                    return AgentApiLookup.Lookup(query);
                default:
                    throw new AgentException("method_not_found", "Unknown method: " + method);
            }
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
        /// Runs a fixed, non-script request on the main thread with Revit dialogs closed and
        /// reported, so a dialog Revit opens mid-request can't hang the call.
        /// </summary>
        /// <remarks>
        /// Dismissed dialogs are added to an object result as <c>dialogs</c>. <c>run</c> doesn't
        /// use this: its guard captures dialogs itself and must disarm for the approval prompt.
        /// </remarks>
        private static JToken InvokeCapturingDialogs(
            Func<Autodesk.Revit.UI.UIApplication, AgentDialogCapture, JToken> work, JObject parameters, string kind, string title) {
            return InvokeOnMainThread(app => {
                using (var dialogs = new AgentDialogCapture(app)) {
                    var result = work(app, dialogs);
                    if (dialogs.Dialogs.Count > 0 && result is JObject response)
                        response["dialogs"] = dialogs.Dialogs;
                    return result;
                }
            }, parameters, kind, title);
        }

        /// <summary>
        /// Runs model work on the main thread behind the session gate, and records it in
        /// <see cref="AgentHost.Activity"/> for the agent panel, refusals included.
        /// </summary>
        /// <param name="kind">What the panel calls the request; see <see cref="AgentRequestRecord.Kind"/>.</param>
        /// <param name="runMode">
        /// The mode of a <c>run</c> request, whose permission is checked again when Revit picks it
        /// up, because the policy may have changed while it was queued.
        /// </param>
        private static JToken InvokeOnMainThread(
            Func<Autodesk.Revit.UI.UIApplication, JToken> work, JObject parameters, string kind, string title,
            AgentRunMode? runMode = null) {
            var startTimeoutSeconds = parameters.Value<double?>("start_timeout_s");
            if (startTimeoutSeconds.HasValue
                && (double.IsNaN(startTimeoutSeconds.Value) || startTimeoutSeconds.Value <= 0 || startTimeoutSeconds.Value > MaxStartTimeoutSeconds))
                throw new AgentException("invalid_params",
                    $"'start_timeout_s' must be more than 0 and at most {MaxStartTimeoutSeconds}.");
            var record = AgentHost.Activity.Arrive(kind, title, DateTime.UtcNow);
            try {
                AgentSessions.CheckOnArrival();
                JToken GatedWork(Autodesk.Revit.UI.UIApplication app) {
                    AgentHost.Activity.Start(record);
                    AgentSessions.CheckOnDequeue(app);
                    if (runMode.HasValue) {
                        AgentHost.RefreshConfigIfChanged();
                        AgentPermissions.CheckRun(runMode.Value, AgentRunService.ReadPolicy());
                    }
                    return work(app);
                }
                JToken result;
                var inline = AgentHost.InlineApplication;
                if (inline != null)
                    result = GatedWork(inline);
                else {
                    var dispatcher = AgentHost.Dispatcher
                        ?? throw new AgentException("host_not_ready", "The agent host is not started.");
                    var startTimeout = startTimeoutSeconds.HasValue
                        ? TimeSpan.FromSeconds(startTimeoutSeconds.Value)
                        : DefaultStartTimeout;
                    result = dispatcher.Invoke(GatedWork, startTimeout);
                }
                AgentHost.Activity.Finish(record, OutcomeOf(result), DateTime.UtcNow);
                return result;
            }
            catch (AgentException ex) {
                AgentHost.Activity.Finish(record, ex.Code, DateTime.UtcNow);
                throw;
            }
            catch (Exception) {
                AgentHost.Activity.Finish(record, "internal_error", DateTime.UtcNow);
                throw;
            }
        }

        /// <summary>
        /// How a request ended, as the agent panel shows it: <c>ok</c>, <c>committed</c>,
        /// <c>rejected</c>, or the error type of a run that failed.
        /// </summary>
        private static string OutcomeOf(JToken result) {
            if (!(result is JObject response) || response["decision"] == null)
                return "ok";
            switch (response.Value<string>("status")) {
                case "error":
                    return (response["error"] as JObject)?.Value<string>("type") ?? "error";
                case "rejected":
                    return "rejected";
                default:
                    return response.Value<string>("decision") == "committed" ? "committed" : "ok";
            }
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
