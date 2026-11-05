using System.Collections.Concurrent;
using System.Text;
using pyRevitCLI;
using pyRevitLabs.Json;
using pyRevitLabs.Json.Linq;

namespace pyRevitCLI.Tests;

public partial class McpServerTests {
    private static readonly TimeSpan Patience = TimeSpan.FromSeconds(10);

    /// <summary>
    /// An MCP session driven line by line: requests go in while earlier calls are still open.
    /// </summary>
    private sealed class LiveSession : IDisposable {
        private readonly BlockingCollection<string> input = new BlockingCollection<string>();
        private readonly LineWriter output = new LineWriter();
        private readonly Task serving;

        public LiveSession(string defaultRevit = null) {
            serving = Task.Run(() => PyRevitMcpServer.Serve(defaultRevit, new LineReader(input), output));
        }

        public void Send(JObject message) => input.Add(message.ToString(Formatting.None));

        public void Cancel(int requestId) => Send(new JObject {
            ["jsonrpc"] = "2.0",
            ["method"] = "notifications/cancelled",
            ["params"] = new JObject { ["requestId"] = requestId, ["reason"] = "test" },
        });

        public JObject Next() {
            Assert.True(output.Lines.TryTake(out var line, Patience), "The server did not answer in time.");
            return JObject.Parse(line);
        }

        public void Dispose() {
            input.CompleteAdding();
            Assert.True(serving.Wait(Patience), "The server did not finish its open calls.");
        }
    }

    private sealed class LineReader : TextReader {
        private readonly BlockingCollection<string> lines;

        public LineReader(BlockingCollection<string> lines) {
            this.lines = lines;
        }

        public override string ReadLine() => lines.TryTake(out var line, Timeout.Infinite) ? line : null;
    }

    private sealed class LineWriter : TextWriter {
        public BlockingCollection<string> Lines { get; } = new BlockingCollection<string>();

        public override Encoding Encoding => Encoding.UTF8;

        public override void WriteLine(string value) => Lines.Add(value);
    }

    private ManualResetEventSlim BlockRunsUntil(ManualResetEventSlim release) {
        var started = new ManualResetEventSlim(false);
        host.Handler = request => {
            if (request.Value<string>("method") == "run") {
                started.Set();
                release.Wait(Patience);
                return RunResponse(request);
            }
            return FakeAgentHost.Result(request, new JObject { ["pong"] = true });
        };
        return started;
    }

    [Fact]
    public void ACallWaitingOnOneRevitDoesNotBlockAnotherRevitOrTheInstanceList() {
        host.AddInstance("2091");
        using var release = new ManualResetEventSlim(false);
        var runStarted = BlockRunsUntil(release);
        using var session = new LiveSession();

        session.Send(ToolCall(1, "run_query", new JObject { ["script"] = "result = 1", ["revit"] = "2090" }));
        Assert.True(runStarted.Wait(Patience));
        session.Send(ToolCall(2, "get_context", new JObject { ["revit"] = "2091" }));
        var context = session.Next();
        session.Send(ToolCall(3, "list_revit_instances"));
        var listed = session.Next();
        release.Set();
        var run = session.Next();

        Assert.Equal(2, context.Value<int>("id"));
        Assert.False(IsError(context));
        Assert.Equal(3, listed.Value<int>("id"));
        var instances = Payload(listed)["instances"].ToDictionary(entry => entry.Value<string>("revit_version"));
        Assert.True(instances["2090"].Value<bool>("busy"));
        Assert.Null(instances["2090"]["responding"]);
        Assert.True(instances["2091"].Value<bool>("responding"));
        Assert.Null(instances["2091"]["busy"]);
        Assert.Equal(1, run.Value<int>("id"));
        Assert.False(IsError(run));
    }

    [Fact]
    public void CancellingAQueuedCallReportsItNotSentAndCancellingASentCallReportsItUnknown() {
        using var release = new ManualResetEventSlim(false);
        var runStarted = BlockRunsUntil(release);
        PyRevitAgentClient.ConnectTimeoutMs = 300;
        using var session = new LiveSession();

        session.Send(ToolCall(1, "run_modify", new JObject { ["script"] = "result = 1" }));
        Assert.True(runStarted.Wait(Patience));
        session.Send(ToolCall(2, "get_context"));
        session.Cancel(2);
        var queued = session.Next();
        session.Cancel(1);
        var sent = session.Next();
        session.Send(ToolCall(3, "list_revit_instances"));
        var listed = session.Next();
        release.Set();

        Assert.Equal(2, queued.Value<int>("id"));
        Assert.True(IsError(queued));
        Assert.Equal("cancelled", Payload(queued).Value<string>("error"));
        Assert.Equal(AgentOutcome.NotSent, Payload(queued).Value<string>("outcome"));
        Assert.Equal(1, sent.Value<int>("id"));
        Assert.True(IsError(sent));
        Assert.Equal("cancelled", Payload(sent).Value<string>("error"));
        Assert.Equal(AgentOutcome.Unknown, Payload(sent).Value<string>("outcome"));
        Assert.Equal(host.RequestsFor("run").Single().Value<string>("id"), Payload(sent).Value<string>("request_id"));
        Assert.Empty(host.RequestsFor("get_context"));
        Assert.Equal(3, listed.Value<int>("id"));
        Assert.Null(Payload(listed)["instances"][0]["busy"]);
        Assert.False(Payload(listed)["instances"][0].Value<bool>("responding"));
    }

    [Theory]
    [InlineData("\"\"")]
    [InlineData("null")]
    public void AnEmptyRevitArgumentUsesTheServerDefault(string revit) {
        host.AddInstance("2091");
        host.Handler = request => FakeAgentHost.Result(request, new JObject { ["pong"] = true });
        var arguments = new JObject { ["revit"] = JToken.Parse(revit) };
        var input = new StringReader(ToolCall(1, "get_context", arguments).ToString(Formatting.None));
        var output = new StringWriter();

        PyRevitMcpServer.Serve("2091", input, output);

        var response = JObject.Parse(output.ToString().Trim());
        Assert.False(IsError(response), Text(response));
        Assert.Single(host.RequestsFor("get_context"));
    }
}
