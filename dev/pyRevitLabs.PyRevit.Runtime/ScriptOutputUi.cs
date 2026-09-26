using System;
using System.Globalization;
using System.Threading;

using System.Windows.Threading;

namespace PyRevitLabs.PyRevit.Runtime {
    /// <summary>
    /// Decides whether the calling thread may construct and touch pyRevit's WPF output UI,
    /// and is the only route by which any other thread reaches it.
    /// </summary>
    /// <remarks>
    /// Warning: a <see cref="ScriptConsole"/> may only be constructed on, and its members only
    /// called from, the thread that owns the host's UI. WPF needs STA plus a message pump the
    /// host owns, so a background worker that reaches <c>Window..ctor()</c> raises
    /// <c>InvalidOperationException</c> - and unhandled on that worker it takes the whole Revit
    /// process down (pyRevit #3473). Output entry points therefore ask
    /// <see cref="MayCreateOutputUi"/> before they touch a window, and a background producer
    /// hands its work over with <see cref="TryBeginInvoke"/> instead.
    /// <para>
    /// Invariant: <see cref="CaptureHostUiThread"/> is the only writer of the host thread, the
    /// first capture wins, and only an STA caller can make one. The host's UI thread is STA and
    /// .NET worker threads are MTA, so a worker cannot promote itself.
    /// </para>
    /// <para>
    /// Before any capture the gate answers from the STA requirement alone. That is enough to keep
    /// a worker out, and it keeps a session's first output window creatable even if it is reached
    /// before the runtime that rides along with the capture.
    /// </para>
    /// </remarks>
    internal sealed class ScriptOutputUiGate {
        private readonly object _syncRoot = new object();
        private volatile Dispatcher _hostUiDispatcher;

        /// <summary>
        /// Record the calling thread as the host's UI thread. Ignored unless the caller is STA, and
        /// ignored once a host thread is recorded.
        /// </summary>
        /// <remarks>
        /// Call this only from a thread the host owns. Session loads and script runtimes are
        /// created on the host's UI thread, which is what the runtime does on construction.
        /// </remarks>
        internal void CaptureHostUiThread() {
            if (Thread.CurrentThread.GetApartmentState() != ApartmentState.STA)
                return;

            var dispatcher = Dispatcher.CurrentDispatcher;
            if (dispatcher == null)
                return;

            lock (_syncRoot) {
                if (_hostUiDispatcher == null)
                    _hostUiDispatcher = dispatcher;
            }
        }

        /// <summary>Whether a host UI thread has been recorded.</summary>
        internal bool HasHostUiThread {
            get { return _hostUiDispatcher != null; }
        }

        /// <summary>Whether the caller is the recorded host UI thread, and its pump is alive.</summary>
        internal bool IsHostUiThread {
            get {
                var dispatcher = _hostUiDispatcher;
                return dispatcher != null && IsPumpAlive(dispatcher) && dispatcher.CheckAccess();
            }
        }

        /// <summary>
        /// Whether the caller may construct and touch output WPF. False means the caller must take
        /// the safe sink instead: buffer the text, then hand it to the host UI thread.
        /// </summary>
        internal bool MayCreateOutputUi {
            get {
                var dispatcher = _hostUiDispatcher;
                if (dispatcher == null)
                    return Thread.CurrentThread.GetApartmentState() == ApartmentState.STA;
                return IsPumpAlive(dispatcher) && dispatcher.CheckAccess();
            }
        }

        /// <summary>
        /// Run <paramref name="action"/> on the host UI thread, or report that it could not be.
        /// Runs inline when the caller is already that thread, so a UI-thread producer keeps its
        /// current synchronous behaviour.
        /// </summary>
        /// <remarks>
        /// The hand-off is fire-and-forget by design. A blocking invoke would stall the producer
        /// for as long as the host's UI is busy - which, with a modal dialog open, reads as a hung
        /// request with no error anywhere (pyRevit #3473). An exception thrown by the action is
        /// contained here: a dispatcher callback that lets one out terminates the host.
        /// </remarks>
        /// <param name="action">Work that must run on the host UI thread.</param>
        /// <param name="priority">Dispatcher priority for the queued hand-off.</param>
        /// <returns>
        /// True if the action ran or was queued. False if there is no live host UI thread to run
        /// it on, in which case the caller must fall back to a non-UI sink.
        /// </returns>
        internal bool TryBeginInvoke(Action action, DispatcherPriority priority = DispatcherPriority.Background) {
            if (action == null)
                return false;

            var dispatcher = _hostUiDispatcher;
            if (dispatcher == null || !IsPumpAlive(dispatcher))
                return false;

            if (dispatcher.CheckAccess()) {
                RunGuarded(action);
                return true;
            }

            try {
                dispatcher.BeginInvoke(new Action(() => RunGuarded(action)), priority);
                return true;
            }
            catch (Exception ex) {
                System.Diagnostics.Trace.TraceWarning(
                    "[ScriptOutputUi] could not queue output work for the host UI thread | {0}", ex);
                return false;
            }
        }

        private static void RunGuarded(Action action) {
            try {
                action();
            }
            catch (Exception ex) {
                System.Diagnostics.Trace.TraceError(
                    "[ScriptOutputUi] output work raised on the host UI thread | {0}", ex);
            }
        }

        private static bool IsPumpAlive(Dispatcher dispatcher) {
            return !dispatcher.HasShutdownStarted && !dispatcher.HasShutdownFinished;
        }

        /// <summary>Caller description for diagnostics; names no output window state.</summary>
        internal static string DescribeCallingThread() {
            var thread = Thread.CurrentThread;
            return string.Format(
                CultureInfo.InvariantCulture,
                "thread {0} ({1})",
                thread.ManagedThreadId,
                thread.GetApartmentState());
        }
    }

    /// <summary>
    /// Process-wide <see cref="ScriptOutputUiGate"/>, the single answer to "may this thread touch
    /// the output window?" for the whole runtime.
    /// </summary>
    internal static class ScriptOutputUi {
        private static readonly ScriptOutputUiGate Gate = new ScriptOutputUiGate();

        internal static void CaptureHostUiThread() {
            Gate.CaptureHostUiThread();
        }

        internal static bool MayCreateOutputUi {
            get { return Gate.MayCreateOutputUi; }
        }

        internal static bool TryBeginInvoke(Action action, DispatcherPriority priority = DispatcherPriority.Background) {
            return Gate.TryBeginInvoke(action, priority);
        }

        internal static string DescribeCallingThread() {
            return ScriptOutputUiGate.DescribeCallingThread();
        }
    }
}
