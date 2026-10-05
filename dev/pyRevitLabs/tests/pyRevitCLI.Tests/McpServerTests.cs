using pyRevitCLI;
using pyRevitLabs.Json;
using pyRevitLabs.Json.Linq;

namespace pyRevitCLI.Tests;

[Collection(CliGlobalState.Name)]
public partial class McpServerTests : IDisposable {
    private static readonly string[] ReadOnlyTools = {
        "list_skills", "get_skill", "list_revit_instances", "get_context", "inspect_elements", "lookup_pyrevit_api", "list_automation",
        "run_automation", "lookup_revit_api", "show_elements", "navigate_revit_link", "capture_view", "get_run",
    };

    private readonly FakeAgentHost host = new FakeAgentHost();

    public void Dispose() {
        host.Dispose();
    }

    private static JObject Request(int id, string method, JObject parameters = null) {
        var request = new JObject { ["jsonrpc"] = "2.0", ["id"] = id, ["method"] = method };
        if (parameters != null)
            request["params"] = parameters;
        return request;
    }

    private static JObject ToolCall(int id, string tool, JObject arguments = null, JObject meta = null) {
        var parameters = new JObject { ["name"] = tool, ["arguments"] = arguments ?? new JObject() };
        if (meta != null)
            parameters["_meta"] = meta;
        return Request(id, "tools/call", parameters);
    }

    private static List<JObject> Serve(params object[] lines) {
        var input = new StringReader(string.Join("\n", lines.Select(line => line is JObject message ? message.ToString(Formatting.None) : (string)line)));
        var output = new StringWriter();
        PyRevitMcpServer.Serve(null, input, output);
        return output.ToString()
            .Split('\n', StringSplitOptions.RemoveEmptyEntries)
            .Select(line => JObject.Parse(line))
            .ToList();
    }

    private static JObject Single(object line) => Assert.Single(Serve(line));

    private static string Text(JObject response, int block = 0) => response["result"]["content"][block].Value<string>("text");

    private static JObject Payload(JObject response) => JObject.Parse(Text(response));

    private static bool IsError(JObject response) => response["result"].Value<bool>("isError");

    private static JObject RunResponse(JObject request, string status = "ok", JObject extra = null) {
        var run = new JObject {
            ["status"] = status,
            ["run_id"] = "abc123def456",
            ["mode"] = request["params"].Value<string>("mode"),
            ["decision"] = "rolled_back",
            ["elapsed_ms"] = 5,
        };
        if (extra != null)
            run.Merge(extra);
        return FakeAgentHost.Result(request, run);
    }

    [Fact]
    public void InitializeNegotiatesTheProtocolVersionAndDescribesTheServer() {
        var supported = Single(Request(1, "initialize", new JObject { ["protocolVersion"] = "2025-03-26" }));
        var unsupported = Single(Request(1, "initialize", new JObject { ["protocolVersion"] = "1999-01-01" }));

        Assert.Equal("2025-03-26", supported["result"].Value<string>("protocolVersion"));
        Assert.Equal("2025-06-18", unsupported["result"].Value<string>("protocolVersion"));
        Assert.Equal("pyrevit", supported["result"]["serverInfo"].Value<string>("name"));
        Assert.Equal("0.0.0-tests", supported["result"]["serverInfo"].Value<string>("version"));
        Assert.False(supported["result"]["capabilities"]["tools"].Value<bool>("listChanged"));
        Assert.Contains("get_context", supported["result"].Value<string>("instructions"));
        Assert.Contains("revit-scripting", supported["result"].Value<string>("instructions"));
    }

    [Fact]
    public void PingAnswersWithAnEmptyResult() {
        Assert.Empty(((JObject)Single(Request(7, "ping"))["result"]).Properties());
    }

    [Fact]
    public void UnknownMethodsParseErrorsAndNotificationsAreHandledAsJsonRpcRequires() {
        var responses = Serve(
            Request(1, "no/such/method"),
            "",
            "{ this is not json",
            new JObject { ["jsonrpc"] = "2.0", ["method"] = "notifications/initialized" },
            Request(2, "ping"));

        Assert.Equal(3, responses.Count);
        Assert.Equal(-32601, responses[0]["error"].Value<int>("code"));
        Assert.Contains("no/such/method", responses[0]["error"].Value<string>("message"));
        Assert.Equal(-32700, responses[1]["error"].Value<int>("code"));
        Assert.Equal(JTokenType.Null, responses[1]["id"].Type);
        Assert.Equal(2, responses[2].Value<int>("id"));
    }

