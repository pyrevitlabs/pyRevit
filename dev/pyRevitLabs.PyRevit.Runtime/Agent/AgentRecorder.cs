using System;

using Autodesk.Revit.UI;

using pyRevitLabs.Json.Linq;
using pyRevitLabs.NLog;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// The explicit record/stop recorder. It is off until a recording starts and records only
    /// between <see cref="Start"/> and <see cref="Stop"/>.
    /// </summary>
    /// <remarks>
    /// Every hook (<see cref="Mark"/>, command, output and log records) is a no-op while no
    /// recording is active, so the idle cost is one volatile read. Recordings are plaintext and
    /// stay in <c>%APPDATA%\pyRevit\agent\recordings</c>; nothing leaves the machine unless the
    /// user shares the folder, or an agent reads it through <c>get_recording</c>.
    /// Only code running inside Revit starts a recording, unless <c>[agent] recording_start</c>
    /// is <c>auto</c>. A start the CLI or an agent asks for over the pipe leaves a request in
    /// <see cref="Consent"/>, which the user takes or declines in the agent panel. This guards
    /// against well-behaved agents recording unseen, not against a hostile script: any code
    /// inside Revit can call <see cref="StartInRevit"/> too, except while an agent run executes.
    /// Stopping and reading the state stay open to the pipe.
    /// Invariant: at most one recording is active per Revit process.
    /// Important: <see cref="Start"/> must run in a valid Revit API context because it subscribes
    /// to Revit events. A stop requested off the Revit main thread ends the recording but leaves
    /// unsubscribing to the watch's next <c>Idling</c>, so shutdown never touches Revit events
    /// from the wrong thread.
    /// </remarks>
    public static class AgentRecorder {
        public const string StartUser = "user";
        public const string StartAuto = "auto";

        internal static readonly AgentRecordingConsent Consent =
            new AgentRecordingConsent(() => AgentSessions.Tracker.IsRunExecuting);

        private static readonly Logger logger = LogManager.GetCurrentClassLogger();
        private static readonly object sync = new object();
        private const int MinimumLoggedLevel = (int)ScriptLogLevel.Info;
        private static volatile AgentRecordingStore store;
        private static AgentRecordingWatch watch;

        [ThreadStatic]
        private static bool appending;

        [ThreadStatic]
        private static bool outputSuppressed;

        private static readonly AgentOutputBuffer pendingOutput = new AgentOutputBuffer();

        private sealed class OutputSuppression : IDisposable {
            private readonly bool previous = outputSuppressed;

            public OutputSuppression() {
                outputSuppressed = true;
            }

            public void Dispose() {
                outputSuppressed = previous;
            }
        }

        /// <summary>
        /// Raised after a recording starts or stops, on the thread that started or stopped it.
        /// </summary>
        /// <remarks>
        /// Important: a handler can't assume the Revit main thread and must queue any UI work.
        /// </remarks>
        internal static event Action StateChanged;

        internal static IDisposable SuppressOutput() => new OutputSuppression();

        public static bool IsRecording => store != null;

        /// <summary>
        /// Whether a start the CLI or an agent asks for begins recording at once. Set from
        /// <c>[agent] recording_start</c> each time pyRevit loads, so editing the config while
        /// Revit runs changes nothing until then.
        /// </summary>
        public static bool StartsAutomatically => Consent.StartMode == AgentRecordingStart.Auto;

        /// <summary>
        /// Sets how recordings start, <see cref="StartUser"/> or <see cref="StartAuto"/>, until
        /// pyRevit loads again.
        /// </summary>
        /// <exception cref="ArgumentException">Any other value.</exception>
        /// <exception cref="AgentException">
        /// <c>recording_locked</c> when making recordings start automatically while an agent run
        /// executes.
        /// </exception>
        public static void SetRecordingStart(string mode) {
            Consent.SetStartMode(ParseStart(mode));
        }

        /// <summary>
        /// Starts a recording for the user, from the agent panel or other code in Revit, with the
        /// limits of the pending request when there is one and the default limits otherwise.
        /// </summary>
        /// <returns>The new recording's id.</returns>
        /// <exception cref="InvalidOperationException">Called off the Revit main thread.</exception>
        /// <exception cref="AgentException">
        /// <c>recording_active</c> when a recording is already active, or <c>recording_locked</c>
        /// while an agent run executes.
        /// </exception>
        public static string StartInRevit(UIApplication app) {
            if (app == null)
                throw new ArgumentNullException(nameof(app));
            if (!ScriptExecutor.IsOnMainThread)
                throw new InvalidOperationException("Recordings must be started on the Revit main thread.");
            Consent.RefuseWhileRunExecutes("A recording can't be started from inside an agent run.");
            var options = Consent.PendingOptions ?? new AgentRecordingOptions();
            return Start(app, options).Value<string>("id");
        }

        /// <summary>
        /// Declines the pending request to record, so the next status tells its caller the user
        /// said no.
        /// </summary>
        public static void Decline() {
            Consent.Decline(DateTime.UtcNow);
        }

        /// <summary>
        /// Applies <c>[agent] recording_start</c>. Called on every pyRevit load while the host is
        /// enabled.
        /// </summary>
        /// <remarks>
        /// A reload from inside an agent run can't make recordings start automatically. The
        /// refusal is logged and never thrown, so the rest of the host's configuration still runs.
        /// </remarks>
        internal static void Configure(string start) {
            try {
                Consent.SetStartMode(ParseStart(start));
            }
            catch (AgentException ex) when (ex.Code == "recording_locked") {
                logger.Warn("Recordings keep starting in the agent panel until pyRevit reloads outside an agent run: {0}", ex.Message);
            }
        }

        /// <summary>
        /// Leaves a request for the user to start a recording with <paramref name="options"/>,
        /// for a caller outside Revit while recordings start in the agent panel.
        /// </summary>
        /// <returns>The recorder's status with <c>requested</c> set, and what the caller does next.</returns>
        /// <exception cref="AgentException"><c>recording_active</c> when a recording is already active.</exception>
        internal static JObject Request(AgentRecordingOptions options, string reason) {
            var active = store;
            if (active != null)
                throw new AgentException("recording_active", "A recording is already active: " + active.Id + ". Stop it first.");
            Consent.Request(options, reason, DateTime.UtcNow);
            if (AgentHost.InlineApplication == null)
                AgentPanel.RevealForRequest();
            var status = Status();
            status["requested"] = true;
            status["message"] = "Recordings start in Revit: the user starts this one in the agent panel, or declines it. "
                + "Tell them you asked; recording_status ('pyrevit agent record status') shows whether it started.";
            return status;
        }

        /// <summary>
        /// Emits a structured breadcrumb from an extension into the active recording. Does
        /// nothing when no recording is active.
        /// </summary>
        /// <param name="source">Who emitted it, such as an extension or tool name.</param>
        /// <param name="dataJson">A JSON value; text that is not valid JSON is stored as a string.</param>
        public static void Mark(string source, string dataJson) {
            if (store == null)
                return;
            Append("mark", new JObject { ["source"] = source, ["data"] = AgentRecordingStore.ParseMarkData(dataJson) });
        }

        internal static void RecordAgentRun(JObject response) {
            if (store == null)
                return;
            try {
                Append("agent_run", new JObject {
                    ["run_id"] = response["run_id"],
                    ["session_id"] = response["session_id"],
                    ["document"] = response["document"],
                    ["title"] = response["title"],
                    ["status"] = response["status"],
                    ["decision"] = response["decision"],
                    ["error"] = AgentRecordingStore.BoundError(response["error"]),
                    ["output"] = AgentRecordingStore.Truncate(response["output"]?.ToString()),
                });
            }
            catch (Exception ex) {
                logger.Debug("Could not record the agent run: {0}", ex.Message);
            }
        }

        /// <remarks>
        /// A recording that starts answers the pending request and clears the last decline.
        /// </remarks>
        internal static JObject Start(UIApplication app, AgentRecordingOptions options) {
            JObject started;
            lock (sync) {
                if (store != null)
                    throw new AgentException("recording_active", "A recording is already active: " + store.Id + ". Stop it first.");
                pendingOutput.Drain();
                var sessionId = AgentSessions.Tracker.SessionId;
                var created = AgentRecordingStore.Create(AgentPaths.RecordingsDir, options, sessionId);
                logger.Info("Recording {0} started", created.Id);
                var attaching = new AgentRecordingWatch(app, created);
                store = created;
                Append("recording_started", new JObject { ["options"] = options.ToJson(), ["session_id"] = sessionId });
                try {
                    attaching.Attach();
                }
                catch (Exception) {
                    store = null;
                    attaching.Dispose();
                    created.Stop("start_failed");
                    throw;
                }
                watch = attaching;
                started = Describe(created, "recording");
            }
            Consent.Clear();
            StateChanged?.Invoke();
            return started;
        }

        internal static JObject Stop(string reason) {
            JObject summary;
            lock (sync) {
                var active = store;
                if (active == null)
                    throw new AgentException("not_recording", "No recording is active.");
                Append(AgentRecordingStore.StoppedKind, new JObject { ["reason"] = reason });
                store = null;
                pendingOutput.Drain();
                var ending = watch;
                watch = null;
                try {
                    if (ScriptExecutor.IsOnMainThread)
                        ending?.Dispose();
                }
                finally {
                    summary = active.Stop(reason);
                }
                summary["directory"] = active.Directory;
                logger.Info("Recording {0} stopped: {1}", active.Id, reason);
            }
            StateChanged?.Invoke();
            return summary;
        }

        internal static void StopIfActive(string reason) {
            try {
                if (store != null)
                    Stop(reason);
            }
            catch (Exception ex) {
                logger.Debug("Could not stop the recording: {0}", ex.Message);
            }
        }

        /// <summary>
        /// The active recording, if any, and how recordings start: <c>start</c>, the
        /// <c>pending_request</c> waiting for the user and the <c>declined_request</c> they last
        /// said no to.
        /// </summary>
        internal static JObject Status() {
            var active = store;
            JObject status;
            if (active == null)
                status = new JObject { ["recording"] = false };
            else {
                status = Describe(active, "recording");
                status["recording"] = true;
                status["elapsed_ms"] = (long)active.Elapsed.TotalMilliseconds;
            }
            foreach (var property in Consent.Describe().Properties())
                status[property.Name] = property.Value;
            return status;
        }

        internal static string ActiveDirectory => store?.Directory;

        internal static bool IsCurrent(AgentRecordingStore candidate) => ReferenceEquals(store, candidate);

        internal static void FlushOutput() {
            var drained = pendingOutput.Drain();
            if (drained != null)
                AppendEntry("output", new JObject { ["text"] = drained });
        }

        internal static void Append(string kind, JObject data) {
            FlushOutput();
            AppendEntry(kind, data);
        }

        private static void AppendEntry(string kind, JObject data) {
            if (appending)
                return;
            appending = true;
            try {
                store?.Append(kind, data);
            }
            catch (Exception ex) {
                logger.Debug("Could not append to the recording: {0}", ex.Message);
            }
            finally {
                appending = false;
            }
        }

        internal static void RecordCommand(string phase, string name, string uniqueId, int? result, string trace) {
            if (store == null)
                return;
            var data = new JObject { ["phase"] = phase, ["command"] = name, ["command_id"] = uniqueId };
            if (result.HasValue) {
                data["result_code"] = result.Value;
                data["succeeded"] = result.Value == ScriptExecutorResultCodes.Succeeded;
            }
            if (!string.IsNullOrEmpty(trace))
                data["trace"] = AgentRecordingStore.Truncate(trace);
            Append("command", data);
        }

        internal static void RecordOutput(string text) {
            if (store == null || outputSuppressed || string.IsNullOrEmpty(text))
                return;
            pendingOutput.Add(text);
        }

        internal static void RecordLog(string loggerName, int level, string message) {
            if (store == null || level < MinimumLoggedLevel)
                return;
            Append("log", new JObject {
                ["logger"] = loggerName,
                ["level"] = level,
                ["message"] = AgentRecordingStore.Truncate(message),
            });
        }

        private static AgentRecordingStart ParseStart(string mode) {
            switch ((mode ?? string.Empty).Trim().ToLowerInvariant()) {
                case StartUser:
                    return AgentRecordingStart.User;
                case StartAuto:
                    return AgentRecordingStart.Auto;
                default:
                    throw new ArgumentException($"Recordings start '{StartUser}' or '{StartAuto}', not '{mode}'.", nameof(mode));
            }
        }

        private static JObject Describe(AgentRecordingStore active, string status) {
            return new JObject {
                ["id"] = active.Id,
                ["status"] = status,
                ["session_id"] = active.SessionId,
                ["started"] = active.StartedUtc.ToString("o"),
                ["directory"] = active.Directory,
                ["options"] = active.Options.ToJson(),
            };
        }
    }
}
