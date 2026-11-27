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

    [Fact]
    public void AStartCarriesItsReasonOnlyWhenGivenAndPrintsThePendingRequest() {
        host.Handler = request => FakeAgentHost.Result(request, new JObject {
            ["recording"] = false,
            ["requested"] = true,
            ["pending_request"] = new JObject { ["reason"] = "Reproduce the crash" },
        });

        var printed = Printed(() => PyRevitCLIAgentCmds.Record("start", true, null, null, null, null, null, reason: "Reproduce the crash"));
        Printed(() => PyRevitCLIAgentCmds.Record("start", true, null, null, null, null, null));

        var requests = host.RequestsFor("recording_start");
        Assert.Equal("Reproduce the crash", requests[0]["params"].Value<string>("reason"));
        Assert.Null(requests[1]["params"]["reason"]);
        var status = JObject.Parse(printed);
        Assert.True(status.Value<bool>("requested"));
        Assert.Equal("Reproduce the crash", status["pending_request"].Value<string>("reason"));
    }

    [Fact]
    public void StopAndStatusSendNoReason() {
        host.Handler = request => FakeAgentHost.Result(request, new JObject());

        Printed(() => PyRevitCLIAgentCmds.Record("stop", true, null, null, null, null, null, reason: "ignored"));
        Printed(() => PyRevitCLIAgentCmds.Record("status", true, null, null, null, null, null, reason: "ignored"));

        Assert.Null((Assert.Single(host.RequestsFor("recording_stop"))["params"] as JObject)?["reason"]);
        Assert.Null((Assert.Single(host.RequestsFor("recording_status"))["params"] as JObject)?["reason"]);
    }

    private static IDictionary<string, DocoptNet.ValueObject> Parse(params string[] argv) {
        var usage = File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "UsagePatterns.txt"));
        return new DocoptNet.Docopt().Apply(usage, argv, help: false, exit: false);
    }

    [Fact]
    public void ARecordStartTakesAReasonOnTheCommandLine() {
        var arguments = Parse("agent", "record", "start", "--no-screenshots", "--reason=Reproduce the crash", "--revit=2026");

        Assert.True(arguments["record"].IsTrue);
        Assert.Equal("start", PyRevitCLIArguments.Value(arguments, "<action>"));
        Assert.Equal("Reproduce the crash", PyRevitCLIArguments.Value(arguments, "--reason"));
        Assert.True(arguments["--no-screenshots"].IsTrue);
    }

    [Fact]
    public void RecordingStartIsConfiguredLikeSessionStart() {
        var set = Parse("configs", "agent", "recordingstart", "auto");
        var read = Parse("configs", "agent", "recordingstart");

        Assert.True(set["recordingstart"].IsTrue);
        Assert.True(set["auto"].IsTrue);
        Assert.False(set["sessionstart"].IsTrue);
        Assert.True(read["recordingstart"].IsTrue);
        Assert.False(read["auto"].IsTrue || read["user"].IsTrue);
    }
}
