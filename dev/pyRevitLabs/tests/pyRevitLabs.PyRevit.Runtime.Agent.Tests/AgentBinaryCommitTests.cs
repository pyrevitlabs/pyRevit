using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    [Trait("Environment", "HostFree")]
    [Trait("Level", "Unit")]
    public sealed class AgentBinaryCommitTests {
        private const string Version = "7.0.0.26278+2233.d85e4ae1234567890abcdef1234567890abcdef0";

        [Fact]
        public void TheCommitIsTheRevisionAfterTheBuildNumber() {
            Assert.Equal("d85e4ae", AgentBinaryCommit.Parse(Version));
        }

        [Theory]
        [InlineData(null)]
        [InlineData("7.0.0.26278")]
        [InlineData("7.0.0.26278+2233")]
        [InlineData("7.0.0.26278+2233.notahexrevision")]
        public void AVersionWithoutARevisionHasNoCommit(string version) {
            Assert.Null(AgentBinaryCommit.Parse(version));
        }

        [Fact]
        public void ADifferentCloneCommitMarksTheBinariesStale() {
            var identity = new JObject();
            AgentBinaryCommit.Describe(identity, Version, "149eb02");
            Assert.Equal("d85e4ae", identity.Value<string>("bin_commit"));
            Assert.True(identity.Value<bool>("bin_stale"));
            Assert.Contains("rebuild", identity.Value<string>("bin_hint"));
        }

        [Fact]
        public void TheSameCloneCommitIsNotStale() {
            var identity = new JObject();
            AgentBinaryCommit.Describe(identity, Version, "D85E4AE");
            Assert.Equal("d85e4ae", identity.Value<string>("bin_commit"));
            Assert.Null(identity["bin_stale"]);
        }

        [Fact]
        public void AnUnknownCloneCommitIsNotFlagged() {
            var identity = new JObject();
            AgentBinaryCommit.Describe(identity, Version, null);
            Assert.Equal("d85e4ae", identity.Value<string>("bin_commit"));
            Assert.Null(identity["bin_stale"]);
        }

        [Fact]
        public void UnknownBinariesAddNothing() {
            var identity = new JObject();
            AgentBinaryCommit.Describe(identity, "7.0.0.26278", "149eb02");
            Assert.Empty(identity);
        }
    }
}
