using System;
using System.Reflection;
using System.Threading;
using System.Threading.Tasks;
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

        static async Task DisposeHostAsync(bool runStatement) {
            using var statementStarted = new ManualResetEventSlim();
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
                            var onShutdown = new Action(() => runtimeShutdown.TrySetResult(true));
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
                if (runStatement) {
                    await dispatcher.InvokeAsync(() => {
                        productionHost.Console.ScriptScope.SetVariable("_statement_started", new Action(statementStarted.Set));
                        productionHost.Console.RunStatements("_statement_started()\nimport time\nwhile True:\n    time.sleep(0.05)\n");
                    });
                    Assert.True(await Task.Run(() => statementStarted.Wait(TimeSpan.FromSeconds(15))));
                    Assert.True(execution.IsRunning);
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
                });
                await Task.Run(() => {
                    Assert.True(consoleWorker.Join(TimeSpan.FromSeconds(10)));
                    Assert.True(dispatcherWorker.Join(TimeSpan.FromSeconds(10)));
                    Assert.True(completionWorker.Join(TimeSpan.FromSeconds(10)));
                }).WaitAsync(TimeSpan.FromSeconds(35));
                Assert.True(await runtimeShutdown.Task.WaitAsync(TimeSpan.FromSeconds(10)));
                Assert.False(consoleWorker.IsAlive);
                Assert.False(dispatcherWorker.IsAlive);
                Assert.False(completionWorker.IsAlive);
                Assert.False(execution.IsRunning);
                await dispatcher.InvokeAsync(() => {
                    productionHost.Editor.ShowCompletionWindow();
                    productionHost.Editor.UpdateCompletionDescription();
                });
                Assert.Null(unhandled);
            }
            finally {
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
