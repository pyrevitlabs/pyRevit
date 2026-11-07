namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    [Trait("Environment", "HostFree")]
    [Trait("Level", "Unit")]
    public sealed class AgentDocumentBindingTests {
        private const string Path = @"C:\models\second.rvt";

        [Theory]
        [InlineData(null)]
        [InlineData("")]
        [InlineData("  ")]
        public void NoRequestedDocumentMatchesAnyActiveDocument(string requested) {
            Assert.True(AgentDocumentBinding.Matches(requested, "second", Path));
        }

        [Fact]
        public void TheActiveTitleMatchesIgnoringCase() {
            Assert.True(AgentDocumentBinding.Matches("SECOND", "second", Path));
        }

        [Fact]
        public void TheActivePathMatchesIgnoringCase() {
            Assert.True(AgentDocumentBinding.Matches(@"c:\MODELS\second.rvt", "second", Path));
        }

        [Fact]
        public void AnotherDocumentDoesNotMatch() {
            Assert.False(AgentDocumentBinding.Matches("Snowdon Towers Sample Architectural", "second", Path));
        }

        [Fact]
        public void AnUnsavedActiveDocumentMatchesByTitleOnly() {
            Assert.True(AgentDocumentBinding.Matches("Project1", "Project1", ""));
            Assert.False(AgentDocumentBinding.Matches(Path, "Project1", ""));
        }
    }
}
