using pyRevitLabs.Json.Linq;

namespace pyRevitCLI.Tests;

public partial class McpServerTests {
    private static JObject Session(string state) {
        return new JObject { ["required"] = true, ["state"] = state };
    }

    [Fact]
    public void RequestSessionForwardsTheReasonAndReturnsTheHostAnswer() {
        host.Handler = request => FakeAgentHost.Result(request, new JObject { ["requested"] = true, ["session"] = Session("inactive") });

        var response = Single(ToolCall(1, "request_session", new JObject { ["reason"] = "Renumber the doors on Level 2" }));

        var sent = Assert.Single(host.RequestsFor("request_session"))["params"];
        Assert.Equal("Renumber the doors on Level 2", sent.Value<string>("reason"));
        Assert.False(IsError(response));
        Assert.True(Payload(response).Value<bool>("requested"));
    }

    [Fact]
    public void ARequestForASessionWithAnOverlongReasonNeverReachesRevit() {
        var response = Single(ToolCall(1, "request_session", new JObject { ["reason"] = new string('r', 301) }));

        Assert.True(IsError(response));
        Assert.Equal("invalid_params", Payload(response).Value<string>("error"));
        Assert.Empty(host.Requests);
    }

    [Fact]
    public void ASessionRefusalReachesTheAgentWithItsType() {
        host.Handler = request => FakeAgentHost.Failure(request, "session_inactive", "No agent session is active in this Revit.");

        var response = Single(ToolCall(1, "get_context"));

        Assert.True(IsError(response));
        Assert.Equal("session_inactive", Payload(response).Value<string>("error"));
    }

    [Fact]
    public void ListedInstancesReportTheirSession() {
        host.Handler = request => FakeAgentHost.Result(request, new JObject { ["pong"] = true, ["session"] = Session("paused") });

        var listed = Payload(Single(ToolCall(1, "list_revit_instances")));

        Assert.Equal("paused", listed["instances"][0]["session"].Value<string>("state"));
    }

    [Fact]
    public void EveryRevitCallNamesTheClientFromInitialize() {
        var initialize = Request(1, "initialize", new JObject {
            ["protocolVersion"] = "2025-06-18",
            ["clientInfo"] = new JObject { ["name"] = "Claude Code", ["version"] = "2.0" },
        });

        Serve(initialize, ToolCall(2, "get_context"), ToolCall(3, "list_revit_instances"));

        Assert.Equal("Claude Code", Assert.Single(host.RequestsFor("get_context"))["params"].Value<string>("client"));
        Assert.Equal("Claude Code", Assert.Single(host.RequestsFor("ping"))["params"].Value<string>("client"));
    }

    [Fact]
    public void WithoutClientInfoNoClientIsSent() {
        Single(ToolCall(1, "get_context"));

        Assert.Null(Assert.Single(host.RequestsFor("get_context"))["params"]["client"]);
    }

    [Fact]
    public void AnInstanceThatReportsNoSessionIsListedWithout() {
        var listed = Payload(Single(ToolCall(1, "list_revit_instances")));

        Assert.Null(listed["instances"][0]["session"]);
    }
}