    [Fact]
    public void TheToolListHasTheExpectedToolsWithConsistentSchemasAndHints() {
        var tools = ((JArray)Single(Request(1, "tools/list"))["result"]["tools"]).Cast<JObject>().ToList();

        Assert.Equal(
            new[] {
                "list_skills", "get_skill", "list_revit_instances", "get_context", "inspect_elements", "lookup_pyrevit_api", "list_automation",
                "run_automation", "lookup_revit_api", "show_elements", "navigate_revit_link", "capture_view", "run_query", "run_modify", "get_run",
            },
            tools.Select(tool => tool.Value<string>("name")));
        foreach (var tool in tools) {
            var name = tool.Value<string>("name");
            Assert.False(string.IsNullOrWhiteSpace(tool.Value<string>("description")), name);
            Assert.Equal("object", tool["inputSchema"].Value<string>("type"));
            var properties = (JObject)tool["inputSchema"]["properties"];
            foreach (var required in tool["inputSchema"]["required"])
                Assert.True(properties[required.Value<string>()] != null, name + " requires an undeclared property");
            var readOnly = ReadOnlyTools.Contains(name);
            Assert.Equal(readOnly, tool["annotations"].Value<bool>("readOnlyHint"));
            Assert.Equal(!readOnly, tool["annotations"].Value<bool>("destructiveHint"));
        }
    }

    [Fact]
    public void RequiredArgumentsAreDeclared() {
        var tools = ((JArray)Single(Request(1, "tools/list"))["result"]["tools"]).Cast<JObject>().ToDictionary(tool => tool.Value<string>("name"));

        Assert.Equal(new[] { "script" }, tools["run_query"]["inputSchema"]["required"].Select(token => token.Value<string>()));
        Assert.Equal(new[] { "script", "title" }, tools["run_modify"]["inputSchema"]["required"].Select(token => token.Value<string>()));
        Assert.Equal(new[] { "run_id" }, tools["get_run"]["inputSchema"]["required"].Select(token => token.Value<string>()));
        Assert.Equal(new[] { "ids" }, tools["inspect_elements"]["inputSchema"]["required"].Select(token => token.Value<string>()));
        Assert.Equal(new[] { "id", "inputs" }, tools["run_automation"]["inputSchema"]["required"].Select(token => token.Value<string>()));
        Assert.Equal(new[] { "query" }, tools["lookup_pyrevit_api"]["inputSchema"]["required"].Select(token => token.Value<string>()));
        Assert.Equal(new[] { "link" }, tools["navigate_revit_link"]["inputSchema"]["required"].Select(token => token.Value<string>()));
        Assert.Contains("revit-scripting", tools["get_skill"]["inputSchema"]["properties"]["name"]["enum"].Select(token => token.Value<string>()));
    }

    [Fact]
    public void AnUnknownToolIsAnErrorResultNotAProtocolError() {
        var response = Single(ToolCall(1, "no_such_tool"));

        Assert.True(IsError(response));
        Assert.Equal("unknown_tool", Payload(response).Value<string>("error"));
    }

    [Fact]
    public void AQueryForwardsTheScriptAndReturnsAShapedResult() {
        host.Handler = request => request.Value<string>("method") == "run"
            ? RunResponse(request, extra: new JObject { ["result"] = new JObject { ["count"] = 3 } })
            : FakeAgentHost.Result(request, new JObject());

        var response = Single(ToolCall(1, "run_query", new JObject { ["script"] = "result = 3" }));

        var sent = Assert.Single(host.RequestsFor("run"))["params"];
        Assert.Equal("query", sent.Value<string>("mode"));
        Assert.Equal("result = 3", sent.Value<string>("script"));
        Assert.Equal("Agent query", sent.Value<string>("title"));
        Assert.Empty(((JObject)sent["inputs"]).Properties());
        Assert.Null(sent["engine"]);
        var payload = Payload(response);
        Assert.Equal(new[] { "status", "run_id" }, payload.Properties().Take(2).Select(property => property.Name));
        Assert.Equal(3, payload["result"].Value<int>("count"));
        Assert.Null(payload["decision"]);
        Assert.False(IsError(response));
    }

