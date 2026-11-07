using PyRevitLabs.PyRevit.Runtime.Agent;
using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    [Trait("Environment", "HostFree")]
    [Trait("Level", "Unit")]
    public sealed class AgentParamsTests {
        private static JObject Params(string json) => JObject.Parse(json);

        [Theory]
        [InlineData("{\"zoom\":\"true\"}", "zoom", "'zoom' must be true or false.")]
        [InlineData("{\"zoom\":1}", "zoom", "'zoom' must be true or false.")]
        public void BooleansMustBeJsonBooleans(string json, string name, string message) {
            var error = Assert.Throws<AgentException>(() => AgentParams.Get<bool?>(Params(json), name));

            Assert.Equal("invalid_params", error.Code);
            Assert.Equal(message, error.Message);
        }

        [Theory]
        [InlineData("{\"width\":1280.5}")]
        [InlineData("{\"width\":\"1280\"}")]
        [InlineData("{\"width\":Infinity}")]
        [InlineData("{\"width\":true}")]
        public void IntegersMustBeWholeJsonNumbers(string json) {
            var error = Assert.Throws<AgentException>(() => AgentParams.Get<int?>(Params(json), "width"));

            Assert.Equal("invalid_params", error.Code);
            Assert.Equal("'width' must be an integer.", error.Message);
        }

        [Theory]
        [InlineData("{\"timeout_s\":\"abc\"}", "'timeout_s' must be a number.")]
        [InlineData("{\"timeout_s\":\"5\"}", "'timeout_s' must be a number.")]
        public void NumbersMustBeJsonNumbers(string json, string message) {
            var error = Assert.Throws<AgentException>(() => AgentParams.Get<double?>(Params(json), "timeout_s"));

            Assert.Equal(message, error.Message);
        }

        [Theory]
        [InlineData("{\"script\":{}}")]
        [InlineData("{\"script\":[]}")]
        [InlineData("{\"script\":5}")]
        public void StringsMustBeJsonStrings(string json) {
            var error = Assert.Throws<AgentException>(() => AgentParams.Get<string>(Params(json), "script"));

            Assert.Equal("'script' must be a string.", error.Message);
        }

        [Fact]
        public void AnIntegerTooLargeForTheTypeIsOutOfRange() {
            var error = Assert.Throws<AgentException>(() => AgentParams.Get<int?>(Params("{\"width\":2147483648}"), "width"));

            Assert.Equal("'width' is out of range.", error.Message);
        }

        [Fact]
        public void MatchingValuesAreRead() {
            var parameters = Params("{\"width\":1280.0,\"zoom\":true,\"timeout_s\":5,\"title\":\"2025-06-18T00:00:00Z\",\"none\":null}");

            Assert.Equal(1280, AgentParams.Get<int?>(parameters, "width"));
            Assert.True(AgentParams.Get<bool?>(parameters, "zoom"));
            Assert.Equal(5.0, AgentParams.Get<double?>(parameters, "timeout_s"));
            Assert.False(string.IsNullOrEmpty(AgentParams.Get<string>(parameters, "title")));
            Assert.Null(AgentParams.Get<int?>(parameters, "none"));
            Assert.Null(AgentParams.Get<string>(parameters, "missing"));
        }
    }
}
