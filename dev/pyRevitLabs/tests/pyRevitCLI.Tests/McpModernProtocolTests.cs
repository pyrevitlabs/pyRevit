using System.Collections.Concurrent;
using pyRevitCLI;
using pyRevitLabs.Json;
using pyRevitLabs.Json.Linq;
using static pyRevitCLI.Tests.McpWire;

namespace pyRevitCLI.Tests;

[Collection(CliGlobalState.Name)]
[Trait("Environment", "HostFree")]
[Trait("Level", "Unit")]
public class McpModernProtocolTests : IDisposable {
    private const string SkillsExtensionKey = "io.modelcontextprotocol/skills";

    private readonly FakeAgentHost host = new FakeAgentHost();

    public void Dispose() {
        host.Dispose();
    }

    [Fact]
    public void DiscoverDescribesTheModernServerAndTheSkillsExtension() {
        var result = Single(Modern(1, "server/discover"))["result"];

        AssertComplete(result);
        Assert.Equal(new[] { ModernVersion }, result["supportedVersions"].Values<string>());
        Assert.NotNull(result["capabilities"]["tools"]);
        Assert.NotNull(result["capabilities"]["resources"]);
        Assert.Empty((JObject)result["capabilities"]["extensions"][SkillsExtensionKey]);
        Assert.Equal("pyrevit", result["_meta"]["io.modelcontextprotocol/serverInfo"].Value<string>("name"));
        Assert.Equal("0.0.0-tests", result["_meta"]["io.modelcontextprotocol/serverInfo"].Value<string>("version"));
        Assert.Contains("revit-scripting", result.Value<string>("instructions"));
        Assert.Null(result["protocolVersion"]);
    }

    [Fact]
    public void AnUnsupportedProtocolVersionIsRefusedWithTheSupportedList() {
        var error = Single(Modern(1, "server/discover", meta: Meta("2025-11-25")))["error"];

        Assert.Equal(-32022, error.Value<int>("code"));
        Assert.Equal("Unsupported protocol version", error.Value<string>("message"));
        Assert.Equal(new[] { ModernVersion }, error["data"]["supported"].Values<string>());
        Assert.Equal("2025-11-25", error["data"].Value<string>("requested"));
    }

    [Fact]
    public void AModernRequestMissingARequiredMetaKeyIsInvalid() {
        var noCapabilities = Modern(1, "tools/list", meta: new JObject { [VersionKey] = ModernVersion });
        var noVersion = Modern(2, "tools/list", meta: new JObject { [CapabilitiesKey] = new JObject() });
        var badVersionType = Modern(3, "tools/list", meta: new JObject { [VersionKey] = 5, [CapabilitiesKey] = new JObject() });

        var responses = Serve(noCapabilities, noVersion, badVersionType);

        Assert.Equal(3, responses.Count);
        Assert.All(responses, AssertInvalidParams);
    }

    [Fact]
    public void ModernToolsListCarriesTheEnvelopeAndTheSameTools() {
        var legacy = Single(Legacy(1, "tools/list"))["result"]["tools"];
        var modern = Single(Modern(1, "tools/list"))["result"];

        AssertComplete(modern);
        Assert.True(JToken.DeepEquals(legacy, modern["tools"]));
    }

    [Fact]
    public void ModernToolsCallCarriesResultTypeAndLeavesTheContentAlone() {
        var meta = Meta();
        meta["progressToken"] = "p1";

        var result = Single(Modern(1, "tools/call", new JObject {
            ["name"] = "get_skill",
            ["arguments"] = new JObject { ["name"] = "revit-scripting" },
        }, meta))["result"];

        AssertComplete(result, cached: false);
        Assert.False(result.Value<bool>("isError"));
        Assert.Contains("name: revit-scripting", result["content"][0].Value<string>("text"));
    }

    [Fact]
    public void ModernToolsCallArgumentErrorsKeepTheirJsonRpcCode() {
        AssertInvalidParams(Single(Modern(1, "tools/call", new JObject { ["arguments"] = new JObject() })));
    }

    [Fact]
    public void ModernPingStillAnswers() {
        var result = (JObject)Single(Modern(1, "ping"))["result"];

        Assert.Equal("complete", result.Value<string>("resultType"));
        Assert.Equal(new[] { "resultType", "_meta" }, result.Properties().Select(property => property.Name));
    }

    [Fact]
    public void LegacyPingStillAnswersAnEmptyResult() {
        Assert.Empty(((JObject)Single(Legacy(1, "ping"))["result"]).Properties());
    }

    [Fact]
    public void ModernMethodsThatAreNotImplementedAreNotFound() {
        var responses = Serve(
            Modern(1, "subscriptions/listen"),
            Modern(2, "resources/templates/list"),
            Modern(3, "resources/directory/read", new JObject { ["uri"] = "skill://revit-scripting/" }));

        Assert.All(responses, response => Assert.Equal(-32601, response["error"].Value<int>("code")));
    }

