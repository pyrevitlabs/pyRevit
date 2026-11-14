using pyRevitLabs.Common;
using pyRevitLabs.Json;
using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    [Trait("Environment", "HostFree")]
    [Trait("Level", "Unit")]
    public sealed class JsonTextTests {
        [Fact]
        public void DateLikeStringsKeepTheirText() {
            var token = JsonText.Parse("{\"a\":\"2024-05-01\",\"b\":[\"2025-06-18T10:00:00Z\"]}");

            Assert.Equal(JTokenType.String, token["a"].Type);
            Assert.Equal("{\"a\":\"2024-05-01\",\"b\":[\"2025-06-18T10:00:00Z\"]}", token.ToString(Formatting.None));
        }

        [Fact]
        public void ScalarsAreAccepted() {
            Assert.Equal("2024-05-01", JsonText.Parse("\"2024-05-01\"").Value<string>());
        }

        [Fact]
        public void RunRequestInputsKeepDateLikeStrings() {
            var request = AgentRunRequest.FromJson(new JObject {
                ["script"] = "x = 1",
                ["inputs"] = new JObject { ["day"] = "2024-05-01T00:00:00.000Z" },
            });

            Assert.Equal("2024-05-01T00:00:00.000Z", request.ToJson()["inputs"]["day"].Value<string>());
        }

        [Theory]
        [InlineData("not json")]
        [InlineData("{\"a\":1} trailing")]
        public void TextThatIsNotOneValueIsRejected(string json) {
            Assert.ThrowsAny<JsonException>(() => JsonText.Parse(json));
        }
    }
}
