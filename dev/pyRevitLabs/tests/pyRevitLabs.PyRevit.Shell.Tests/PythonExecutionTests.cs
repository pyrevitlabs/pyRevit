using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using IronPython.Hosting;
using Microsoft.Scripting;
using PythonConsoleControl;
using PyRevitLabs.PyRevit.Shell;

namespace pyRevitLabs.PyRevit.Shell.Tests {
    public class PythonExecutionTests {
        [Theory]
        [InlineData(false, false)]
        [InlineData(true, false)]
        [InlineData(false, true)]
        [InlineData(true, true)]
        public void InterruptOrDisposeStopsRunningPythonAndEndsWorker(bool dispose, bool nestedExec) {
            var engine = Python.CreateEngine(new Dictionary<string, object> { { "FullFrames", true } });
            var script = nestedExec ? "exec('while True:\\n    pass\\n')" : "while True:\n    pass\n";
            var statement = engine.CreateScriptSourceFromString(script, SourceCodeKind.Statements).Compile();
            using var execution = new PythonExecution();
            using var enteredPython = new ManualResetEventSlim();
            Exception error = null;
            var worker = new Thread(() => {
                try {
                    execution.Run(engine, () => statement.Execute(), command => command(), () => {
                        enteredPython.Set();
                        return false;
                    });
                }
                catch (Exception exception) { error = exception; }
            }) { IsBackground = true };
            worker.Start();
            try {
                Assert.True(enteredPython.Wait(TimeSpan.FromSeconds(10)));
                if (dispose) execution.Dispose();
                else execution.Interrupt();
                Assert.True(worker.Join(TimeSpan.FromSeconds(10)));
                Assert.IsType<KeyboardInterruptException>(error);
                Assert.Contains("KeyboardInterrupt", engine.GetService<Microsoft.Scripting.Hosting.ExceptionOperations>().FormatException(error));
                Assert.False(execution.IsRunning);
                if (!dispose) {
                    object result = null;
                    execution.Run(engine, () => result = engine.Execute("6 * 7"), command => command());
                    Assert.Equal(42, result);
                }
            }
            finally {
                execution.Interrupt();
                if (worker.Join(TimeSpan.FromSeconds(10))) engine.Runtime.Shutdown();
            }
        }

        [Fact]
        public async Task InterruptCancelsExecutionWaitingForApiContextAsync() {
            var engine = Python.CreateEngine();
            using var execution = new PythonExecution();
            using var dispatcher = new ShellExternalEventDispatcher();
            using var queued = new ManualResetEventSlim();
            var ran = false;
            var task = Task.Run(() => Record.Exception(() =>
                execution.Run(engine, () => ran = true, command => {
                    var request = dispatcher.Enqueue(command);
                    queued.Set();
                    request.Wait(PythonExecution.CurrentCancellationToken, () => dispatcher.Cancel(request));
                })));
            try {
                Assert.True(queued.Wait(TimeSpan.FromSeconds(10)));
                execution.Interrupt();
                Assert.IsType<KeyboardInterruptException>(await task.WaitAsync(TimeSpan.FromSeconds(10)));
                dispatcher.ExecutePendingRequests();
                Assert.False(ran);
            }
            finally { execution.Interrupt(); engine.Runtime.Shutdown(); }
        }

        [Fact]
        public async Task DelayedInterruptFromManagedCallCannotCancelNextStatementAsync() {
            var engine = Python.CreateEngine();
            using var execution = new PythonExecution();
            using var enteredCall = new ManualResetEventSlim();
            using var releaseCall = new ManualResetEventSlim();
            var first = Task.Run(() => Record.Exception(() => execution.Run(engine, () => {
                enteredCall.Set();
                releaseCall.Wait();
                engine.Execute("41");
            }, command => command())));
            try {
                Assert.True(enteredCall.Wait(TimeSpan.FromSeconds(10)));
                var inputTimestamp = PythonExecution.InputTimestamp;
                Assert.True(execution.Interrupt(inputTimestamp));
                Assert.False(first.IsCompleted);
                releaseCall.Set();
                Assert.IsType<KeyboardInterruptException>(await first.WaitAsync(TimeSpan.FromSeconds(10)));
                Assert.True(execution.IsInterruptedInput(inputTimestamp));
                object result = null;
                execution.Run(engine, () => {
                    Assert.False(execution.Interrupt(inputTimestamp));
                    result = engine.Execute("42");
                }, command => command());
                Assert.Equal(42, result);
                Assert.False(execution.IsRunning);
            }
            finally {
                releaseCall.Set();
                execution.Interrupt();
                await first.WaitAsync(TimeSpan.FromSeconds(10));
                engine.Runtime.Shutdown();
            }
        }