    [Fact]
    public void OptionalRunArgumentsAreForwardedWhenGiven() {
        host.Handler = request => RunResponse(request);

        Serve(ToolCall(1, "run_query", new JObject {
            ["script"] = "x = 1",
            ["title"] = "Mine",
            ["engine"] = "cpython",
            ["workspace"] = "C:\\work",
            ["timeout_s"] = 12,
            ["inputs"] = new JObject { ["a"] = 1 },
        }));

        var sent = Assert.Single(host.RequestsFor("run"))["params"];
        Assert.Equal("Mine", sent.Value<string>("title"));
        Assert.Equal("cpython", sent.Value<string>("engine"));
        Assert.Equal("C:\\work", sent.Value<string>("workspace"));
        Assert.Equal(12, sent.Value<int>("timeout_s"));
        Assert.Equal(1, sent["inputs"].Value<int>("a"));
    }

    [Fact]
    public void ModifyRunsChooseTheModeFromDryRunAndKeepTheDecision() {
        host.Handler = request => RunResponse(request);

        var dry = Single(ToolCall(1, "run_modify", new JObject { ["script"] = "x = 1", ["title"] = "T", ["dry_run"] = true }));
        var real = Single(ToolCall(2, "run_modify", new JObject { ["script"] = "x = 1", ["title"] = "T" }));

        var modes = host.RequestsFor("run").Select(request => request["params"].Value<string>("mode")).ToList();
        Assert.Equal(new[] { "dry_run", "modify" }, modes);
        Assert.Equal("rolled_back", Payload(dry).Value<string>("decision"));
        Assert.Equal("rolled_back", Payload(real).Value<string>("decision"));
    }

    [Fact]
    public void ModifyRunsDefaultTheTitle() {
        host.Handler = request => RunResponse(request);

        Serve(ToolCall(1, "run_modify", new JObject { ["script"] = "x = 1" }));

        Assert.Equal("Agent change", Assert.Single(host.RequestsFor("run"))["params"].Value<string>("title"));
    }

    [Fact]
    public void ARunWithoutAScriptIsRejectedWithoutReachingRevit() {
        var response = Single(ToolCall(1, "run_query", new JObject { ["script"] = "  " }));

        Assert.True(IsError(response));
        Assert.Equal("invalid_params", Payload(response).Value<string>("error"));
        Assert.Empty(host.Requests);
    }

    [Fact]
    public void AFailedRunIsFlaggedAsAnErrorResult() {
        host.Handler = request => RunResponse(request, "error", new JObject {
            ["error"] = new JObject { ["type"] = "ValueError", ["message"] = "bad" },
        });

        var response = Single(ToolCall(1, "run_query", new JObject { ["script"] = "raise ValueError()" }));

        Assert.True(IsError(response));
        Assert.Equal("ValueError", Payload(response)["error"].Value<string>("type"));
    }

    [Fact]
    public void AMissingRevitNameIsLookedUpAndTheAnswerBecomesTheHint() {
        host.Handler = request => request.Value<string>("method") == "run"
            ? RunResponse(request, "error", new JObject {
                ["error"] = new JObject { ["type"] = "AttributeError", ["message"] = "'Autodesk.Revit.DB' object has no attribute 'Wal'" },
            })
            : FakeAgentHost.Result(request, new JObject {
                ["found"] = false,
                ["suggestions"] = new JArray("Autodesk.Revit.DB.Wall"),
            });

        var response = Single(ToolCall(1, "run_query", new JObject { ["script"] = "x = DB.Wal" }));

        Assert.Equal("Wal", Assert.Single(host.RequestsFor("lookup_api"))["params"].Value<string>("name"));
        Assert.Contains("DB.Wall", Payload(response)["error"].Value<string>("hint"));
    }

    [Fact]
    public void AFailedLookupLeavesTheRunResultIntact() {
        host.Handler = request => request.Value<string>("method") == "run"
            ? RunResponse(request, "error", new JObject {
                ["error"] = new JObject { ["type"] = "AttributeError", ["message"] = "'Autodesk.Revit.DB' object has no attribute 'Wal'" },
            })
            : FakeAgentHost.Failure(request, "revit_busy", "busy");

        var response = Single(ToolCall(1, "run_query", new JObject { ["script"] = "x = DB.Wal" }));

        Assert.Equal("abc123def456", Payload(response).Value<string>("run_id"));
        Assert.Equal("AttributeError", Payload(response)["error"].Value<string>("type"));
    }

