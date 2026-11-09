using System;
using System.Collections.Generic;

using Autodesk.Revit.UI;

using pyRevitLabs.NLog;

namespace PyRevitLabs.PyRevit.Runtime {
    /// <summary>
    /// Runs callbacks in Revit API context through one ExternalEvent that every script engine shares.
    /// </summary>
    /// <remarks>
    /// Invariant: the ExternalEvent and its handler live for the whole Revit process, and a callback is
    /// held only until it runs or is refused. Revit keeps every handler passed to
    /// <see cref="ExternalEvent.Create"/> until the event is disposed, so a handler implemented in a
    /// script would keep its engine, and every module that engine imported, alive after each reload.
    /// </remarks>
    public static class ApiContextQueue {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();
        private static readonly object pendingLock = new object();
        private static readonly List<Action> pending = new List<Action>();
        private static ExternalEvent externalEvent;

        /// <summary>
        /// Creates the shared ExternalEvent. Must run in Revit API context; later calls do nothing.
        /// </summary>
        internal static void Initialize() {
            if (externalEvent != null)
                return;

            externalEvent = ExternalEvent.Create(new QueueHandler());
        }

        /// <summary>
        /// Queues <paramref name="callback"/> and raises the shared ExternalEvent, so the callback runs
        /// once the next time Revit is idle.
        /// </summary>
        /// <returns>
        /// The result of <see cref="ExternalEvent.Raise"/>. On <see cref="ExternalEventRequest.Denied"/>
        /// or <see cref="ExternalEventRequest.TimedOut"/> the callback is dropped and never runs.
        /// </returns>
        /// <exception cref="InvalidOperationException">No pyRevit session has initialized the queue.</exception>
        /// <remarks>
        /// An exception the callback raises is logged and does not stop the callbacks queued after it.
        /// </remarks>
        public static ExternalEventRequest Schedule(Action callback) {
            if (callback == null)
                throw new ArgumentNullException(nameof(callback));

            var sharedEvent = externalEvent
                ?? throw new InvalidOperationException("The pyRevit API context queue is not initialized.");

            lock (pendingLock)
                pending.Add(callback);

            ExternalEventRequest request;
            try {
                request = sharedEvent.Raise();
            }
            catch {
                Discard(callback);
                throw;
            }

            if (request == ExternalEventRequest.Denied || request == ExternalEventRequest.TimedOut)
                Discard(callback);
            return request;
        }

        private static void Discard(Action callback) {
            lock (pendingLock)
                pending.Remove(callback);
        }

        private static Action[] TakePending() {
            lock (pendingLock) {
                var callbacks = pending.ToArray();
                pending.Clear();
                return callbacks;
            }
        }

        private sealed class QueueHandler : IExternalEventHandler {
            public void Execute(UIApplication app) {
                foreach (var callback in TakePending()) {
                    try {
                        callback();
                    }
                    catch (Exception ex) {
                        logger.Error(ex, "Callback queued for Revit API context failed.");
                    }
                }
            }

            public string GetName() {
                return "pyRevit API context queue";
            }
        }
    }
}
