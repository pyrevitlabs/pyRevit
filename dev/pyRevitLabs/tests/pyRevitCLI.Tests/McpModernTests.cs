using System.Collections.Concurrent;
using System.Security.Cryptography;
using System.Text;
using pyRevitCLI;
using pyRevitLabs.Json;
using pyRevitLabs.Json.Linq;

namespace pyRevitCLI.Tests;

[Collection(CliGlobalState.Name)]
[Trait("Environment", "HostFree")]
[Trait("Level", "Unit")]
public class McpModernTests : IDisposable {
    private const string Version = "2026-07-28";
    private const string VersionKey = "io.modelcontextprotocol/protocolVersion";
    private const string CapabilitiesKey = "io.modelcontextprotocol/clientCapabilities";
    private const string SkillsExtensionKey = "io.modelcontextprotocol/skills";
    private static readonly TimeSpan Patience = TimeSpan.FromSeconds(10);

    private readonly FakeAgentHost host = new FakeAgentHost();

    public void Dispose() {
        host.Dispose();
    }

    private static JObject Meta(string version = Version) => new JObject {
        [VersionKey] = version,
        [CapabilitiesKey] = new JObject(),
    };

    private static JObject Modern(int id, string method, JObject parameters = null, JObject meta = null) {
        parameters ??= new JObject();
        parameters["_meta"] = meta ?? Meta();
        return new JObject { ["jsonrpc"] = "2.0", ["id"] = id, ["method"] = method, ["params"] = parameters };
    }

    private static JObject Legacy(int id, string method, JObject parameters = null) {
        var request = new JObject { ["jsonrpc"] = "2.0", ["id"] = id, ["method"] = method };
        if (parameters != null)
            request["params"] = parameters;
        return request;
    }

    private static List<JObject> Serve(params JObject[] lines) {
        var output = new StringWriter();
        PyRevitMcpServer.Serve(null, new StringReader(string.Join("\n", lines.Select(line => line.ToString(Formatting.None)))), output);
        return output.ToString().Split('\n', StringSplitOptions.RemoveEmptyEntries).Select(line => JObject.Parse(line)).ToList();
    }

    private static JObject Single(JObject line) => Assert.Single(Serve(line));

    private static string Sha256(byte[] bytes) => "sha256:" + Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();

    private static void AssertComplete(JToken result, bool cached = true) {
        Assert.Equal("complete", result.Value<string>("resultType"));
        if (!cached)
            return;
        Assert.True(result.Value<long>("ttlMs") > 0);
        Assert.Equal("public", result.Value<string>("cacheScope"));
    }

    private static void AssertInvalidParams(JObject response) => Assert.Equal(-32602, response["error"].Value<int>("code"));

    [Fact]
    public void DiscoverDescribesTheModernServerAndTheSkillsExtension() {
        var result = Single(Modern(1, "server/discover"))["result"];

        AssertComplete(result);
        Assert.Equal(new[] { Version }, result["supportedVersions"].Values<string>());
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
        Assert.Equal(new[] { Version }, error["data"]["supported"].Values<string>());
        Assert.Equal("2025-11-25", error["data"].Value<string>("requested"));
    }

