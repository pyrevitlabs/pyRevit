using System;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Threading;
using PyRevitLabs.PyRevit.Shell;

namespace pyRevitLabs.PyRevit.Shell.Tests {
    public class ShellDispatcherTests {
        [Fact]
        public async Task RunOnDispatcherReturnsCallbackErrorWithoutUnhandledWpfExceptionAsync() {
            using var ready = new ManualResetEventSlim();
            Dispatcher dispatcher = null;
            Exception unhandled = null;
            var worker = new Thread(() => {
                dispatcher = Dispatcher.CurrentDispatcher;
                dispatcher.UnhandledException += (sender, args) => { unhandled = args.Exception; args.Handled = true; };
                ready.Set();
                Dispatcher.Run();
            }) { IsBackground = true };
            worker.SetApartmentState(ApartmentState.STA);
            worker.Start();
            try {
                Assert.True(ready.Wait(TimeSpan.FromSeconds(10)));
                var error = new InvalidOperationException("Modal callback failure");
                var reported = await Task.Run(() => Record.Exception(() => ShellLauncher.RunOnDispatcher(dispatcher, () => throw error)))
                    .WaitAsync(TimeSpan.FromSeconds(10));
                Assert.Same(error, reported);
                Assert.Null(unhandled);
                var executed = false;
                await Task.Run(() => ShellLauncher.RunOnDispatcher(dispatcher, () => executed = true)).WaitAsync(TimeSpan.FromSeconds(10));
                Assert.True(executed);
            }
            finally {
                dispatcher?.BeginInvokeShutdown(DispatcherPriority.Send);
                Assert.True(worker.Join(TimeSpan.FromSeconds(10)));
            }
        }

        [Fact]
        public async Task RunOnClosedDispatcherReleasesCallerWithoutExecutingAsync() {
            Dispatcher dispatcher = null;
            var worker = new Thread(() => {
                dispatcher = Dispatcher.CurrentDispatcher;
                dispatcher.InvokeShutdown();
            }) { IsBackground = true };
            worker.SetApartmentState(ApartmentState.STA);
            worker.Start();
            Assert.True(worker.Join(TimeSpan.FromSeconds(10)));
            var executed = false;
            var error = await Task.Run(() => Record.Exception(() => ShellLauncher.RunOnDispatcher(dispatcher, () => executed = true)))
                .WaitAsync(TimeSpan.FromSeconds(10));
            Assert.IsType<Microsoft.Scripting.KeyboardInterruptException>(error);
            Assert.False(executed);
        }
    }
}
