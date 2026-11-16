using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    [Trait("Environment", "HostFree")]
    [Trait("Level", "Unit")]
    /// <summary>
    /// Covers reading the build commit from an assembly version and flagging binaries that differ from the clone.
    /// </summary>
    public sealed class AgentBinaryCommitTests {
        private const string Version = "7.0.0.26278+2233.d85e4ae1234567890abcdef1234567890abcdef0";

        /// <summary>
        /// The commit is the short revision that follows the build number.
        /// </summary>
        [Fact]
        public void TheCommitIsTheRevisionAfterTheBuildNumber() {
            Assert.Equal("d85e4ae", AgentBinaryCommit.Parse(Version));
        }

        /// <summary>
        /// A version without a hexadecimal revision yields no commit.
        /// </summary>
        [Theory]
        [InlineData(null)]
        [InlineData("7.0.0.26278")]
        [InlineData("7.0.0.26278+2233")]
        [InlineData("7.0.0.26278+2233.notahexrevision")]
        public void AVersionWithoutARevisionHasNoCommit(string version) {
            Assert.Null(AgentBinaryCommit.Parse(version));
        }

        /// <summary>
        /// A clone commit different from the build commit flags the binaries as stale with a rebuild hint.
        /// </summary>
        [Fact]
        public void ADifferentCloneCommitMarksTheBinariesStale() {
            var identity = new JObject();
            AgentBinaryCommit.Describe(identity, Version, "149eb02");
            Assert.Equal("d85e4ae", identity.Value<string>("bin_commit"));
            Assert.True(identity.Value<bool>("bin_stale"));
            Assert.Contains("rebuild", identity.Value<string>("bin_hint"));
        }

        /// <summary>
        /// The same commit, in any letter case, is not flagged.
        /// </summary>
        [Fact]
        public void TheSameCloneCommitIsNotStale() {
            var identity = new JObject();
            AgentBinaryCommit.Describe(identity, Version, "D85E4AE");
            Assert.Equal("d85e4ae", identity.Value<string>("bin_commit"));
            Assert.Null(identity["bin_stale"]);
        }

        /// <summary>
        /// An unknown clone commit reports the build commit without flagging.
        /// </summary>
        [Fact]
        public void AnUnknownCloneCommitIsNotFlagged() {
            var identity = new JObject();
            AgentBinaryCommit.Describe(identity, Version, null);
            Assert.Equal("d85e4ae", identity.Value<string>("bin_commit"));
            Assert.Null(identity["bin_stale"]);
        }

        /// <summary>
        /// A version with no revision adds no fields.
        /// </summary>
        [Fact]
        public void UnknownBinariesAddNothing() {
            var identity = new JObject();
            AgentBinaryCommit.Describe(identity, "7.0.0.26278", "149eb02");
            Assert.Empty(identity);
        }
    }
}