    [Fact]
    public void ReadToolsMapToTheHostMethodsWithTheirDefaults() {
        host.Handler = request => FakeAgentHost.Result(request, new JObject { ["ok"] = true });

        Serve(
            ToolCall(1, "get_context"),
            ToolCall(2, "inspect_elements", new JObject { ["ids"] = new JArray(1, 2) }),
            ToolCall(3, "lookup_revit_api", new JObject { ["name"] = "Wall" }),
            ToolCall(4, "show_elements", new JObject { ["ids"] = new JArray(1) }),
            ToolCall(5, "capture_view", new JObject { ["view"] = "3d", ["mode"] = "viewport", ["width"] = 400, ["direction"] = "top", ["elements"] = new JArray(9) }));

        var methods = host.Requests.Select(request => request.Value<string>("method")).OrderBy(name => name).ToList();
        Assert.Equal(new[] { "capture", "get_context", "inspect_elements", "lookup_api", "show" }, methods);
        Assert.True(host.RequestsFor("inspect_elements").Single()["params"].Value<bool>("parameters"));
        Assert.Equal("Wall", host.RequestsFor("lookup_api").Single()["params"].Value<string>("name"));
        var show = host.RequestsFor("show").Single()["params"];
        Assert.Equal("select", show.Value<string>("action"));
        Assert.False(show.Value<bool>("zoom"));
        var capture = host.RequestsFor("capture").Single()["params"];
        Assert.Equal("3d", capture.Value<string>("view"));
        Assert.Equal("viewport", capture.Value<string>("mode"));
        Assert.Equal(400, capture.Value<int>("width"));
        Assert.Equal("top", capture.Value<string>("direction"));
        Assert.Equal(9, capture["elements"][0].Value<int>());
    }

    [Fact]
    public void ACaptureIsReturnedAsAnImageBlockWithoutRepeatingTheData() {
        host.Handler = request => FakeAgentHost.Result(request, new JObject {
            ["image_base64"] = "QUJD",
            ["mode"] = "export",
            ["path"] = "C:\\captures\\view.png",
        });

        var response = Single(ToolCall(1, "capture_view"));

        var content = (JArray)response["result"]["content"];
        Assert.Equal("image", content[0].Value<string>("type"));
        Assert.Equal("QUJD", content[0].Value<string>("data"));
        Assert.Equal("image/png", content[0].Value<string>("mimeType"));
        Assert.DoesNotContain("QUJD", content[1].Value<string>("text"));
        Assert.Contains("view.png", content[1].Value<string>("text"));
        Assert.False(IsError(response));
    }

    [Fact]
    public void TheRevitArgumentSelectsTheHost() {
        host.Handler = request => FakeAgentHost.Result(request, new JObject { ["picked"] = true });

        var picked = Single(ToolCall(1, "get_context", new JObject { ["revit"] = "2090" }));
        var missing = Single(ToolCall(2, "get_context", new JObject { ["revit"] = "2077" }));

        Assert.True(Payload(picked).Value<bool>("picked"));
        Assert.True(IsError(missing));
        Assert.Equal("no_revit", Payload(missing).Value<string>("error"));
    }

    [Fact]
    public void WithoutAHostTheToolsSayNoRevit() {
        Directory.Delete(Path.Combine(host.AgentDir, "instances"), recursive: true);

        var response = Single(ToolCall(1, "get_context"));

        Assert.True(IsError(response));
        Assert.Equal("no_revit", Payload(response).Value<string>("error"));
    }

    [Fact]
    public void HostErrorsKeepTheirTypeAndAMalformedAnswerBecomesAServerError() {
        host.Handler = request => FakeAgentHost.Failure(request, "no_active_document", "Open a project first");
        var hostError = Single(ToolCall(1, "get_context"));
        host.RawResponse = "this is not json";
        var malformed = Single(ToolCall(2, "get_context"));

        Assert.Equal("no_active_document", Payload(hostError).Value<string>("error"));
        Assert.Equal("Open a project first", Payload(hostError).Value<string>("message"));
        Assert.Equal("server_error", Payload(malformed).Value<string>("error"));
    }

