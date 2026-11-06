using PyRevitLabs.PyRevit.Runtime.Agent;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    [Trait("Environment", "HostFree")]
    [Trait("Level", "Unit")]
    public sealed class AgentEngineWarmUpTests {
        [Theory]
        [InlineData("ping")]
        [InlineData("get_context")]
        [InlineData("lookup_api")]
        [InlineData("no_such_method")]
        public void TheFirstRequestOfASessionLoadQueuesTheWarmUp(string method) {
            var warmUp = new AgentEngineWarmUp();

            Assert.True(warmUp.OnRequest(method, warmUp.Load));
        }

        [Fact]
        public void LaterRequestsQueueNothing() {
            var warmUp = new AgentEngineWarmUp();
            warmUp.OnRequest("ping", warmUp.Load);

            Assert.False(warmUp.OnRequest("ping", warmUp.Load));
            Assert.False(warmUp.OnRequest("get_context", warmUp.Load));
        }

        [Fact]
        public void AFirstRunQueuesNothingAndUsesUpTheSessionLoad() {
            var warmUp = new AgentEngineWarmUp();

            Assert.False(warmUp.OnRequest("run", warmUp.Load));
            Assert.False(warmUp.OnRequest("ping", warmUp.Load));
        }

        [Fact]
        public void AReloadLetsTheNextRequestWarmAgain() {
            var warmUp = new AgentEngineWarmUp();
            warmUp.OnRequest("ping", warmUp.Load);

            warmUp.Reset();

            Assert.True(warmUp.OnRequest("get_context", warmUp.Load));
        }

        [Fact]
        public void ARequestDuringWhichPyRevitReloadedLeavesTheNewLoadUncontacted() {
            var warmUp = new AgentEngineWarmUp();
            var loadAtStart = warmUp.Load;

            warmUp.Reset();

            Assert.False(warmUp.OnRequest("run", loadAtStart));
            Assert.True(warmUp.OnRequest("ping", warmUp.Load));
        }

        [Fact]
        public void ARequestThatStartedBeforeAReloadDoesNotWarmTheNewLoad() {
            var warmUp = new AgentEngineWarmUp();
            var loadAtStart = warmUp.Load;

            warmUp.Reset();

            Assert.False(warmUp.OnRequest("ping", loadAtStart));
            Assert.True(warmUp.OnRequest("get_context", warmUp.Load));
        }

        [Fact]
        public void ConcurrentFirstRequestsQueueOneWarmUp() {
            var warmUp = new AgentEngineWarmUp();
            var queued = 0;

            System.Threading.Tasks.Parallel.For(0, 64, _ => {
                if (warmUp.OnRequest("ping", warmUp.Load))
                    System.Threading.Interlocked.Increment(ref queued);
            });

            Assert.Equal(1, queued);
        }

        [Theory]
        [InlineData(true, true, false, true)]
        [InlineData(false, true, false, false)]
        [InlineData(true, false, false, false)]
        [InlineData(true, true, true, false)]
        public void WarmsOnlyAnEnabledIronPythonDefaultWithNoCachedEngine(
            bool agentEnabled, bool defaultEngineIsIronPython, bool engineCached, bool expected) {
            Assert.Equal(expected, AgentEngineWarmUp.ShouldWarm(agentEnabled, defaultEngineIsIronPython, engineCached));
        }
    }
}
