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
        public async Task DisposeProductionHostEndsWorkersAndShutsDownRuntimeAsync() {
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
                await dispatcher.InvokeAsync(productionHost.Dispose);
                await Task.Run(() => {
                    Assert.True(consoleWorker.Join(TimeSpan.FromSeconds(10)));
                    Assert.True(dispatcherWorker.Join(TimeSpan.FromSeconds(10)));
                    Assert.True(completionWorker.Join(TimeSpan.FromSeconds(10)));
                }).WaitAsync(TimeSpan.FromSeconds(35));
                Assert.True(await runtimeShutdown.Task.WaitAsync(TimeSpan.FromSeconds(10)));
                Assert.False(consoleWorker.IsAlive);
                Assert.False(dispatcherWorker.IsAlive);
                Assert.False(completionWorker.IsAlive);
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
