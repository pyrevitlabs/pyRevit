using pyRevitLabs.Json.Linq;

namespace pyRevitCLI.Tests;

public partial class McpServerTests {
    private static JObject Session(string state) {
        return new JObject { ["required"] = true, ["state"] = state };
    }

    [Fact]
    public void ModelToolsRefuseAMissingDocumentWithoutReachingRevit() {
        var calls = new[] {
            ToolCall(1, "run_query", new JObject { ["script"] = "x = 1", ["title"] = "Read" }),
            ToolCall(2, "run_modify", new JObject { ["script"] = "x = 1", ["title"] = "Change", ["document"] = "  " }),
            ToolCall(3, "inspect_elements", new JObject { ["ids"] = new JArray(1), ["title"] = "Inspect" }),
            ToolCall(4, "show_elements", new JObject { ["ids"] = new JArray(1), ["title"] = "Show" }),
            ToolCall(5, "capture_view", new JObject { ["title"] = "Look", ["document"] = null }),
        };

        foreach (var call in calls) {
            var payload = Payload(Single(call));
            Assert.Equal("invalid_params", payload.Value<string>("error"));
            Assert.Contains("document", payload.Value<string>("message"));
        }
        Assert.Empty(host.Requests);
    }

    [Fact]
    public void TheDocumentTheAgentNamesIsSentToRevit() {
        host.Handler = request => request.Value<string>("method") == "run"
            ? RunResponse(request)
            : FakeAgentHost.Result(request, new JObject { ["ok"] = true });

        Serve(
            ToolCall(1, "run_query", new JObject { ["script"] = "x = 1", ["title"] = "Read", ["document"] = " doc-7 " }),
            ToolCall(2, "inspect_elements", new JObject { ["ids"] = new JArray(1), ["title"] = "Inspect", ["document"] = "doc-7" }),
            ToolCall(3, "show_elements", new JObject { ["ids"] = new JArray(1), ["title"] = "Show", ["document"] = "doc-7" }),
            ToolCall(4, "capture_view", new JObject { ["title"] = "Look", ["document"] = "doc-7" }));

        foreach (var method in new[] { "run", "inspect_elements", "show", "capture" })
            Assert.Equal("doc-7", Assert.Single(host.RequestsFor(method))["params"].Value<string>("document"));
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

        using (var session = new LiveSession()) {
            session.Send(initialize);
            session.Next();
            session.Send(ToolCall(2, "get_context"));
            session.Next();
            session.Send(ToolCall(3, "list_revit_instances"));
            session.Next();
        }

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
