using pyRevitCLI;
using pyRevitLabs.Common;
using pyRevitLabs.Json.Linq;

namespace pyRevitCLI.Tests;

[Collection(CliGlobalState.Name)]
[Trait("Environment", "HostFree")]
[Trait("Level", "Unit")]
public sealed class AgentRecordCommandTests : IDisposable {
    private readonly FakeAgentHost host = new FakeAgentHost();

    public void Dispose() => host.Dispose();

    private static string Printed(Action command) {
        var original = Console.Out;
        var captured = new StringWriter();
        Console.SetOut(captured);
        try {
            command();
        }
        finally {
            Console.SetOut(original);
        }
        return captured.ToString();
    }

    [Theory]
    [InlineData("--screenshot-interval", "abc", null, null, null)]
    [InlineData("--max-screenshots", null, "abc", null, null)]
    [InlineData("--max-events", null, null, "1e999", null)]
    [InlineData("--max-duration", null, null, null, "NaN")]
    public void ANonNumberNamesTheOptionTheUserTypedAndNeverReachesTheHost(
        string option, string interval, string screenshots, string events, string duration) {
        var refused = Assert.Throws<PyRevitException>(
            () => PyRevitCLIAgentCmds.Record("start", true, interval, screenshots, events, duration, null));

        Assert.StartsWith(option + " must be a number: ", refused.Message);
        Assert.Empty(host.Requests);
    }

    [Fact]
    public void ARangeErrorFromTheHostNamesTheOptionsInsteadOfTheRuntimeParameters() {
        host.Handler = request => FakeAgentHost.Failure(
            request, "invalid_params", "'max_screenshots' must be between 0 and 100.");

        var refused = Assert.Throws<PyRevitException>(
            () => PyRevitCLIAgentCmds.Record("start", true, null, "101", null, null, null));

        Assert.Equal("--max-screenshots must be between 0 and 100.", refused.Message);
    }

    [Fact]
    public void ZeroIsPassedOnAsANumber() {
        host.Handler = request => FakeAgentHost.Result(request, new JObject());

        Printed(() => PyRevitCLIAgentCmds.Record("start", true, "0", null, null, null, null));

        var parameters = (JObject)Assert.Single(host.RequestsFor("recording_start"))["params"];
        Assert.Equal(0, parameters.Value<double>("screenshot_interval_s"));
    }
}
