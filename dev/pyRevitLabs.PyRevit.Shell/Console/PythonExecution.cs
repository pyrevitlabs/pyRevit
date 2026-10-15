using System;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Threading;
using IronPython.Hosting;
using Microsoft.Scripting;
using Microsoft.Scripting.Hosting;

namespace PythonConsoleControl {
    internal sealed class PythonExecution : IDisposable {
        [ThreadStatic] static CancellationToken currentCancellationToken;
        static readonly bool isWindows = Environment.OSVersion.Platform == PlatformID.Win32NT;
        static readonly ConditionalWeakTable<ScriptEngine, object> engineLocks = new ConditionalWeakTable<ScriptEngine, object>();
        readonly object executionLock = new object();
        CancellationTokenSource cancellation;
        bool disposed;
        int executionStarted;
        bool interruptKeyPressed;
        bool hasInterruptedExecution;
        int interruptedStarted;
        int interruptedEnded;

        /// <summary>
        /// Gets cancellation for the dispatch request being submitted on the current thread.
        /// </summary>
        /// <remarks>
        /// Important: dispatch reads this token on the calling thread before marshalling the callback and waits until the callback finishes or is cancelled before it starts.
        /// </remarks>
        internal static CancellationToken CurrentCancellationToken => currentCancellationToken;
        /// <summary>
        /// Gets the Windows message tick clock used by WPF input timestamps.
        /// </summary>
        internal static int InputTimestamp => isWindows ? GetTickCount() : Environment.TickCount;

        [DllImport("kernel32.dll")]
        static extern int GetTickCount();
        internal bool IsRunning { get { lock (executionLock) return cancellation != null; } }

        internal void Interrupt() {
            lock (executionLock) cancellation?.Cancel();
        }

        internal bool Interrupt(int inputTimestamp) {
            lock (executionLock) {
                var hasTimestamp = inputTimestamp != 0;
                if (!hasTimestamp) inputTimestamp = InputTimestamp;
                if (cancellation == null || (hasTimestamp && (unchecked(inputTimestamp - executionStarted) < 0
                    || IsCompletedInterruptedInput(inputTimestamp)))) return false;
                interruptKeyPressed = true;
                cancellation.Cancel();
                return true;
            }
        }

        internal bool IsInterruptedInput(int inputTimestamp) {
            lock (executionLock) {
                if (inputTimestamp == 0) inputTimestamp = InputTimestamp;
                if (cancellation != null && cancellation.IsCancellationRequested)
                    return unchecked(inputTimestamp - executionStarted) >= 0;
                return IsCompletedInterruptedInput(inputTimestamp);
            }
        }

        bool IsCompletedInterruptedInput(int inputTimestamp) {
            return hasInterruptedExecution
                && unchecked(inputTimestamp - interruptedStarted) >= 0
                && unchecked(interruptedEnded - inputTimestamp) >= 0;
        }

        /// <summary>
        /// Waits for this execution's active statement, then dispatches the command with cancellation tracing.
        /// </summary>
        /// <remarks>
        /// Important: dispatch is synchronous and consumes CurrentCancellationToken on the calling thread; callbacks sharing an engine execute serially.
        /// </remarks>
        internal void Run(ScriptEngine engine, Action command, Action<Action> dispatch, Func<bool> interruptRequested = null) {
            TryRun(engine, command, dispatch, interruptRequested, true);
        }

        internal bool TryRun(ScriptEngine engine, Action command, Action<Action> dispatch, Func<bool> interruptRequested = null, bool waitForExecution = false) {
            if (command == null) return true;
            CancellationTokenSource source;
            lock (executionLock) {
                while (cancellation != null && !disposed) {
                    if (!waitForExecution) return false;
                    Monitor.Wait(executionLock);
                }
                if (disposed) throw new KeyboardInterruptException("");
                source = cancellation = new CancellationTokenSource();
                executionStarted = InputTimestamp;
            }
            var previousCancellationToken = currentCancellationToken;
            currentCancellationToken = source.Token;
            try {
                dispatch(() => {
                    var engineLock = engineLocks.GetValue(engine, _ => new object());
                    while (!Monitor.TryEnter(engineLock, TimeSpan.FromMilliseconds(50)))
                        if (source.IsCancellationRequested) throw new KeyboardInterruptException("");
                    try {
                        if (interruptRequested != null) {
                            var keyPressedAtStart = interruptRequested();
                            lock (executionLock) interruptKeyPressed = keyPressedAtStart;
                        }
                        IronPython.Runtime.Exceptions.TracebackDelegate trace = null;
                        var nextKeyboardCheck = InputTimestamp;
                        trace = (frame, traceEvent, payload) => {
                            if (interruptRequested != null && unchecked(InputTimestamp - nextKeyboardCheck) >= 0) {
                                nextKeyboardCheck = unchecked(InputTimestamp + 10);
                                var keyPressed = interruptRequested();
                                lock (executionLock) {
                                    if (keyPressed && !interruptKeyPressed) source.Cancel();
                                    interruptKeyPressed = keyPressed;
                                }
                            }
                            if (source.IsCancellationRequested) throw new KeyboardInterruptException("");
                            return trace;
                        };
                        if (source.IsCancellationRequested) throw new KeyboardInterruptException("");
                        engine.SetTrace(trace);
                        try { command(); }
                        finally { engine.SetTrace(null); }
                    }
                    finally { Monitor.Exit(engineLock); }
                });
            }
            finally {
                currentCancellationToken = previousCancellationToken;
                lock (executionLock) {
                    if (source.IsCancellationRequested) {
                        hasInterruptedExecution = true;
                        interruptedStarted = executionStarted;
                        interruptedEnded = InputTimestamp;
                    }
                    cancellation = null;
                    source.Dispose();
                    Monitor.PulseAll(executionLock);
                }
            }
            return true;
        }

        public void Dispose() {
            lock (executionLock) {
                disposed = true;
                cancellation?.Cancel();
                Monitor.PulseAll(executionLock);
            }
        }
    }
}
