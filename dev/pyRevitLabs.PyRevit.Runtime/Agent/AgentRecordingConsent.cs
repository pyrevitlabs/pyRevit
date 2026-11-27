using System;

using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>How recordings start, from <c>[agent] recording_start</c>.</summary>
    internal enum AgentRecordingStart {
        /// <summary>Only the user starts a recording, in the agent panel.</summary>
        User,

        /// <summary>A start the CLI or an agent asks for begins recording at once.</summary>
        Auto,
    }

    /// <summary>
    /// The user's consent to record what happens in Revit: how recordings start, the start the
    /// CLI or an agent is waiting on, and the last one the user declined. Pure logic with no
    /// Revit dependency; <see cref="AgentRecorder"/> connects it to the recorder.
    /// </summary>
    /// <remarks>
    /// A recording shows an agent what the user did in every open document, so it needs the
    /// user's consent apart from an agent session, which lets agents act in chosen documents.
    /// Invariants:
    /// <list type="bullet">
    /// <item>With <see cref="AgentRecordingStart.User"/>, a start asked for from outside Revit
    /// never starts a recording. It leaves a request, which only the user's click in Revit
    /// takes.</item>
    /// <item>Nothing that loosens that succeeds while an agent run executes, so run code can't
    /// let itself record: making recordings start automatically, or starting one as the
    /// user.</item>
    /// </list>
    /// Every member is safe to call from any thread. <see cref="Changed"/> is raised on the
    /// thread that made the change, after the lock is released.
    /// </remarks>
    internal sealed class AgentRecordingConsent {
        private readonly object sync = new object();
        private readonly Func<bool> runExecuting;
        private AgentRecordingStart startMode = AgentRecordingStart.User;
        private AgentRecordingOptions pendingOptions;
        private JObject pendingRequest;
        private JObject lastDeclined;

        /// <param name="runExecuting">Whether an agent run executes now.</param>
        public AgentRecordingConsent(Func<bool> runExecuting) {
            this.runExecuting = runExecuting ?? throw new ArgumentNullException(nameof(runExecuting));
        }

        public event Action Changed;

        public AgentRecordingStart StartMode {
            get {
                lock (sync)
                    return startMode;
            }
        }

        /// <summary>
        /// The limits the pending request asked for, or null when no request is pending.
        /// </summary>
        public AgentRecordingOptions PendingOptions {
            get {
                lock (sync)
                    return pendingOptions;
            }
        }

        /// <exception cref="AgentException">
        /// <c>recording_locked</c> when making recordings start automatically while an agent run
        /// executes.
        /// </exception>
        public void SetStartMode(AgentRecordingStart mode) {
            lock (sync) {
                if (startMode == mode)
                    return;
                if (mode == AgentRecordingStart.Auto)
                    RefuseWhileRunExecutes("Recordings can't be made to start automatically while an agent run executes.");
                startMode = mode;
            }
            Changed?.Invoke();
        }

        /// <summary>
        /// Records a request to start a recording with <paramref name="options"/>, replacing an
        /// earlier one. A new request also clears the last decline.
        /// </summary>
        /// <returns>The pending request as <see cref="Describe"/> reports it.</returns>
        public JObject Request(AgentRecordingOptions options, string reason, DateTime nowUtc) {
            if (options == null)
                throw new ArgumentNullException(nameof(options));
            JObject requested;
            lock (sync) {
                pendingOptions = options;
                pendingRequest = new JObject {
                    ["reason"] = string.IsNullOrWhiteSpace(reason) ? JValue.CreateNull() : new JValue(reason.Trim()),
                    ["requested"] = nowUtc.ToString("o"),
                    ["options"] = options.ToJson(),
                };
                lastDeclined = null;
                requested = (JObject)pendingRequest.DeepClone();
            }
            Changed?.Invoke();
            return requested;
        }

        /// <summary>
        /// Declines the pending request, so the next status tells the caller the user said no.
        /// </summary>
        /// <returns>False when no request is pending.</returns>
        public bool Decline(DateTime nowUtc) {
            lock (sync) {
                if (pendingRequest == null)
                    return false;
                lastDeclined = (JObject)pendingRequest.DeepClone();
                lastDeclined["declined"] = nowUtc.ToString("o");
                pendingRequest = null;
                pendingOptions = null;
            }
            Changed?.Invoke();
            return true;
        }

        /// <summary>
        /// Forgets the pending request and the last decline, as when a recording starts or the
        /// host stops.
        /// </summary>
        public void Clear() {
            lock (sync) {
                if (pendingRequest == null && lastDeclined == null)
                    return;
                pendingRequest = null;
                pendingOptions = null;
                lastDeclined = null;
            }
            Changed?.Invoke();
        }

        /// <exception cref="AgentException"><c>recording_locked</c> while an agent run executes.</exception>
        public void RefuseWhileRunExecutes(string message) {
            if (runExecuting())
                throw new AgentException("recording_locked", message);
        }

        public JObject Describe() {
            lock (sync) {
                return new JObject {
                    ["start"] = startMode == AgentRecordingStart.Auto ? "auto" : "user",
                    ["pending_request"] = pendingRequest?.DeepClone(),
                    ["declined_request"] = lastDeclined?.DeepClone(),
                };
            }
        }
    }
}