        [Fact]
        public void HeldInterruptKeyDoesNotInterruptFollowingStatement() {
            var engine = Python.CreateEngine();
            using var execution = new PythonExecution();
            try {
                Assert.Throws<KeyboardInterruptException>(() =>
                    execution.Run(engine, () => engine.Execute("41"), command => command(), () => true));
                object result = null;
                execution.Run(engine, () => result = engine.Execute("42"), command => command(), () => true);
                Assert.Equal(42, result);
                execution.Run(engine, () => engine.Execute("0"), command => command(), () => false);
                Assert.Throws<KeyboardInterruptException>(() =>
                    execution.Run(engine, () => engine.Execute("43"), command => command(), () => true));
            }
            finally { engine.Runtime.Shutdown(); }
        }

        [Fact]
        public void QueuedKeyFromBeforeStatementIsNotAnInterruptOfThatStatement() {
            var engine = Python.CreateEngine();
            using var execution = new PythonExecution();
            var inputTimestamp = unchecked(PythonExecution.InputTimestamp - 1);
            try {
                object result = null;
                execution.Run(engine, () => {
                    Assert.False(execution.Interrupt(inputTimestamp));
                    result = engine.Execute("42");
                }, command => command());
                Assert.Equal(42, result);
            }
            finally { engine.Runtime.Shutdown(); }
        }

        [Fact]
        public async Task EditorRunDoesNotReplaceActiveReplExecutionAsync() {
            var engine = Python.CreateEngine();
            using var execution = new PythonExecution();
            using var entered = new ManualResetEventSlim();
            using var release = new ManualResetEventSlim();
            var repl = Task.Run(() => Record.Exception(() => execution.Run(engine, () => {
                entered.Set();
                release.Wait();
                engine.Execute("41");
            }, command => command())));
            try {
                Assert.True(entered.Wait(TimeSpan.FromSeconds(10)));
                Assert.False(execution.TryRun(engine, () => throw new Xunit.Sdk.XunitException("Concurrent editor code ran."), command => command()));
                Assert.True(execution.IsRunning);
                execution.Interrupt();
                release.Set();
                Assert.IsType<KeyboardInterruptException>(await repl.WaitAsync(TimeSpan.FromSeconds(10)));
                object result = null;
                Assert.True(execution.TryRun(engine, () => result = engine.Execute("42"), command => command()));
                Assert.Equal(42, result);
            }
            finally {
                release.Set();
                execution.Interrupt();
                await repl.WaitAsync(TimeSpan.FromSeconds(10));
                engine.Runtime.Shutdown();
            }
        }

        [Fact]
        public async Task ReplRunWaitsForEditorExecutionWithoutAnAlreadyRunningErrorAsync() {
            var engine = Python.CreateEngine();
            using var execution = new PythonExecution();
            using var entered = new ManualResetEventSlim();
            using var release = new ManualResetEventSlim();
            using var replStarted = new ManualResetEventSlim();
            var editor = Task.Run(() => execution.TryRun(engine, () => {
                entered.Set();
                release.Wait();
                engine.Execute("41");
            }, command => command()));
            Task<object> repl = null;
            try {
                Assert.True(entered.Wait(TimeSpan.FromSeconds(10)));
                repl = Task.Run(() => {
                    replStarted.Set();
                    object result = null;
                    execution.Run(engine, () => result = engine.Execute("42"), command => command());
                    return result;
                });
                Assert.True(replStarted.Wait(TimeSpan.FromSeconds(10)));
                Assert.False(repl.IsCompleted);
                release.Set();
                Assert.True(await editor.WaitAsync(TimeSpan.FromSeconds(10)));
                Assert.Equal(42, await repl.WaitAsync(TimeSpan.FromSeconds(10)));
            }
            finally {
                release.Set();
                execution.Interrupt();
                await editor.WaitAsync(TimeSpan.FromSeconds(10));
                if (repl != null) await repl.WaitAsync(TimeSpan.FromSeconds(10));
                engine.Runtime.Shutdown();
            }
        }

    }
}