    [Fact]
    public void ListedInstancesReportWhetherTheyRespond() {
        var responding = Payload(Single(ToolCall(1, "list_revit_instances")));
        host.Handler = request => null;
        var silent = Payload(Single(ToolCall(2, "list_revit_instances")));

        Assert.True(responding["instances"][0].Value<bool>("responding"));
        Assert.Equal("2090", responding["instances"][0].Value<string>("revit_version"));
        Assert.False(silent["instances"][0].Value<bool>("responding"));
    }

    [Fact]
    public void ASlowCallWithAProgressTokenAnswersWithJustTheResultWhenFast() {
        host.Handler = request => FakeAgentHost.Result(request, new JObject());

        var responses = Serve(ToolCall(1, "get_context", meta: new JObject { ["progressToken"] = "t1" }));

        var only = Assert.Single(responses);
        Assert.Equal(1, only.Value<int>("id"));
    }

    [Fact]
    public void SkillsAreServedAndBadSkillRequestsAreRejected() {
        var read = Single(ToolCall(1, "get_skill", new JObject { ["name"] = "revit-scripting" }));
        var traversal = Single(ToolCall(2, "get_skill", new JObject { ["name"] = "revit-scripting", ["file"] = "..\\INSTRUCTIONS.md" }));
        var notMarkdown = Single(ToolCall(3, "get_skill", new JObject { ["name"] = "revit-scripting", ["file"] = "SKILL.txt" }));
        var unknown = Single(ToolCall(4, "get_skill", new JObject { ["name"] = "no-such-skill" }));

        Assert.False(IsError(read));
        Assert.Contains("name: revit-scripting", Text(read));
        Assert.Equal("invalid_params", Payload(traversal).Value<string>("error"));
        Assert.Equal("invalid_params", Payload(notMarkdown).Value<string>("error"));
        Assert.Equal("skill_not_found", Payload(unknown).Value<string>("error"));
    }

    [Fact]
    public void ARecordedRunIsReturnedWithItsScriptAndAPageOfItsResult() {
        host.AddRun("abc123def456", response: "{\"status\":\"ok\",\"run_id\":\"abc123def456\"}", script: "result = 1", result: "0123456789");

        var run = Payload(Single(ToolCall(1, "get_run", new JObject { ["run_id"] = "abc123def456", ["offset"] = 2, ["length"] = 4 })));

        Assert.Equal("ok", run.Value<string>("status"));
        Assert.Equal("result = 1", run.Value<string>("script"));
        var page = run["result_page"];
        Assert.Equal(2, page.Value<int>("offset"));
        Assert.Equal(4, page.Value<int>("length"));
        Assert.Equal(10, page.Value<int>("total_length"));
        Assert.Equal("2345", page.Value<string>("text"));
    }

    [Fact]
    public void ResultPagesAreCappedAndOffsetsAreClamped() {
        host.AddRun("abc123def456", response: "{}", result: new string('x', 300000));

        var capped = Payload(Single(ToolCall(1, "get_run", new JObject { ["run_id"] = "abc123def456", ["length"] = 999999 })));
        var negative = Payload(Single(ToolCall(2, "get_run", new JObject { ["run_id"] = "abc123def456", ["offset"] = -5, ["length"] = 3 })));
        var beyond = Payload(Single(ToolCall(3, "get_run", new JObject { ["run_id"] = "abc123def456", ["offset"] = 999999 })));

        Assert.Equal(200 * 1024, capped["result_page"].Value<int>("length"));
        Assert.Equal(0, negative["result_page"].Value<int>("offset"));
        Assert.Equal(0, beyond["result_page"].Value<int>("length"));
    }

    [Theory]
    [InlineData("000000000000")]
    [InlineData("*")]
    [InlineData("")]
    public void UnknownRunIdsAreReported(string runId) {
        host.AddRun("abc123def456", response: "{}");

        var response = Single(ToolCall(1, "get_run", new JObject { ["run_id"] = runId }));

        Assert.True(IsError(response));
        Assert.Equal("run_not_found", Payload(response).Value<string>("error"));
    }

    [Fact]
    public void ARunWithoutARecordedResultHasNoResultPage() {
        host.AddRun("abc123def456", response: "{\"status\":\"ok\"}");

        var run = Payload(Single(ToolCall(1, "get_run", new JObject { ["run_id"] = "abc123def456" })));

        Assert.Null(run["result_page"]);
        Assert.Equal(JTokenType.Null, run["script"].Type);
    }
}
