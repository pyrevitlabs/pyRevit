using System;
using System.Collections.Generic;
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
        private readonly object queueLock = new object();
        private readonly Queue<AgentWorkItem> queue = new Queue<AgentWorkItem>();
        private ExternalEvent externalEvent;

        public void Attach(ExternalEvent ev) {
            externalEvent = ev;
        }

        /// <summary>
        /// Runs <paramref name="work"/> on the main thread and waits for its result.
        /// </summary>
        /// <exception cref="AgentException">
        /// <c>revit_busy</c> when Revit refuses the ExternalEvent or does not become idle
        /// within <paramref name="startTimeout"/>. Once the work has started, the call waits
        /// for it to finish no matter how long it takes, because it can't be aborted safely.
        /// </exception>
        public JToken Invoke(Func<UIApplication, JToken> work, TimeSpan startTimeout) {
            var item = new AgentWorkItem(work);
            lock (queueLock)
                queue.Enqueue(item);

            var response = externalEvent.Raise();
            if (response == ExternalEventRequest.Denied || response == ExternalEventRequest.TimedOut) {
                if (TryRemove(item))
                    throw new AgentException("revit_busy", "Revit rejected the agent request: " + response);
            }

            if (!item.Started.Wait(startTimeout)) {
                if (TryRemove(item))
                    throw new AgentException(
                        "revit_busy",
                        string.Format("Revit did not become idle within {0:0}s.", startTimeout.TotalSeconds)
                    );
            }

            return item.Completion.Task.GetAwaiter().GetResult();
        }

        public void Execute(UIApplication app) {
            AgentWorkItem item;
            while (TryDequeue(out item)) {
                item.Started.Set();
                try {
                    item.Completion.TrySetResult(item.Work(app));
                }
                catch (Exception ex) {
                    item.Completion.TrySetException(ex);
                }
            }
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
        public AgentException(string code, string message) : base(message) {
            Code = code;
        }

        public string Code { get; }
    }
}