    [Fact]
    public void ModernCancelStopsAModernToolCall() {
        using var release = new ManualResetEventSlim(false);
        using var started = new ManualResetEventSlim(false);
        host.Handler = request => {
            if (request.Value<string>("method") == "run") {
                started.Set();
                release.Wait(Patience);
            }
            return FakeAgentHost.Result(request, new JObject { ["pong"] = true });
        };
        var input = new BlockingCollection<string>();
        var output = new BlockingCollection<string>();
        var serving = Task.Run(() => PyRevitMcpServer.Serve(null, new QueueReader(input), new QueueWriter(output)));

        input.Add(Modern(1, "tools/call", new JObject { ["name"] = "run_modify", ["arguments"] = new JObject { ["script"] = "result = 1" } }).ToString(Formatting.None));
        Assert.True(started.Wait(Patience));
        input.Add(new JObject { ["jsonrpc"] = "2.0", ["method"] = "notifications/cancelled", ["params"] = new JObject { ["requestId"] = 1 } }.ToString(Formatting.None));
        input.Add(Modern(2, "ping").ToString(Formatting.None));
        Assert.True(output.TryTake(out var line, Patience));
        release.Set();
        input.CompleteAdding();
        Assert.True(serving.Wait(Patience));

        Assert.Equal(2, JObject.Parse(line).Value<int>("id"));
        Assert.Empty(output);
    }

    [Fact]
    public void LegacyAndModernRequestsMixInOneProcess() {
        var initializeFirst = Serve(
            Legacy(1, "initialize", new JObject { ["protocolVersion"] = "2025-06-18" }),
            Modern(2, "server/discover"),
            Legacy(3, "tools/list"));
        var modernFirst = Serve(
            Modern(1, "server/discover"),
            Legacy(2, "initialize", new JObject { ["protocolVersion"] = "2025-06-18" }),
            Modern(3, "tools/list"));

        Assert.Equal("2025-06-18", initializeFirst[0]["result"].Value<string>("protocolVersion"));
        Assert.Equal("complete", initializeFirst[1]["result"].Value<string>("resultType"));
        Assert.Null(initializeFirst[2]["result"]["resultType"]);
        Assert.Equal("complete", modernFirst[0]["result"].Value<string>("resultType"));
        Assert.Equal("2025-06-18", modernFirst[1]["result"].Value<string>("protocolVersion"));
        Assert.Null(modernFirst[1]["result"]["resultType"]);
        Assert.Equal("complete", modernFirst[2]["result"].Value<string>("resultType"));
    }

    [Fact]
    public void LegacyClientsDoNotSeeTheSkillsMethods() {
        var responses = Serve(Legacy(1, "skills/list"), Legacy(2, "resources/list"), Legacy(3, "server/discover"));

        Assert.All(responses, response => Assert.Equal(-32601, response["error"].Value<int>("code")));
    }

    [Fact]
    public void EveryModernSuccessResultCarriesTheServerInfoAndLegacyResultsDoNot() {
        var skill = new JObject { ["uri"] = "skill://revit-scripting/SKILL.md" };
        var modern = Serve(
            Modern(1, "ping"),
            Modern(2, "server/discover"),
            Modern(3, "tools/list"),
            Modern(4, "tools/call", new JObject { ["name"] = "get_skill", ["arguments"] = new JObject { ["name"] = "revit-scripting" } }),
            Modern(5, "skills/list"),
            Modern(6, "skills/get", (JObject)skill.DeepClone()),
            Modern(7, "resources/list"),
            Modern(8, "resources/read", (JObject)skill.DeepClone()));
        var legacy = Serve(Legacy(1, "ping"), Legacy(2, "tools/list"));

        Assert.Equal(8, modern.Count);
        foreach (var response in modern) {
            Assert.Null(response["error"]);
            Assert.Equal("pyrevit", response["result"]["_meta"][ServerInfoKey].Value<string>("name"));
            Assert.Equal("0.0.0-tests", response["result"]["_meta"][ServerInfoKey].Value<string>("version"));
        }
        Assert.All(legacy, response => Assert.Null(response["result"]["_meta"]));
    }

    [Fact]
    public void AModernRequestNeedsAStringOrIntegerId() {
        JObject WithId(JToken id) {
            var request = Modern(0, "ping");
            request["id"] = id;
            return request;
        }

        var responses = Serve(WithId(JValue.CreateNull()), WithId(new JValue(1.5)), WithId(new JValue("abc")), WithId(new JValue(7)));

        Assert.Equal(4, responses.Count);
        Assert.Equal(-32600, responses[0]["error"].Value<int>("code"));
        Assert.Equal(-32600, responses[1]["error"].Value<int>("code"));
        Assert.Equal("abc", responses[2].Value<string>("id"));
        Assert.Equal("complete", responses[2]["result"].Value<string>("resultType"));
        Assert.Equal(7, responses[3].Value<int>("id"));
    }

    [Fact]
    public void ALegacyRequestStillAcceptsNullAndFloatIds() {
        var nullId = Legacy(0, "ping");
        nullId["id"] = JValue.CreateNull();
        var floatId = Legacy(0, "ping");
        floatId["id"] = new JValue(1.5);

        var responses = Serve(nullId, floatId);

        Assert.Equal(2, responses.Count);
        Assert.All(responses, response => Assert.Null(response["error"]));
    }

    [Fact]
    public void AProgressTokenAloneDoesNotMakeARequestModern() {
        var meta = new JObject { ["progressToken"] = "p1" };

        var list = Single(Legacy(1, "tools/list", new JObject { ["_meta"] = meta.DeepClone() }))["result"];
        var call = Single(Legacy(2, "tools/call", new JObject {
            ["name"] = "get_skill",
            ["arguments"] = new JObject { ["name"] = "revit-scripting" },
            ["_meta"] = meta.DeepClone(),
        }))["result"];
        var discover = Single(Legacy(3, "server/discover", new JObject { ["_meta"] = meta.DeepClone() }));

        Assert.Equal(new[] { "tools" }, ((JObject)list).Properties().Select(property => property.Name));
        Assert.Equal(new[] { "content", "isError" }, ((JObject)call).Properties().Select(property => property.Name));
        Assert.Equal(-32601, discover["error"].Value<int>("code"));
    }
}