    [Fact]
    public void AModernRequestMissingARequiredMetaKeyIsInvalid() {
        var noCapabilities = Modern(1, "tools/list", meta: new JObject { [VersionKey] = Version });
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
        Assert.Single(result.Properties());
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

    [RepoSkillsFact]
    public void EveryShippedSkillIsListedWithItsFrontMatterAndAVerifiableManifest() {
        var skills = (JArray)Single(Modern(1, "skills/list"))["result"]["skills"];
        var shippedNames = Directory.GetDirectories(RepoSkills.Directory)
            .Where(path => File.Exists(Path.Combine(path, "SKILL.md")))
            .Select(path => Path.GetFileName(path))
            .OrderBy(name => name)
            .ToList();

        Assert.Equal(shippedNames, skills.Select(skill => skill["frontmatter"].Value<string>("name")).OrderBy(name => name).ToList());
        foreach (var skill in skills) {
            var name = skill["frontmatter"].Value<string>("name");
            Assert.Equal($"skill://{name}/SKILL.md", skill.Value<string>("uri"));
            var declared = File.ReadAllLines(Path.Combine(RepoSkills.Directory, name, "SKILL.md"))
                .Skip(1)
                .TakeWhile(line => line.Trim() != "---")
                .Where(line => line.IndexOf(':') > 0)
                .Select(line => line.Substring(0, line.IndexOf(':')).Trim())
                .OrderBy(key => key)
                .ToList();
            var served = skill["frontmatter"].Children<JProperty>().Select(property => property.Name).OrderBy(key => key).ToList();
            Assert.Equal(declared, served);
            var manifest = (JArray)skill["resources"];
            Assert.Equal(manifest.Count, manifest.Select(entry => entry.Value<string>("uri")).Distinct().Count());
            Assert.Contains(manifest, entry => entry.Value<string>("uri") == skill.Value<string>("uri"));
            foreach (var entry in manifest) {
                var read = Single(Modern(2, "resources/read", new JObject { ["uri"] = entry.Value<string>("uri") }))["result"];
                AssertComplete(read);
                var content = Assert.Single(read["contents"]);
                var bytes = Encoding.UTF8.GetBytes(content.Value<string>("text"));
                Assert.Equal("text/markdown", content.Value<string>("mimeType"));
                Assert.Equal(entry.Value<string>("uri"), content.Value<string>("uri"));
                Assert.Equal(entry.Value<string>("digest"), Sha256(bytes));
                Assert.Equal(entry.Value<long>("size"), bytes.Length);
                var relative = entry.Value<string>("uri").Substring($"skill://{name}/".Length).Replace('/', Path.DirectorySeparatorChar);
                Assert.Equal(Sha256(File.ReadAllBytes(Path.Combine(RepoSkills.Directory, name, relative))), entry.Value<string>("digest"));
            }
        }
    }

    [RepoSkillsFact]
    public void SkillsGetAnswersForAListedSkillAndRejectsUnknownUris() {
        var got = Single(Modern(1, "skills/get", new JObject { ["uri"] = "skill://revit-scripting/SKILL.md" }))["result"];
        var list = (JArray)Single(Modern(2, "skills/list"))["result"]["skills"];
        var responses = Serve(
            Modern(3, "skills/get", new JObject { ["uri"] = "skill://no-such-skill/SKILL.md" }),
            Modern(4, "resources/read", new JObject { ["uri"] = "skill://revit-scripting/missing.md" }),
            Modern(5, "resources/read", new JObject { ["uri"] = "skill://revit-scripting/../INSTRUCTIONS.md" }),
            Modern(6, "resources/read", new JObject { ["uri"] = "file:///etc/passwd" }),
            Modern(7, "skills/list", new JObject { ["cursor"] = "abc" }),
            Modern(8, "resources/list", new JObject { ["cursor"] = "abc" }));

        AssertComplete(got);
        Assert.True(JToken.DeepEquals(list.Single(skill => skill.Value<string>("uri") == "skill://revit-scripting/SKILL.md"), got["skill"]));
        Assert.All(responses, AssertInvalidParams);
        Assert.Equal("skill://no-such-skill/SKILL.md", responses[0]["error"]["data"].Value<string>("uri"));
    }

    [RepoSkillsFact]
    public void ResourcesListHoldsEveryManifestFileOnce() {
        var result = Single(Modern(1, "resources/list"))["result"];
        var list = (JArray)Single(Modern(2, "skills/list"))["result"]["skills"];

        AssertComplete(result);
        Assert.Null(result["nextCursor"]);
        var expected = list.SelectMany(skill => skill["resources"]).Select(entry => entry.Value<string>("uri")).OrderBy(uri => uri, StringComparer.Ordinal).ToList();
        var listed = result["resources"].Select(entry => entry.Value<string>("uri")).OrderBy(uri => uri, StringComparer.Ordinal).ToList();
        Assert.Equal(expected, listed);
        Assert.All(result["resources"], entry => Assert.Equal("text/markdown", entry.Value<string>("mimeType")));
    }

    [Fact]
    public void UserSkillsAreNeverListedOrReachableByUri() {
        var userSkill = Path.Combine(host.AgentDir, "skills", "planted-user-skill");
        Directory.CreateDirectory(userSkill);
        File.WriteAllText(Path.Combine(userSkill, "SKILL.md"), "---\nname: planted-user-skill\ndescription: x\n---\nbody\n");

        var list = Single(Modern(1, "skills/list"))["result"]["skills"];
        var read = Single(Modern(2, "resources/read", new JObject { ["uri"] = "skill://planted-user-skill/SKILL.md" }));
        var get = Single(Modern(3, "skills/get", new JObject { ["uri"] = "skill://planted-user-skill/SKILL.md" }));

        Assert.DoesNotContain(list, skill => skill.Value<string>("uri").Contains("planted-user-skill"));
        AssertInvalidParams(read);
        AssertInvalidParams(get);
    }

    private static void Plant(string root, string directory, byte[] skill, params (string Relative, byte[] Bytes)[] extra) {
        var path = Directory.CreateDirectory(Path.Combine(root, directory)).FullName;
        File.WriteAllBytes(Path.Combine(path, "SKILL.md"), skill);
        foreach (var (relative, bytes) in extra) {
            Directory.CreateDirectory(Path.GetDirectoryName(Path.Combine(path, relative)));
            File.WriteAllBytes(Path.Combine(path, relative), bytes);
        }
    }

    [Fact]
    public void ABomAndCrlfRoundTripByteForByte() {
        var directory = Directory.CreateTempSubdirectory("pyrevit-skills-ext-");
        try {
            var bom = new byte[] { 0xEF, 0xBB, 0xBF };
            var skill = bom.Concat(Encoding.UTF8.GetBytes("---\r\nname: crlf-skill\r\ndescription: café ✓\r\n---\r\nBody\r\n")).ToArray();
            var extra = Encoding.UTF8.GetBytes("# Extra\r\nline\r\n");
            Plant(directory.FullName, "crlf-skill", skill, ("notes/extra.md", extra));
            var extension = new SkillsExtension(directory.FullName);

            var listed = extension.List()["skills"].Single();
            var manifest = listed["resources"].ToDictionary(entry => entry.Value<string>("uri"));
            Assert.Equal("café ✓", listed["frontmatter"].Value<string>("description"));
            Assert.Equal(new[] { "skill://crlf-skill/SKILL.md", "skill://crlf-skill/notes/extra.md" }.OrderBy(uri => uri), manifest.Keys.OrderBy(uri => uri));
            foreach (var (uri, bytes) in new[] { ("skill://crlf-skill/SKILL.md", skill), ("skill://crlf-skill/notes/extra.md", extra) }) {
                var served = Encoding.UTF8.GetBytes(extension.Read(uri)["contents"][0].Value<string>("text"));
                Assert.Equal(bytes, served);
                Assert.Equal(Sha256(bytes), manifest[uri].Value<string>("digest"));
                Assert.Equal(bytes.Length, manifest[uri].Value<long>("size"));
            }
        }
        finally {
            directory.Delete(recursive: true);
        }
    }

    [Fact]
    public void ASkillWhoseNameDiffersFromItsDirectoryIsSkippedAndNotServed() {
        var directory = Directory.CreateTempSubdirectory("pyrevit-skills-ext-");
        try {
            Plant(directory.FullName, "folder-name", Encoding.UTF8.GetBytes("---\nname: other-name\ndescription: x\n---\n"));
            Plant(directory.FullName, "good-skill", Encoding.UTF8.GetBytes("---\nname: good-skill\ndescription: x\n---\n"));
            var extension = new SkillsExtension(directory.FullName);

            var names = extension.List()["skills"].Select(skill => skill["frontmatter"].Value<string>("name")).ToList();
            Assert.Equal(new[] { "good-skill" }, names);
            Assert.Throws<McpRequestException>(() => extension.Read("skill://folder-name/SKILL.md"));
            Assert.Throws<McpRequestException>(() => extension.Get("skill://other-name/SKILL.md"));
        }
        finally {
            directory.Delete(recursive: true);
        }
    }

    [Fact]
    public void AMissingSkillsFolderIsAnEmptyList() {
        Assert.Empty(new SkillsExtension(null).List()["skills"]);
        Assert.Empty(new SkillsExtension(Path.Combine(Path.GetTempPath(), "pyrevit-no-such-folder-" + Guid.NewGuid())).List()["skills"]);
    }

    private sealed class QueueReader : TextReader {
        private readonly BlockingCollection<string> lines;
        private string current = string.Empty;
        private int position;

        public QueueReader(BlockingCollection<string> lines) {
            this.lines = lines;
        }

        public override int Read() {
            if (position == current.Length) {
                if (!lines.TryTake(out var line, Timeout.Infinite))
                    return -1;
                current = line + '\n';
                position = 0;
            }
            return current[position++];
        }
    }

    private sealed class QueueWriter : TextWriter {
        private readonly BlockingCollection<string> lines;

        public QueueWriter(BlockingCollection<string> lines) {
            this.lines = lines;
        }

        public override Encoding Encoding => Encoding.UTF8;

        public override void WriteLine(string value) => lines.Add(value);
    }
}
