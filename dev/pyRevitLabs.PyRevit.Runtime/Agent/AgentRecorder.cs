using System;

using Autodesk.Revit.UI;

using pyRevitLabs.Json.Linq;
using pyRevitLabs.NLog;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// The explicit record/stop session recorder. It is off until a user starts it and records
    /// only between <see cref="Start"/> and <see cref="Stop"/>.
    /// </summary>
    /// <remarks>
    /// Every hook (<see cref="Mark"/>, command, output and log records) is a no-op while no
    /// recording is active, so the idle cost is one volatile read. Recordings are plaintext and
    /// stay in <c>%APPDATA%\pyRevit\agent\recordings</c>; nothing leaves the machine unless the
    /// user shares the folder, or an agent reads it through <c>get_recording</c>.
    /// Invariant: at most one recording is active per Revit process.
    /// Important: <see cref="Start"/> must run in a valid Revit API context. A stop requested off
    /// the Revit main thread ends the recording but leaves unsubscribing to the session's next
    /// <c>Idling</c>, so shutdown never touches Revit events from the wrong thread. Both must run in a valid Revit API
    /// context, because they subscribe to and unsubscribe from Revit events.
    /// </remarks>
    public static class AgentRecorder {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();
        private static readonly object sync = new object();
        private const int MinimumLoggedLevel = (int)ScriptLogLevel.Info;
        private static volatile AgentRecordingStore store;
        private static AgentRecorderSession session;

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

        internal static IDisposable SuppressOutput() => new OutputSuppression();

        public static bool IsRecording => store != null;

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

        internal static JObject Start(UIApplication app, AgentRecordingOptions options) {
            lock (sync) {
                if (store != null)
                    throw new AgentException("recording_active", "A recording is already active: " + store.Id + ". Stop it first.");
                var root = AgentPaths.RecordingsDir;
                AgentRecordingStore.Prune(root, DateTime.Now, null);
                var created = AgentRecordingStore.Create(root, options);
                logger.Info("Session recording {0} started", created.Id);
                var attaching = new AgentRecorderSession(app, created);
                store = created;
                Append("recording_started", new JObject { ["options"] = options.ToJson() });
                try {
                    attaching.Attach();
                }
                catch (Exception) {
                    store = null;
                    attaching.Dispose();
                    created.Stop("start_failed");
                    throw;
                }
                session = attaching;
                return Describe(created, "recording");
            }
        }

        internal static JObject Stop(string reason) {
            lock (sync) {
                var active = store;
                if (active == null)
                    throw new AgentException("not_recording", "No recording is active.");
                Append("recording_stopped", new JObject { ["reason"] = reason });
                store = null;
                var ending = session;
                session = null;
                JObject summary;
                try {
                    if (ScriptExecutor.IsOnMainThread)
                        ending?.Dispose();
                }
                finally {
                    summary = active.Stop(reason);
                }
                summary["directory"] = active.Directory;
                logger.Info("Session recording {0} stopped: {1}", active.Id, reason);
                return summary;
            }
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

        internal static JObject Status() {
            var active = store;
            if (active == null)
                return new JObject { ["recording"] = false };
            var status = Describe(active, "recording");
            status["recording"] = true;
            status["elapsed_ms"] = (long)active.Elapsed.TotalMilliseconds;
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

        private static JObject Describe(AgentRecordingStore active, string status) {
            return new JObject {
                ["id"] = active.Id,
                ["status"] = status,
                ["directory"] = active.Directory,
                ["options"] = active.Options.ToJson(),
            };
        }
    }
}
