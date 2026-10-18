using System;
using System.Reflection;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;
using ICSharpCode.AvalonEdit;
using IronPython.Hosting;
using PythonConsoleControl;

namespace pyRevitLabs.PyRevit.Shell.Tests {
    public class PythonConsoleHostLifecycleTests {
        [Fact]
        public Task DisposeProductionHostEndsWorkersAndShutsDownRuntimeAsync() {
            return DisposeHostAsync(false);
        }

        [Fact]
        public Task DisposeWhileStatementRunsDoesNotRaiseUnhandledAndWorkersExitAsync() {
            return DisposeHostAsync(true);
        }

        [Fact]
        public Task DisposeDuringManagedCallShutsDownRuntimeAfterJoinTimeoutAsync() {
            return DisposeHostAsync(true, true);
        }

        [Fact]
        public async Task StopWindowThresholdCompletionCancellationAndReuseAsync() {
            using var stopWindow = new PythonStatementStopWindow();
            var worker = GetWorker(stopWindow, "thread");
            var dispatcherField = typeof(PythonStatementStopWindow).GetField("dispatcher", BindingFlags.Instance | BindingFlags.NonPublic);
            var windowField = typeof(PythonStatementStopWindow).GetField("window", BindingFlags.Instance | BindingFlags.NonPublic);
            var stopDispatcher = Assert.IsType<Dispatcher>(dispatcherField.GetValue(stopWindow));
            async Task<bool> VisibleAsync() {
                return await stopDispatcher.InvokeAsync(() => windowField.GetValue(stopWindow) != null);
            }
            for (var statement = 0; statement < 10; statement++) {
                using var cancellation = new CancellationTokenSource();
                stopWindow.Begin(cancellation.Token, cancellation.Cancel);
                await Task.Delay(100);
                Assert.False(await VisibleAsync());
                stopWindow.End();
                Assert.False(await VisibleAsync());
                Assert.Same(worker, GetWorker(stopWindow, "thread"));
            }
            using var activeCancellation = new CancellationTokenSource();
            stopWindow.Begin(activeCancellation.Token, activeCancellation.Cancel);
            await Task.Delay(1300);
            Assert.True(await VisibleAsync());
            await stopDispatcher.InvokeAsync(stopWindow.RequestStop);
            Assert.True(activeCancellation.IsCancellationRequested);
            Assert.False(await VisibleAsync());
            stopWindow.End();
            using var completedCancellation = new CancellationTokenSource();
            stopWindow.Begin(completedCancellation.Token, completedCancellation.Cancel);
            await Task.Delay(1300);
            Assert.True(await VisibleAsync());
            stopWindow.End();
            Assert.False(await VisibleAsync());
            Assert.False(completedCancellation.IsCancellationRequested);
            stopWindow.Begin(completedCancellation.Token, completedCancellation.Cancel);
            await Task.Delay(1300);
            Assert.True(await VisibleAsync());
            stopWindow.Dispose();
            Assert.True(await Task.Run(() => stopWindow.WaitForExit(TimeSpan.FromSeconds(2))));
            Assert.False(worker.IsAlive);
            stopWindow.End();
            stopWindow.Begin(CancellationToken.None, () => { });
            Assert.False(worker.IsAlive);
        }

        [Fact]
        public async Task StaleStopWindowCannotCancelFollowingStatementAsync() {
            using var stopWindow = new PythonStatementStopWindow();
            using var firstCancellation = new CancellationTokenSource();
            using var secondCancellation = new CancellationTokenSource();
            var dispatcherField = typeof(PythonStatementStopWindow).GetField("dispatcher", BindingFlags.Instance | BindingFlags.NonPublic);
            var windowField = typeof(PythonStatementStopWindow).GetField("window", BindingFlags.Instance | BindingFlags.NonPublic);
            var stopDispatcher = Assert.IsType<Dispatcher>(dispatcherField.GetValue(stopWindow));
            try {
                stopWindow.Begin(firstCancellation.Token, firstCancellation.Cancel);
                await Task.Delay(1300);
                await stopDispatcher.InvokeAsync(() => {
                    var staleWindow = Assert.IsType<Window>(windowField.GetValue(stopWindow));
                    var staleButton = Assert.IsType<Button>(staleWindow.Content);
                    stopWindow.End();
                    stopWindow.Begin(secondCancellation.Token, secondCancellation.Cancel);
                    staleButton.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
                    Assert.False(secondCancellation.IsCancellationRequested);
                    staleWindow.Close();
                    Assert.False(secondCancellation.IsCancellationRequested);
                });
                await Task.Delay(1300);
                await stopDispatcher.InvokeAsync(() => {
                    var currentWindow = Assert.IsType<Window>(windowField.GetValue(stopWindow));
                    var currentButton = Assert.IsType<Button>(currentWindow.Content);
                    currentButton.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
                });
                Assert.False(firstCancellation.IsCancellationRequested);
                Assert.True(secondCancellation.IsCancellationRequested);
            }
            finally {
                stopWindow.Dispose();
                Assert.True(await Task.Run(() => stopWindow.WaitForExit(TimeSpan.FromSeconds(2))));
            }
        }

