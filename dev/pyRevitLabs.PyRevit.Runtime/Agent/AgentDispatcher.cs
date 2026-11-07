using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Threading;
using System.Threading.Tasks;

using Autodesk.Revit.UI;

using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Queues agent work from the pipe thread and runs it on the Revit main thread through
    /// one ExternalEvent.
    /// </summary>
    /// <remarks>
    /// Modeled on the shell's <c>ShellExternalEventDispatcher</c>: callers block on a task
    /// instead of spinning on <see cref="ExternalEvent.IsPending"/>, and every queued item is
    /// drained in order, so concurrent requests can never overwrite each other.
    /// </remarks>
    internal sealed class AgentDispatcher : IExternalEventHandler {
        public const string RunHungCode = "run_hung";

        private static readonly TimeSpan DefaultHungGrace = TimeSpan.FromSeconds(30);
        private static readonly TimeSpan HungPollInterval = TimeSpan.FromSeconds(1);

        private readonly object queueLock = new object();
        private readonly Queue<AgentWorkItem> queue = new Queue<AgentWorkItem>();
        private readonly TimeSpan hungGrace;
        private ExternalEvent externalEvent;
        private long runningSinceTicks;
        private ScriptDeadline currentScript;

        public AgentDispatcher() : this(DefaultHungGrace) {
        }

        internal AgentDispatcher(TimeSpan hungGrace) {
            this.hungGrace = hungGrace;
        }

        public void Attach(ExternalEvent ev) {
            externalEvent = ev;
        }

        /// <summary>
        /// Runs <paramref name="work"/> on the main thread and waits for its result.
        /// </summary>
        /// <exception cref="AgentException">
        /// <c>revit_busy</c> (see <see cref="AgentException.NotRun"/>) when Revit refuses the
        /// ExternalEvent or does not become idle within <paramref name="startTimeout"/>. The work
        /// is then removed from the queue and never runs. Once the work has started, the call
        /// waits for it to finish, because it can't be aborted safely, unless its script passes
        /// the deadline set by <see cref="BeginScript"/> by more than the grace period.
        /// </exception>
        /// <exception cref="AgentException">
        /// <c>run_hung</c> with outcome <c>unknown</c> when the script is stuck past its deadline
        /// in a call its timeout can't interrupt. The work keeps running on the main thread and
        /// finishes, and is recorded, whenever that call returns; the caller just stops waiting,
        /// so the pipe can answer later requests.
        /// </exception>
        public JToken Invoke(Func<UIApplication, JToken> work, TimeSpan startTimeout) {
            var item = new AgentWorkItem(work);
            lock (queueLock)
                queue.Enqueue(item);

            var response = externalEvent.Raise();
            if (response == ExternalEventRequest.Denied || response == ExternalEventRequest.TimedOut) {
                if (TryRemove(item))
                    throw AgentException.NotRun("Revit rejected the agent request: " + response + ".");
            }

            if (!item.Started.Wait(startTimeout)) {
                if (TryRemove(item))
                    throw AgentException.NotRun(BusyMessage(startTimeout));
            }

            var completion = new Task[] { item.Completion.Task };
            while (Task.WaitAny(completion, HungPollInterval) < 0) {
                var stuck = OverdueScript();
                if (stuck != null)
                    throw RunHung(stuck);
            }
            return item.Completion.Task.GetAwaiter().GetResult();
        }

        /// <summary>
        /// Marks the script of the work running now as due to end within
        /// <paramref name="timeLimit"/>, until the returned object is disposed.
        /// </summary>
        /// <remarks>
        /// Called on the main thread around the script only, so time spent waiting for the
        /// user's approval never counts. Disposing restores the previous deadline, so a nested run
        /// can't clear the deadline of the run that started it. <paramref name="runId"/> and
        /// <paramref name="requestId"/> go into the <c>run_hung</c> error.
        /// </remarks>
        public IDisposable BeginScript(TimeSpan timeLimit, string runId, string requestId) {
            var script = new ScriptDeadline(this, timeLimit, runId, requestId);
            script.Previous = Interlocked.Exchange(ref currentScript, script);
            return script;
        }

        private ScriptDeadline OverdueScript() {
            var script = Volatile.Read(ref currentScript);
            return script != null && script.Overdue > hungGrace ? script : null;
        }

        private static AgentException RunHung(ScriptDeadline script) {
            var exception = new AgentException(
                RunHungCode,
                string.Format(
                    "The script is still running {0:0}s past its time limit, stuck in a call its timeout "
                    + "can't interrupt, such as a long Revit API call, Thread.Sleep, or a printer or window "
                    + "waiting for input. Revit stays busy, and later requests that need it fail with "
                    + "revit_busy, until that call returns; the run then ends and is recorded as usual. Look "
                    + "it up by its request id before sending it again, and ask the user to check Revit.",
                    script.Overdue.TotalSeconds));
            exception.Details["outcome"] = "unknown";
            exception.Details["run_id"] = script.RunId;
            exception.Details["request_id"] = script.RequestId;
            return exception;
        }

        public void Execute(UIApplication app) {
            AgentWorkItem item;
            while (TryDequeue(out item)) {
                item.Started.Set();
                Interlocked.Exchange(ref runningSinceTicks, DateTime.UtcNow.Ticks);
                try {
                    item.Completion.TrySetResult(item.Work(app));
                }
                catch (Exception ex) {
                    item.Completion.TrySetException(ex);
                }
                finally {
                    Interlocked.Exchange(ref runningSinceTicks, 0);
                }
            }
        }

        private string BusyMessage(TimeSpan startTimeout) {
            var message = string.Format("Revit did not become idle within {0:0}s.", startTimeout.TotalSeconds);
            var since = Interlocked.Read(ref runningSinceTicks);
            var stuck = OverdueScript();
            if (since != 0 && stuck != null)
                return message + string.Format(
                    " An earlier agent run is stuck {0:0}s past its time limit in a call its timeout can't "
                    + "interrupt; Revit stays busy until that call returns.",
                    stuck.Overdue.TotalSeconds);
            if (since != 0)
                message += string.Format(
                    " An earlier agent request has been running for {0:0}s; it may be waiting on a dialog.",
                    TimeSpan.FromTicks(DateTime.UtcNow.Ticks - since).TotalSeconds);
            var dialogs = AgentWindows.OpenDialogs();
            if (dialogs.Count > 0)
                message += " Open Revit windows: " + string.Join(", ", dialogs)
                    + ". A modal dialog (for example Revit's save reminder) blocks every request until it is answered: "
                    + "ask the user to answer it. Don't close Revit windows yourself; closing one can cancel work.";
            return message;
        }

        public string GetName() {
            return "pyRevit Agent";
        }

        private bool TryDequeue(out AgentWorkItem item) {
            lock (queueLock) {
                if (queue.Count == 0) {
                    item = null;
                    return false;
                }
                item = queue.Dequeue();
                return true;
            }
        }

        private bool TryRemove(AgentWorkItem item) {
            lock (queueLock) {
                if (item.Started.IsSet || !queue.Contains(item))
                    return false;
                var remaining = new Queue<AgentWorkItem>();
                foreach (var queued in queue)
                    if (!ReferenceEquals(queued, item))
                        remaining.Enqueue(queued);
                queue.Clear();
                foreach (var queued in remaining)
                    queue.Enqueue(queued);
                return true;
            }
        }

        private sealed class ScriptDeadline : IDisposable {
            private readonly AgentDispatcher owner;
            private readonly long dueTimestamp;
            private int disposed;

            public ScriptDeadline(AgentDispatcher owner, TimeSpan timeLimit, string runId, string requestId) {
                this.owner = owner;
                dueTimestamp = Stopwatch.GetTimestamp() + (long)(timeLimit.TotalSeconds * Stopwatch.Frequency);
                RunId = runId;
                RequestId = requestId;
            }

            public string RunId { get; }
            public string RequestId { get; }
            public ScriptDeadline Previous { get; set; }

            public TimeSpan Overdue =>
                TimeSpan.FromSeconds((double)(Stopwatch.GetTimestamp() - dueTimestamp) / Stopwatch.Frequency);

            public void Dispose() {
                if (Interlocked.Exchange(ref disposed, 1) == 0)
                    Interlocked.Exchange(ref owner.currentScript, Previous);
            }
        }

        private sealed class AgentWorkItem {
            public AgentWorkItem(Func<UIApplication, JToken> work) {
                Work = work;
            }

            public Func<UIApplication, JToken> Work { get; }
            public ManualResetEventSlim Started { get; } = new ManualResetEventSlim(false);
            public TaskCompletionSource<JToken> Completion { get; } =
                new TaskCompletionSource<JToken>(TaskCreationOptions.RunContinuationsAsynchronously);
        }
    }

    /// <summary>
    /// A failure reported to the agent with a stable machine-readable <see cref="Code"/>.
    /// </summary>
    public sealed class AgentException : Exception {
        public const string NotRunCode = "revit_busy";

        public AgentException(string code, string message) : base(message) {
            Code = code;
        }

        public string Code { get; }

        /// <summary>
        /// Extra fields for the error's <c>data</c> object, next to <c>type</c>.
        /// </summary>
        public JObject Details { get; } = new JObject();

        /// <summary>
        /// A request the host refused before running any of it because Revit was busy.
        /// </summary>
        /// <remarks>
        /// Invariant: every <c>revit_busy</c> the host raises goes through here. It means the
        /// request was discarded and will never run later, so the caller may send it again.
        /// The message says so and <c>data.outcome</c> is <c>not_run</c>.
        /// </remarks>
        public static AgentException NotRun(string message) {
            var exception = new AgentException(
                NotRunCode,
                message + " The request was not run and has been discarded; it will not run later, "
                + "so it is safe to send again once Revit is idle.");
            exception.Details["outcome"] = "not_run";
            return exception;
        }
    }
}
