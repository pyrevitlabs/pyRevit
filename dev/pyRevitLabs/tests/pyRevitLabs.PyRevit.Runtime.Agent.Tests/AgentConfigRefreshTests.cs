using System;
using System.Threading;
using System.Threading.Tasks;
using PyRevitLabs.PyRevit.Runtime.Agent;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    [Trait("Environment", "HostFree")]
    [Trait("Level", "Integration")]
    public sealed class AgentConfigRefreshTests {
        private static readonly TimeSpan Patience = TimeSpan.FromSeconds(10);

        [Fact]
        public async Task ARequestThatSeesTheNewTimestampWaitsUntilTheConfigIsReloaded() {
            var lastWrite = new DateTime(2026, 1, 1);
            var reloading = new ManualResetEventSlim();
            var finishReload = new ManualResetEventSlim();
            var reloads = 0;
            var refresh = new AgentConfigRefresh(() => "config.ini", _ => lastWrite, () => {
                Interlocked.Increment(ref reloads);
                reloading.Set();
                Assert.True(finishReload.Wait(Patience));
            });
            var first = Task.Run(() => refresh.RefreshIfChanged());
            Assert.True(reloading.Wait(Patience));

            var second = Task.Run(() => refresh.RefreshIfChanged());

            var early = await Task.WhenAny(second, Task.Delay(TimeSpan.FromMilliseconds(300)));
            Assert.NotSame(second, early);
            finishReload.Set();
            var both = Task.WhenAll(first, second);
            Assert.Same(both, await Task.WhenAny(both, Task.Delay(Patience)));
            await both;
            Assert.Equal(1, reloads);
        }

        [Fact]
        public void AFailedReloadIsTriedAgainOnTheNextRequest() {
            var reloads = 0;
            var refresh = new AgentConfigRefresh(() => "config.ini", _ => new DateTime(2026, 1, 1), () => {
                if (Interlocked.Increment(ref reloads) == 1)
                    throw new InvalidOperationException("locked");
            });

            Assert.Throws<InvalidOperationException>(() => refresh.RefreshIfChanged());
            refresh.RefreshIfChanged();
            refresh.RefreshIfChanged();

            Assert.Equal(2, reloads);
        }
    }
}
