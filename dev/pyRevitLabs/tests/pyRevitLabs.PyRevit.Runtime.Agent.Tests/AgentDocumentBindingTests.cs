using pyRevitLabs.Json.Linq;

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
        public void AnUnsavedActiveDocumentMatchesByTitleOnly() {
            Assert.True(AgentDocumentBinding.Matches("Project1", "Project1", ""));
            Assert.False(AgentDocumentBinding.Matches(Path, "Project1", ""));
        }

        [Fact]
        public void AMalformedPathDoesNotThrow() {
            Assert.False(AgentDocumentBinding.Matches("C:\\bad|path\\x.rvt", "second", Path));
        }

        [Fact]
        public void ParseReturnsNullWhenAbsentOrNull() {
            Assert.Null(AgentDocumentBinding.Parse(null));
            Assert.Null(AgentDocumentBinding.Parse(JValue.CreateNull()));
        }

        [Fact]
        public void ParseKeepsAStringUnchanged() {
            Assert.Equal("  second ", AgentDocumentBinding.Parse(new JValue("  second ")));
        }

        [Fact]
        public void ATitleWithSurroundingSpacesMatchesItself() {
            Assert.True(AgentDocumentBinding.Matches(" Tower", " Tower", Path));
        }

        [Theory]
        [InlineData("")]
        [InlineData("   ")]
        public void ParseRejectsABlankString(string value) {
            var error = Assert.Throws<AgentException>(() => AgentDocumentBinding.Parse(new JValue(value)));
            Assert.Equal("invalid_params", error.Code);
        }

        [Fact]
        public void ParseRejectsANonString() {
            var error = Assert.Throws<AgentException>(() => AgentDocumentBinding.Parse(new JObject { ["title"] = "second" }));
            Assert.Equal("invalid_params", error.Code);
            Assert.Throws<AgentException>(() => AgentDocumentBinding.Parse(new JValue(3)));
        }

        [Fact]
        public void TheRefusalNamesBothDocumentsAndIsANotRun() {
            var refusal = AgentDocumentBinding.Refusal("first", "second");

            Assert.Equal("document_changed", refusal.Code);
            Assert.Contains("'first'", refusal.Message);
            Assert.Contains("'second'", refusal.Message);
            Assert.Equal("not_run", refusal.Details.Value<string>("outcome"));
        }

        [Fact]
        public void TheRefusalSaysWhenNoDocumentIsActive() {
            var refusal = AgentDocumentBinding.Refusal("first", null);

            Assert.Contains("no active document", refusal.Message);
            Assert.Equal("not_run", refusal.Details.Value<string>("outcome"));
        }
    }
}
