using pyRevitCLI;
using pyRevitLabs.Json;
using pyRevitLabs.Json.Linq;

namespace pyRevitCLI.Tests;

[Collection(CliGlobalState.Name)]
[Trait("Environment", "HostFree")]
[Trait("Level", "Unit")]
public class McpLegacyGoldenTests : IDisposable {
    private const string InstructionsPlaceholder = "<instructions>";

    private readonly FakeAgentHost host = new FakeAgentHost();

    public void Dispose() {
        host.Dispose();
    }

    public static IEnumerable<object[]> Versions() {
        yield return new object[] { "2025-06-18" };
        yield return new object[] { "2025-03-26" };
        yield return new object[] { "2024-11-05" };
    }

    [Theory]
    [MemberData(nameof(Versions))]
    public void LegacyClientsGetTheSameBytesAsBeforeTheModernRevision(string version) {
        var input = string.Join("\n",
            "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"" + version + "\",\"capabilities\":{},\"clientInfo\":{\"name\":\"t\",\"version\":\"1\"}}}",
            "{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}",
            "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"ping\"}",
            "{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/list\"}",
            "{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"server/discover\"}",
            "{\"jsonrpc\":\"2.0\",\"id\":5,\"method\":\"skills/list\"}");
        var output = new StringWriter();
        PyRevitMcpServer.Serve(null, new StringReader(input), output);

        var instructions = PyRevitAgentSkills.Instructions(PyRevitAgentSkills.Load());
        var actual = output.ToString().Split('\n', StringSplitOptions.RemoveEmptyEntries).Select(line => {
            var message = JObject.Parse(line);
            var served = message["result"]?["instructions"];
            if (served != null) {
                Assert.Equal(instructions, served.Value<string>());
                message["result"]["instructions"] = InstructionsPlaceholder;
            }
            return message.ToString(Formatting.None);
        }).ToList();

        var path = Path.Combine(AppContext.BaseDirectory, "Goldens", "mcp-legacy-" + version + ".jsonl");
        Assert.Equal(File.ReadAllLines(path), actual);
    }
}
