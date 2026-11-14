using pyRevitLabs.Common;
using pyRevitLabs.Json;
using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    [Trait("Environment", "HostFree")]
    [Trait("Level", "Unit")]
    public sealed class JsonTextTests {
        /// <summary>
        /// A script result with a date-like or offset timestamp string comes back as written.
        /// </summary>
        [Theory]
        [InlineData("2024-05-01")]
        [InlineData("2024-05-01T10:00:00+02:00")]
        [InlineData("2024-05-01T10:00:00.1234567+02:00")]
        [InlineData("2024-05-01T10:00:00.123Z")]
        [InlineData("2025-06-18T10:00:00Z")]
        public void DateLikeStringsKeepTheirText(string text) {
            var result = JsonText.Parse("{\"d\":\"" + text + "\",\"list\":[\"" + text + "\"]}");

            Assert.Equal(JTokenType.String, result["d"].Type);
            Assert.Equal("{\"d\":\"" + text + "\",\"list\":[\"" + text + "\"]}", result.ToString(Formatting.None));
        }

        [Fact]
        public void ScalarsAreAccepted() {
            Assert.Equal("2024-05-01", JsonText.Parse("\"2024-05-01\"").Value<string>());
        }

        /// <summary>
        /// Inputs with date-like and offset timestamp strings reach the run record as written.
        /// </summary>
        [Theory]
        [InlineData("2024-05-01")]
        [InlineData("2024-05-01T10:00:00+02:00")]
        [InlineData("2024-05-01T10:00:00.1234567+02:00")]
        [InlineData("2024-05-01T10:00:00.50Z")]
        [InlineData("2024-05-01T00:00:00.000Z")]
        public void RunRequestInputsKeepDateLikeStrings(string text) {
            var request = AgentRunRequest.FromJson(new JObject {
                ["script"] = "x = 1",
                ["inputs"] = new JObject { ["d"] = text, ["list"] = new JArray(text) },
            });

            var record = request.ToJson().ToString(Formatting.None);

            Assert.Contains("\"d\":\"" + text + "\"", record);
            Assert.Contains("\"list\":[\"" + text + "\"]", record);
        }

        [Theory]
        [InlineData("not json")]
        [InlineData("{\"a\":1} trailing")]
        public void TextThatIsNotOneValueIsRejected(string json) {
            Assert.ThrowsAny<JsonException>(() => JsonText.Parse(json));
        }
    }
}
