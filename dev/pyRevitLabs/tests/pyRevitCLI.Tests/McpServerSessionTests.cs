using pyRevitLabs.Json;
using pyRevitLabs.Json.Linq;

namespace pyRevitCLI.Tests;

public partial class McpServerTests {
    private static JObject Session(string state) {
        return new JObject { ["required"] = true, ["state"] = state };
    }

    private static JObject ContextWithGeneration(int? generation) {
        var session = Session("active");
        if (generation.HasValue)
            session["generation"] = generation.Value;
        return new JObject { ["document"] = new JObject { ["title"] = "Tower" }, ["agent"] = new JObject { ["session"] = session } };
    }

    private static JObject QueryArguments(string title) {
        return new JObject { ["script"] = "result = 1", ["title"] = title };
    }

    /// <summary>
    /// Serves the requests one at a time, each after the previous one was answered, for tests
    /// that depend on the order of tool calls the server otherwise runs concurrently.
    /// </summary>
    private static List<JObject> ServeInTurn(params JObject[] requests) {
        using var output = new AnswerWriter();
        PyRevitMcpServer.Serve(null, new InTurnReader(requests, output), output);
        return output.Answers;
    }

    private sealed class AnswerWriter : StringWriter {
        private readonly object sync = new object();

        public List<JObject> Answers { get; } = new List<JObject>();

        public override void WriteLine(string value) {
            lock (sync) {
                Answers.Add(JObject.Parse(value));
                Monitor.PulseAll(sync);
            }
        }

        public void WaitFor(int count) {
            lock (sync) {
                while (Answers.Count < count)
                    if (!Monitor.Wait(sync, TimeSpan.FromSeconds(30)))
                        throw new TimeoutException($"Expected {count} answers, got {Answers.Count}.");
            }
        }
    }

    private sealed class InTurnReader : TextReader {
        private readonly JObject[] requests;
        private readonly AnswerWriter output;
        private int next;

        public InTurnReader(JObject[] requests, AnswerWriter output) {
            this.requests = requests;
            this.output = output;
        }

        public override string ReadLine() {
            if (next == requests.Length)
                return null;
            output.WaitFor(next);
            return requests[next++].ToString(Formatting.None);
        }
    }

    [Fact]
    public void RequestsAfterGetContextCarryTheGenerationItRead() {
        host.Handler = request => request.Value<string>("method") == "get_context"
            ? FakeAgentHost.Result(request, ContextWithGeneration(3))
            : RunResponse(request);

        ServeInTurn(
            ToolCall(1, "run_query", QueryArguments("Before")),
            ToolCall(2, "get_context"),
            ToolCall(3, "run_query", QueryArguments("After")));

        var runs = host.RequestsFor("run");
        Assert.Null(runs[0]["params"]["generation"]);
        Assert.Equal(3, runs[1]["params"].Value<int>("generation"));
        Assert.Null(Assert.Single(host.RequestsFor("get_context"))["params"]["generation"]);
    }

    [Fact]
    public void AnAutomationsContextCheckLeavesTheAgentsGenerationAlone() {
        host.Handler = request => request.Value<string>("method") == "get_context"
            ? FakeAgentHost.Result(request, ContextWithGeneration(request["params"].Value<bool?>("keep_changes") == true ? 7 : 3))
            : RunResponse(request);

        ServeInTurn(
            ToolCall(1, "get_context"),
            ToolCall(2, "run_automation", new JObject {
                ["id"] = "pyrevit.levels.resolve",
                ["inputs"] = new JObject { ["name"] = "Level 1" },
            }),
            ToolCall(3, "run_query", QueryArguments("After")));

        var runs = host.RequestsFor("run");
        Assert.Equal(2, runs.Count);
        Assert.All(runs, run => Assert.Equal(3, run["params"].Value<int>("generation")));
    }

    [Fact]
    public void AContextWithoutAGenerationStopsTheServerSendingOne() {
        var reads = 0;
        host.Handler = request => request.Value<string>("method") == "get_context"
            ? FakeAgentHost.Result(request, ContextWithGeneration(++reads == 1 ? 3 : null))
            : RunResponse(request);

        ServeInTurn(
            ToolCall(1, "get_context"),
            ToolCall(2, "get_context"),
            ToolCall(3, "run_query", QueryArguments("After")));

        Assert.Null(Assert.Single(host.RequestsFor("run"))["params"]["generation"]);
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
