using PyRevitLabs.PyRevit.Runtime.Agent;
using pyRevitLabs.Json;
using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    [Trait("Environment", "HostFree")]
    [Trait("Level", "Unit")]
    public sealed class AgentRequestLineTests {
        [Fact]
        public void DateLikeStringsKeepTheirText() {
            var request = AgentRequestLine.Parse(
                "{\"id\":\"2025-06-18T00:00:00Z\",\"params\":{\"title\":\"2025-06-18T00:00:00+02:00\"}}");

            Assert.Equal(JTokenType.String, request["id"].Type);
            Assert.Equal("2025-06-18T00:00:00Z", request["id"].Value<string>());
            Assert.Equal("2025-06-18T00:00:00+02:00", request["params"]["title"].Value<string>());
        }

        [Theory]
        [InlineData("not json")]
        [InlineData("{\"id\":1} trailing")]
        [InlineData("[1]")]
        public void ALineThatIsNotOneJsonObjectIsRejected(string line) {
            Assert.ThrowsAny<JsonException>(() => AgentRequestLine.Parse(line));
        }
    }
}
