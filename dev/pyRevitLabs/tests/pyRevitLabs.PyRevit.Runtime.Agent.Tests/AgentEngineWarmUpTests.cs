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

            Assert.True(warmUp.OnRequest(method));
        }

        [Fact]
        public void LaterRequestsQueueNothing() {
            var warmUp = new AgentEngineWarmUp();
            warmUp.OnRequest("ping");

            Assert.False(warmUp.OnRequest("ping"));
            Assert.False(warmUp.OnRequest("get_context"));
        }

        [Fact]
        public void AFirstRunQueuesNothingAndUsesUpTheSessionLoad() {
            var warmUp = new AgentEngineWarmUp();

            Assert.False(warmUp.OnRequest("run"));
            Assert.False(warmUp.OnRequest("ping"));
        }

        [Fact]
        public void AReloadLetsTheNextRequestWarmAgain() {
            var warmUp = new AgentEngineWarmUp();
            warmUp.OnRequest("ping");

            warmUp.Reset();

            Assert.True(warmUp.OnRequest("get_context"));
        }

        [Fact]
        public void ConcurrentFirstRequestsQueueOneWarmUp() {
            var warmUp = new AgentEngineWarmUp();
            var queued = 0;

            System.Threading.Tasks.Parallel.For(0, 64, _ => {
                if (warmUp.OnRequest("ping"))
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
