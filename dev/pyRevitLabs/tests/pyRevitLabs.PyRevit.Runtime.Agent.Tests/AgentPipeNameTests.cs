using System.Linq;
using PyRevitLabs.PyRevit.Runtime.Agent;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    [Trait("Environment", "HostFree")]
    [Trait("Level", "Unit")]
    public sealed class AgentPipeNameTests {
        [Fact]
        public void ANameCarriesTheProcessIdAndARandomNonce() {
            var first = AgentPipeName.Create(1234);
            var second = AgentPipeName.Create(1234);

            Assert.StartsWith("pyrevit-agent-1234-", first);
            Assert.Equal("pyrevit-agent-1234-".Length + 32, first.Length);
            Assert.NotEqual(first, second);
            Assert.True(AgentPipeName.IsValid(first));
        }

        [Theory]
        [InlineData("pyrevit-agent-1234")]
        [InlineData("pyrevit-agent-1234-0123456789abcdef0123456789abcdef")]
        public void TheNameWithAndWithoutANonceIsValid(string name) {
            Assert.True(AgentPipeName.IsValid(name));
        }

        [Theory]
        [InlineData(null)]
        [InlineData("")]
        [InlineData("pyrevit-agent-")]
        [InlineData("pyrevit-agent-12-0123")]
        [InlineData("pyrevit-agent-12-0123456789ABCDEF0123456789ABCDEF")]
        [InlineData("pyrevit-agent-12-0123456789abcdef0123456789abcdef\n")]
        [InlineData(@"..\pyrevit-agent-12")]
        [InlineData("other-12")]
        public void OtherNamesAreNotValid(string name) {
            Assert.False(AgentPipeName.IsValid(name));
        }
    }
}
