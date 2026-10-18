using System;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Scripting;
using PyRevitLabs.PyRevit.Shell;

namespace pyRevitLabs.PyRevit.Shell.Tests {
    [Trait("Environment", "HostFree")]
    [Trait("Level", "Unit")]
    public class ShellExternalEventDispatcherTests {
        [Fact]
        public async Task CancelRemovesPendingCommandAndReleasesWaitAsync() {
            using var dispatcher = new ShellExternalEventDispatcher();
            var executed = false;
            var request = dispatcher.Enqueue(() => executed = true);
            var wait = Task.Run(() => Record.Exception(() => request.Wait(CancellationToken.None, () => dispatcher.Cancel(request))));
            Assert.True(dispatcher.Cancel(request));
            Assert.False(dispatcher.Cancel(request));
            Assert.IsType<KeyboardInterruptException>(await wait.WaitAsync(TimeSpan.FromSeconds(10)));
            dispatcher.ExecutePendingRequests();
            Assert.False(executed);
        }

        [Fact]
        public async Task DisposeCancelsAllPendingCommandsAndRejectsNewWorkAsync() {
            using var dispatcher = new ShellExternalEventDispatcher();
            var executed = 0;
            var first = dispatcher.Enqueue(() => executed++);
            var second = dispatcher.Enqueue(() => executed++);
            var firstWait = Task.Run(() => Record.Exception(() => first.Wait(CancellationToken.None, () => dispatcher.Cancel(first))));
            var secondWait = Task.Run(() => Record.Exception(() => second.Wait(CancellationToken.None, () => dispatcher.Cancel(second))));
            dispatcher.Dispose();
            dispatcher.Dispose();
            Assert.IsType<KeyboardInterruptException>(await firstWait.WaitAsync(TimeSpan.FromSeconds(10)));
            Assert.IsType<KeyboardInterruptException>(await secondWait.WaitAsync(TimeSpan.FromSeconds(10)));
            Assert.Throws<KeyboardInterruptException>(() => dispatcher.Enqueue(() => executed++));
            dispatcher.ExecutePendingRequests();
            Assert.Equal(0, executed);
        }

        [Fact]
        public async Task CancelDoesNotReleaseAnExecutingApiCallbackEarlyAsync() {
            using var dispatcher = new ShellExternalEventDispatcher();
            using var cancellation = new CancellationTokenSource();
            using var executing = new ManualResetEventSlim();
            using var release = new ManualResetEventSlim();
            using var cancelAttempted = new ManualResetEventSlim();
            var request = dispatcher.Enqueue(() => { executing.Set(); release.Wait(); });
            var callback = Task.Run(dispatcher.ExecutePendingRequests);
            try {
                Assert.True(executing.Wait(TimeSpan.FromSeconds(10)));
                Assert.False(dispatcher.Cancel(request));
                cancellation.Cancel();
                var wait = Task.Run(() => request.Wait(cancellation.Token, () => {
                    cancelAttempted.Set();
                    return dispatcher.Cancel(request);
                }));
                Assert.True(cancelAttempted.Wait(TimeSpan.FromSeconds(10)));
                Assert.False(wait.IsCompleted);
                release.Set();
                await callback.WaitAsync(TimeSpan.FromSeconds(10));
                await wait.WaitAsync(TimeSpan.FromSeconds(10));
            }
            finally { release.Set(); await callback.WaitAsync(TimeSpan.FromSeconds(10)); }
        }

        [Fact]
        public void ApiCallbackErrorReachesConsoleWithoutEscapingEventHandler() {
            using var dispatcher = new ShellExternalEventDispatcher();
            var error = new InvalidOperationException("API failure");
            var failed = dispatcher.Enqueue(() => throw error);
            var nextExecuted = false;
            dispatcher.Enqueue(() => nextExecuted = true);
            Assert.Null(Record.Exception(dispatcher.ExecutePendingRequests));
            Assert.Same(error, Record.Exception(() => failed.Wait(CancellationToken.None, () => dispatcher.Cancel(failed))));
            Assert.True(nextExecuted);
        }
    }
}
