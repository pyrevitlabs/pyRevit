using System;
using System.Runtime.InteropServices;
using System.Threading;
using IronPython.Hosting;
using IronPython.Runtime.Exceptions;
using Microsoft.Scripting;
using Microsoft.Scripting.Hosting;

namespace PythonConsoleControl {
    internal sealed class PythonExecution : IDisposable {
        [ThreadStatic] static CancellationToken currentCancellationToken;
        static readonly bool isWindows = Environment.OSVersion.Platform == PlatformID.Win32NT;
        readonly object executionLock = new object();
        CancellationTokenSource cancellation;
        bool disposed;
        // WPF input timestamps use the Windows GetTickCount clock.
        int executionStarted;
        bool interruptKeyPressed;
        bool hasInterruptedExecution;
        int interruptedStarted;
        int interruptedEnded;

        internal static CancellationToken CurrentCancellationToken => currentCancellationToken;
        internal static int InputTimestamp => isWindows ? GetTickCount() : Environment.TickCount;

        [DllImport("kernel32.dll")]
        static extern int GetTickCount();
        internal bool IsRunning { get { lock (executionLock) return cancellation != null; } }

        internal void Interrupt() {
            lock (executionLock) cancellation?.Cancel();
        }

        internal bool Interrupt(int inputTimestamp) {
            lock (executionLock) {
                if (cancellation == null || unchecked(inputTimestamp - executionStarted) < 0
                    || IsCompletedInterruptedInput(inputTimestamp)) return false;
                interruptKeyPressed = true;
                cancellation.Cancel();
                return true;
            }
        }

        internal bool IsInterruptedInput(int inputTimestamp) {
            lock (executionLock) {
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
                    TracebackDelegate trace = null;
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
