using pyRevitLabs.Json.Linq;

namespace pyRevitCLI.Tests;

[Collection(CliGlobalState.Name)]
public sealed class AgentSessionCommandTests : IDisposable {
    private readonly FakeAgentHost host = new FakeAgentHost();

    public AgentSessionCommandTests() {
        host.Handler = request => FakeAgentHost.Result(request, new JObject { ["state"] = "inactive" });
    }

    public void Dispose() {
        host.Dispose();
    }

    [Theory]
    [InlineData("status", "session_status")]
    [InlineData("pause", "pause_session")]
    [InlineData("end", "end_session")]
    [InlineData("request", "request_session")]
    public void EachActionCallsItsHostMethod(string action, string method) {
        PyRevitCLIAgentCmds.ControlSession(action, reason: null, revitSelector: null);

        var sent = Assert.Single(host.Requests);
        Assert.Equal(method, sent.Value<string>("method"));
    }

    [Fact]
    public void ARequestSendsItsReasonOnlyWhenGiven() {
        PyRevitCLIAgentCmds.ControlSession("request", reason: "Check the door marks", revitSelector: null);
        PyRevitCLIAgentCmds.ControlSession("request", reason: null, revitSelector: null);

        var requests = host.RequestsFor("request_session");
        Assert.Equal("Check the door marks", requests[0]["params"].Value<string>("reason"));
        Assert.Null(requests[1]["params"]["reason"]);
    }
}
