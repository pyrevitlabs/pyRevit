namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    [Trait("Environment", "HostFree")]
    [Trait("Level", "Unit")]
    public sealed class AgentDocumentBindingTests {
        private const string Path = @"C:\models\second.rvt";

        private static readonly (string Key, string Title, string Path)[] Open = {
            ("doc-1", "Tower", @"C:\models\Tower.rvt"),
            ("doc-2", "second", Path),
            ("doc-3", "Project1", ""),
            ("doc-4", "Family1", ""),
            ("doc-5", "Family1", ""),
        };

        [Theory]
        [InlineData(null)]
        [InlineData("")]
        [InlineData("  ")]
        public void ABlankValueMatchesNothing(string requested) {
            Assert.False(AgentDocumentBinding.Matches(requested, "second", Path));
        }

        [Fact]
        public void ATitleMatchesIgnoringCase() {
            Assert.True(AgentDocumentBinding.Matches("SECOND", "second", Path));
        }

        [Theory]
        [InlineData(@"c:\MODELS\second.rvt")]
        [InlineData("C:/models/second.rvt")]
        [InlineData(@"C:\models\.\second.rvt")]
        [InlineData(@"C:\models\other\..\second.rvt")]
        public void ThePathMatchesAfterNormalisingIgnoringCase(string requested) {
            Assert.True(AgentDocumentBinding.Matches(requested, "second", Path));
        }

        [Fact]
        public void ANetworkPathMatchesItself() {
            const string unc = @"\\server\share\models\second.rvt";
            Assert.True(AgentDocumentBinding.Matches(unc, "second", unc));
            Assert.True(AgentDocumentBinding.Matches(unc + @"\", "second", unc));
        }

        [Fact]
        public void AnotherDocumentDoesNotMatch() {
            Assert.False(AgentDocumentBinding.Matches("Snowdon Towers Sample Architectural", "second", Path));
        }

        [Fact]
        public void APathNeverMatchesATitle() {
            Assert.False(AgentDocumentBinding.Matches(@"C:\other\second.rvt", "second", Path));
            Assert.False(AgentDocumentBinding.Matches(@"C:\other\Project1", "Project1", ""));
        }

        [Fact]
        public void AnUnsavedDocumentMatchesByTitleOnly() {
            Assert.True(AgentDocumentBinding.Matches("Project1", "Project1", ""));
            Assert.False(AgentDocumentBinding.Matches(Path, "Project1", ""));
        }

        [Fact]
        public void AMalformedPathDoesNotThrow() {
            Assert.False(AgentDocumentBinding.Matches("C:\\bad|path\\x.rvt", "second", Path));
        }

        [Fact]
        public void ATitleWithSurroundingSpacesMatchesItself() {
            Assert.True(AgentDocumentBinding.Matches(" Tower", " Tower", Path));
        }

        [Theory]
        [InlineData("tower", "doc-1")]
        [InlineData(@"C:\models\second.rvt", "doc-2")]
        [InlineData("Project1", "doc-3")]
        public void TheOneDocumentATitleOrPathNamesIsFound(string requested, string key) {
            Assert.Equal(key, AgentDocumentBinding.Named(requested, Open)?.Key);
        }

        [Theory]
        [InlineData("Family1")]
        [InlineData("doc-9")]
        [InlineData(@"C:\models\gone.rvt")]
        public void ATitleSeveralDocumentsShareOrAValueNoneHasNamesNone(string requested) {
            Assert.Null(AgentDocumentBinding.Named(requested, Open));
        }
    }
}
