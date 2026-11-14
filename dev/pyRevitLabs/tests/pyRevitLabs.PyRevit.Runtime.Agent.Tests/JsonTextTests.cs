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

        /// <summary>
        /// A script result with a date-like or offset timestamp string comes back as written.
        /// </summary>
        [Theory]
        [InlineData("2024-05-01")]
        [InlineData("2024-05-01T10:00:00+02:00")]
        [InlineData("2024-05-01T10:00:00.1234567+02:00")]
        [InlineData("2024-05-01T10:00:00.123Z")]
        public void AResultKeepsTheTimestampTextAsWritten(string text) {
            var result = JsonText.Parse("{\"d\":\"" + text + "\"}");

            Assert.Equal(JTokenType.String, result["d"].Type);
            Assert.Equal(text, result["d"].Value<string>());
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

        /// <summary>
        /// Inputs with date-like and offset timestamp strings reach the run record as written.
        /// </summary>
        [Theory]
        [InlineData("2024-05-01")]
        [InlineData("2024-05-01T10:00:00+02:00")]
        [InlineData("2024-05-01T10:00:00.1234567+02:00")]
        [InlineData("2024-05-01T10:00:00.50Z")]
        public void TheRunRecordKeepsTheInputTimestampText(string text) {
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
