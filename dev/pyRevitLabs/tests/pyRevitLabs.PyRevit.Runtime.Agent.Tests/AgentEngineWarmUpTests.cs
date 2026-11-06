using PyRevitLabs.PyRevit.Runtime.Agent;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    [Trait("Environment", "HostFree")]
    [Trait("Level", "Unit")]
    public sealed class AgentEngineWarmUpTests {
        [Fact]
        public void LoadsBeforeTheFirstIdlingScheduleOneWarmUp() {
            var warmUp = new AgentEngineWarmUp();

            Assert.True(warmUp.Schedule(hasUserInterface: true));
            Assert.False(warmUp.Schedule(hasUserInterface: true));
        }

        [Fact]
        public void ALoadAfterTheWarmUpRanSchedulesAnother() {
            var warmUp = new AgentEngineWarmUp();
            warmUp.Schedule(hasUserInterface: true);

            Assert.True(warmUp.TakeScheduled());
            Assert.True(warmUp.Schedule(hasUserInterface: true));
        }

        [Fact]
        public void IdlingWithoutAScheduledWarmUpTakesNothing() {
            var warmUp = new AgentEngineWarmUp();

            Assert.False(warmUp.TakeScheduled());
            warmUp.Schedule(hasUserInterface: true);
            warmUp.TakeScheduled();
            Assert.False(warmUp.TakeScheduled());
        }

        [Fact]
        public void RevitWithoutAUserInterfaceIsNotWarmed() {
            var warmUp = new AgentEngineWarmUp();

            Assert.False(warmUp.Schedule(hasUserInterface: false));
            Assert.False(warmUp.TakeScheduled());
        }

        [Theory]
        [InlineData(true, true, true)]
        [InlineData(false, true, false)]
        [InlineData(true, false, false)]
        [InlineData(false, false, false)]
        public void WarmsOnlyARunningHostWhoseDefaultEngineIsIronPython(
            bool hostRunning, bool defaultEngineIsIronPython, bool expected) {
            Assert.Equal(expected, AgentEngineWarmUp.ShouldWarm(hostRunning, defaultEngineIsIronPython));
        }
    }
}
