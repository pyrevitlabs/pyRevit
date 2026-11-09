using System;
using System.Diagnostics;
using System.Linq;

using Autodesk.Revit.DB;

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
    /// Invariant: every request that needs the Revit main thread reads or changes the model, so
    /// <see cref="InvokeOnMainThread"/> is the session gate. It checks the session when the
    /// request arrives and again when Revit picks it up. Requests answered on the pipe thread
    /// (<c>ping</c>, <c>lookup_api</c> and the session requests) stay open without a session.
    /// The pipe can request and pause a session, and end one the user started, but never start
    /// or resume one, or add a document to it. While sessions start automatically, Revit starts
    /// one when it picks up a request.
    /// A model request names the document it works in with <c>document</c>, a key from
    /// <c>get_context</c>; without one it works in the active document. The key is resolved on
    /// the main thread, and the gate refuses a document the session isn't on.
    /// A model request's result carries <c>since_last_call</c> when the user changed the
    /// session's document, view or selection since the previous one; changes the request makes
    /// itself are never reported back to it. A <c>get_context</c> with <c>keep_changes</c>
    /// reports <c>since_last_call</c> without clearing it, for a client that checks the context
    /// before a request it makes on the agent's behalf.
    /// </remarks>
    internal static class AgentRequestHandler {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();
        private static readonly TimeSpan DefaultStartTimeout = TimeSpan.FromSeconds(30);
        private const double MaxStartTimeoutSeconds = 3600;

        public static string Handle(string line) {
            JToken id = null;
            string method = null;
            var loadAtStart = AgentHost.SessionLoad;
            try {
                var request = JObject.Parse(line);
                id = request["id"];
                method = request.Value<string>("method") ?? string.Empty;
                var parameters = request["params"] as JObject ?? new JObject();
                return Success(id, Dispatch(method, parameters, id));
            }
            catch (AgentException ex) {
                return Failure(id, -32000, ex.Message, ex.Code, ex.Details);
            }
            catch (JsonException ex) {
                return Failure(id, -32700, ex.Message, "parse_error");
            }
            catch (Exception ex) {
                logger.Error(ex, "Agent request failed");
                return Failure(id, -32603, ex.Message, "internal_error");
            }
            finally {
                if (method != null)
                    AgentHost.NoteRequest(method, loadAtStart);
            }
        }

        private static JToken Dispatch(string method, JObject parameters, JToken id) {
            AgentHost.RefreshConfigIfChanged();
            AgentHost.Activity.NoteClient((parameters["client"] as JValue)?.Value as string);
            if (method != "ping")
                RequireEnabled();
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
                    AgentSessions.PauseByClient();
                    return AgentSessions.Describe();
                case "end_session":
                    AgentSessions.EndByClient();
                    return AgentSessions.Describe();
                case "get_context":
                    var keepChanges = parameters.Value<bool?>("keep_changes") == true;
                    return InvokeCapturingDialogs(
                        (app, _, __) => AgentContext.Describe(app), parameters, "context", null, keepChanges);
                case "run":
                    var runRequest = AgentRunRequest.FromJson(parameters);
                    runRequest.RequestId = id?.ToString(Formatting.None).Trim('"');
                    return InvokeRunOnMainThread(runRequest, parameters);
                case "inspect_elements":
                    var ids = AgentInspector.ParseIds(parameters);
                    var includeParameters = parameters.Value<bool?>("parameters") ?? true;
                    return InvokeCapturingDialogs(
                        (app, target, _) => AgentInspector.Inspect(target, ids, includeParameters), parameters,
                        "inspect", AgentRequestText.Title(parameters));
                case "show":
                    var showRequest = AgentPresenter.Parse(parameters);
                    return InvokeCapturingDialogs(
                        (app, target, dialogs) => AgentPresenter.Show(app, target, showRequest, dialogs), parameters,
                        "show", AgentRequestText.Title(parameters) ?? showRequest.Action);
                case "capture":
                    var captureRequest = AgentCapture.Parse(parameters);
                    return InvokeCapturingDialogs(
                        (app, target, _) => AgentCapture.Capture(app, target, captureRequest), parameters,
                        "capture", AgentRequestText.Title(parameters),
                        describe: result => AgentLogDetails.FromCapture(result as JObject ?? new JObject(), AgentPaths.CapturesDir));
                case "lookup_api":
                    var query = parameters.Value<string>("name");
                    var lookup = AgentApiLookup.Lookup(query);
                    AgentHost.Activity.RecordLookup(
                        "lookup", query, AgentSessions.Tracker.CurrentSession,
                        (lookup as JObject)?.Value<bool?>("found") == false ? "not_found" : "ok", DateTime.UtcNow);
                    return lookup;
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
            Func<Autodesk.Revit.UI.UIApplication, Document, AgentDialogCapture, JToken> work, JObject parameters, string kind,
            string title, bool keepChanges = false, Func<JToken, JObject> describe = null) {
            return InvokeOnMainThread((app, target) => {
                using (var dialogs = new AgentDialogCapture(app)) {
                    var result = work(app, target, dialogs);
                    if (dialogs.Dialogs.Count > 0 && result is JObject response)
                        response["dialogs"] = dialogs.Dialogs;
                    return result;
                }
            }, parameters, kind, title, AgentRequestText.Reason(parameters), describe: describe, keepChanges: keepChanges);
        }

        /// <summary>
        /// Runs a <c>run</c> request on the main thread behind the session gate. A request the host
        /// refused before running any of it, such as <c>revit_busy</c>, is marked <c>not_run</c>
        /// and leaves a <c>not_run</c> record so the caller can confirm that later.
        /// </summary>
        private static JToken InvokeRunOnMainThread(AgentRunRequest request, JObject parameters) {
            try {
                return InvokeOnMainThread(
                    (app, target) => AgentRunService.Execute(app, target, request), parameters,
                    request.ModeName, request.Title, request.Reason, request.Mode,
                    result => AgentLogDetails.FromRun(result as JObject ?? new JObject(), request.Script),
                    () => {
                        AgentPermissions.CheckRun(request.Mode, AgentRunService.ReadPolicy());
                        AgentScripting.EnsureAvailable(request.Engine, AgentHost.RevitVersion);
                        RefuseNestedCPython(request);
                    });
            }
            catch (AgentException ex) when (ex.Details.Value<string>("outcome") == "not_run") {
                AgentRunService.RecordNotRun(request, ex);
                throw;
            }
        }

        /// <summary>
        /// Runs model work on the main thread behind the session gate, and records it in
        /// <see cref="AgentHost.Activity"/> for the agent panel, refusals included.
        /// </summary>
        /// <param name="work">
        /// The request's work, given the document it names; null only for a context read, which
        /// names none, or when the request names none and no document is active.
        /// </param>
        /// <param name="kind">What the panel calls the request; see <see cref="AgentRequestRecord.Kind"/>.</param>
        /// <param name="runMode">
        /// The mode of a <c>run</c> request, whose permission is checked again when Revit picks it
        /// up, because the policy may have changed while it was queued.
        /// </param>
        /// <param name="describe">Builds the log's summary of a successful result, for runs and captures.</param>
        /// <param name="refuseEarly">
        /// Checks that refuse the request before it waits for Revit, such as the policy; their
        /// refusals are logged like the session gate's. They run after the session gate, so an
        /// agent without a session is told to ask for one, not refused for a reason that
        /// would only send it back with the same request.
        /// </param>
        /// <param name="keepChanges">
        /// Reports <c>since_last_call</c> without clearing it, so the next request reports it too.
        /// </param>
        private static JToken InvokeOnMainThread(
            Func<Autodesk.Revit.UI.UIApplication, Document, JToken> work, JObject parameters, string kind, string title, string reason,
            AgentRunMode? runMode = null, Func<JToken, JObject> describe = null, Action refuseEarly = null,
            bool keepChanges = false) {
            var startTimeoutSeconds = parameters.Value<double?>("start_timeout_s");
            if (startTimeoutSeconds.HasValue
                && (double.IsNaN(startTimeoutSeconds.Value) || startTimeoutSeconds.Value <= 0 || startTimeoutSeconds.Value > MaxStartTimeoutSeconds))
                throw new AgentException("invalid_params",
                    $"'start_timeout_s' must be more than 0 and at most {MaxStartTimeoutSeconds}.");
            var documentKey = DocumentKey(parameters);
            var record = AgentHost.Activity.Arrive(kind, title, reason, AgentSessions.Tracker.CurrentSession, DateTime.UtcNow);
            var namesDocument = kind != "context";
            try {
                AgentSessions.CheckOnArrival();
                refuseEarly?.Invoke();
                JToken GatedWork(Autodesk.Revit.UI.UIApplication app) {
                    AgentHost.Activity.Start(record, DateTime.UtcNow);
                    var target = namesDocument ? ResolveDocument(app, documentKey) : null;
                    AgentSessions.CheckOnDequeue(app, target);
                    if (runMode.HasValue) {
                        AgentHost.RefreshConfigIfChanged();
                        AgentPermissions.CheckRun(runMode.Value, AgentRunService.ReadPolicy());
                    }
                    var sinceLastCall = AgentAwarenessWatch.SinceLastCall(app);
                    JToken done;
                    try {
                        using (AgentAwarenessWatch.Awareness.Suppress())
                            done = work(app, target);
                    }
                    catch {
                        AgentAwarenessWatch.Rebaseline(app);
                        throw;
                    }
                    if (!keepChanges)
                        AgentAwarenessWatch.Reset(app);
                    if (sinceLastCall != null && done is JObject response)
                        response["since_last_call"] = sinceLastCall;
                    return done;
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
                    result = dispatcher.Invoke(app => {
                        AgentHost.RefreshConfigIfChanged();
                        RequireEnabled();
                        return GatedWork(app);
                    }, startTimeout);
                }
                AgentHost.Activity.Finish(record, OutcomeOf(result), DateTime.UtcNow, Describe(describe, result));
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

        /// <exception cref="AgentException"><c>invalid_params</c> when <c>document</c> isn't a key.</exception>
        private static string DocumentKey(JObject parameters) {
            var token = parameters["document"];
            if (token == null || token.Type == JTokenType.Null)
                return null;
            if (token.Type != JTokenType.String || string.IsNullOrWhiteSpace(token.Value<string>()))
                throw new AgentException("invalid_params", "'document' must be a document key from get_context, such as 'doc-1'.");
            return token.Value<string>();
        }

        /// <summary>
        /// The document a request names by key, or the active document when it names none, as a
        /// request from the CLI may.
        /// </summary>
        /// <exception cref="AgentException"><c>unknown_document</c> when no open document has the key.</exception>
        private static Document ResolveDocument(Autodesk.Revit.UI.UIApplication app, string key) {
            if (key == null)
                return app.ActiveUIDocument?.Document;
            return AgentDocuments.Keys.Find(key) ?? throw UnknownDocument(app, key);
        }

        /// <summary>
        /// The refusal for a <c>document</c> that is no open document's key. When it is the title
        /// or path of exactly one open document, the message gives that document's key, so the
        /// caller can send the key instead; a title or path never selects a document itself.
        /// </summary>
        private static AgentException UnknownDocument(Autodesk.Revit.UI.UIApplication app, string key) {
            var open = AgentDocuments.Describe(app)
                .OfType<JObject>()
                .Where(document => document.Value<bool?>("linked") != true)
                .Select(document => (Key: document.Value<string>("key"), Title: document.Value<string>("title"), Path: document.Value<string>("path")));
            var named = AgentDocumentBinding.Named(key, open);
            return new AgentException("unknown_document", named.HasValue
                ? $"'{key}' isn't a document key; requests name documents by key. '{named.Value.Title}' has the key '{named.Value.Key}'."
                : $"No open document has the key '{key}': it was closed, or the key is wrong. "
                    + "Call get_context for the keys of the open documents.");
        }

        /// <remarks>
        /// The log's summary is a convenience; failing to build it must never fail the request.
        /// </remarks>
        private static JObject Describe(Func<JToken, JObject> describe, JToken result) {
            if (describe == null)
                return null;
            try {
                return describe(result);
            }
            catch (Exception ex) {
                logger.Debug("Could not summarize an agent request for the panel: {0}", ex.Message);
                return null;
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
