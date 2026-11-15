using PyRevitLabs.PyRevit.Runtime.Agent;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    [Trait("Environment", "HostFree")]
    [Trait("Level", "Unit")]
    public sealed class AgentRunTimingsTests {
        [Fact]
        public void QueueWaitIsReportedAsAPhaseAndCountsTowardTotal() {
            var timings = new AgentRunTimings(30000);
            timings.Lap("prepare");

            var json = timings.ToJson();

            Assert.Equal(30000, json.Value<double>("queue_wait"));
            Assert.True(json.Value<double>("total") >= 30000);
            Assert.True(timings.TotalMilliseconds >= 30000 + json.Value<double>("prepare") - 0.1);
        }

        [Fact]
        public void RepeatedPhaseAccumulates() {
            var timings = new AgentRunTimings(0);
            timings.Add("guard_release", 2);
            timings.Add("guard_release", 3);

            Assert.Equal(5, timings.ToJson().Value<double>("guard_release"));
        }
    }
}