        [Fact]
        public async Task DisposeDoesNotWaitForBlockedStopDispatcherAsync() {
            using var stopWindow = new PythonStatementStopWindow();
            using var enteredDispatcher = new ManualResetEventSlim();
            using var releaseDispatcher = new ManualResetEventSlim();
            var dispatcherField = typeof(PythonStatementStopWindow).GetField("dispatcher", BindingFlags.Instance | BindingFlags.NonPublic);
            var stopDispatcher = Assert.IsType<Dispatcher>(dispatcherField.GetValue(stopWindow));
            _ = stopDispatcher.BeginInvoke(new Action(() => {
                enteredDispatcher.Set();
                releaseDispatcher.Wait();
            }));
            try {
                Assert.True(await Task.Run(() => enteredDispatcher.Wait(TimeSpan.FromSeconds(10))));
                await Task.Run(stopWindow.Dispose).WaitAsync(TimeSpan.FromSeconds(1));
                Assert.True(GetWorker(stopWindow, "thread").IsAlive);
            }
            finally {
                releaseDispatcher.Set();
                stopWindow.Dispose();
                Assert.True(await Task.Run(() => stopWindow.WaitForExit(TimeSpan.FromSeconds(2))));
            }
        }

        static async Task DisposeHostAsync(bool runStatement, bool blockManagedCall = false) {
            using var statementStarted = new ManualResetEventSlim();
            using var releaseStatement = new ManualResetEventSlim();
            var ready = new TaskCompletionSource<PythonConsoleHost>(TaskCreationOptions.RunContinuationsAsynchronously);
            var runtimeShutdown = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
            Dispatcher dispatcher = null;
            PythonConsoleHost host = null;
            Exception unhandled = null;
            var uiThread = new Thread(() => {
                try {
                    dispatcher = Dispatcher.CurrentDispatcher;
                    dispatcher.UnhandledException += (sender, args) => { unhandled = args.Exception; args.Handled = true; };
                    host = new PythonConsoleHost(new PythonTextEditor(new TextEditor()));
                    host.WhenConsoleCreated(created => {
                        try {
                            var sys = created.Engine.GetSysModule();
                            var onShutdown = new Action(() => {
                                if (!blockManagedCall || releaseStatement.IsSet) runtimeShutdown.TrySetResult(true);
                            });
                            sys.SetVariable("exitfunc", onShutdown);
                            sys.SetVariable("_exitfunc", onShutdown);
                            ready.TrySetResult(created);
                        }
                        catch (Exception error) { ready.TrySetException(error); }
                    });
                    host.Run();
                    Dispatcher.Run();
                }
                catch (Exception error) { ready.TrySetException(error); }
            }) { IsBackground = true };
            uiThread.SetApartmentState(ApartmentState.STA);
            uiThread.Start();
            try {
                var productionHost = await ready.Task.WaitAsync(TimeSpan.FromSeconds(15));
                var consoleWorker = GetWorker(productionHost, "thread");
                var dispatcherWorker = GetWorker(productionHost.Console, "dispatcherThread");
                var completionWorker = GetWorker(productionHost.Editor, "completionThread");
                Assert.True(consoleWorker.IsAlive);
                Assert.True(dispatcherWorker.IsAlive);
                Assert.True(completionWorker.IsAlive);
                var executionField = typeof(PythonConsole).GetField("execution", BindingFlags.Instance | BindingFlags.NonPublic);
                Assert.NotNull(executionField);
                var execution = Assert.IsType<PythonExecution>(executionField.GetValue(productionHost.Console));
                var stopWorker = GetWorker(execution.StopWindow, "thread");
                if (runStatement) {
                    await dispatcher.InvokeAsync(() => {
                        productionHost.Console.ScriptScope.SetVariable("_statement_started", new Action(() => {
                            statementStarted.Set();
                            if (blockManagedCall) releaseStatement.Wait();
                        }));
                        productionHost.Console.RunStatements(blockManagedCall
                            ? "_statement_started()\n"
                            : "_statement_started()\nimport time\nwhile True:\n    time.sleep(0.05)\n");
                    });
                    Assert.True(await Task.Run(() => statementStarted.Wait(TimeSpan.FromSeconds(15))));
                    Assert.True(execution.IsRunning);
                    await Task.Delay(1300);
                    var stopDispatcherField = typeof(PythonStatementStopWindow).GetField("dispatcher", BindingFlags.Instance | BindingFlags.NonPublic);
                    var stopDispatcher = Assert.IsType<Dispatcher>(stopDispatcherField.GetValue(execution.StopWindow));
                    await stopDispatcher.InvokeAsync(() => {
                        var windowField = typeof(PythonStatementStopWindow).GetField("window", BindingFlags.Instance | BindingFlags.NonPublic);
                        Assert.NotNull(windowField.GetValue(execution.StopWindow));
                    });
                }
                await dispatcher.InvokeAsync(() => {
                    var popup = new PythonConsoleCompletionWindow(productionHost.Editor.textArea, productionHost.Editor);
                    var popupField = typeof(PythonTextEditor).GetField("completionWindow", BindingFlags.Instance | BindingFlags.NonPublic);
                    Assert.NotNull(popupField);
                    popupField.SetValue(productionHost.Editor, popup);
                    var timerField = typeof(PythonConsoleCompletionWindow).GetField("updateDescription", BindingFlags.Instance | BindingFlags.NonPublic);
                    Assert.NotNull(timerField);
                    var completionTimer = Assert.IsType<DispatcherTimer>(timerField.GetValue(popup));
                    completionTimer.Interval = TimeSpan.FromMilliseconds(300);
                    completionTimer.Start();
                    productionHost.Dispose();
                    Assert.False(completionTimer.IsEnabled);
                }).Task.WaitAsync(TimeSpan.FromSeconds(1));
                if (blockManagedCall) {
                    await Task.Delay(TimeSpan.FromSeconds(15));
                    Assert.True(dispatcherWorker.IsAlive);
                    Assert.False(runtimeShutdown.Task.IsCompleted);
                    releaseStatement.Set();
                }
                await productionHost.CleanupCompleted.WaitAsync(TimeSpan.FromSeconds(35));
                await Task.Run(() => {
                    Assert.True(consoleWorker.Join(TimeSpan.FromSeconds(10)));
                    Assert.True(dispatcherWorker.Join(TimeSpan.FromSeconds(10)));
                    Assert.True(completionWorker.Join(TimeSpan.FromSeconds(10)));
                    Assert.True(stopWorker.Join(TimeSpan.FromSeconds(10)));
                }).WaitAsync(TimeSpan.FromSeconds(45));
                Assert.True(await runtimeShutdown.Task.WaitAsync(TimeSpan.FromSeconds(10)));
                Assert.False(consoleWorker.IsAlive);
                Assert.False(dispatcherWorker.IsAlive);
                Assert.False(completionWorker.IsAlive);
                Assert.False(stopWorker.IsAlive);
                Assert.False(execution.IsRunning);
                await dispatcher.InvokeAsync(() => {
                    productionHost.Editor.ShowCompletionWindow();
                    productionHost.Editor.UpdateCompletionDescription();
                });
                Assert.Null(unhandled);
            }
            finally {
                releaseStatement.Set();
                if (host != null && dispatcher != null && !dispatcher.HasShutdownStarted)
                    await dispatcher.InvokeAsync(host.Dispose);
                dispatcher?.BeginInvokeShutdown(DispatcherPriority.Send);
                Assert.True(uiThread.Join(TimeSpan.FromSeconds(10)));
            }
        }

        static Thread GetWorker(object owner, string fieldName) {
            var field = owner.GetType().GetField(fieldName, BindingFlags.Instance | BindingFlags.NonPublic);
            Assert.NotNull(field);
            return Assert.IsType<Thread>(field.GetValue(owner));
        }
    }
}
