using System.Text;
using pyRevitCLI;
using pyRevitLabs.Json.Linq;
using static pyRevitCLI.Tests.McpWire;

namespace pyRevitCLI.Tests;

[Collection(CliGlobalState.Name)]
[Trait("Environment", "HostFree")]
[Trait("Level", "Unit")]
public class SkillsExtensionTests : IDisposable {
    private readonly FakeAgentHost host = new FakeAgentHost();

    public void Dispose() {
        host.Dispose();
    }

    private static JObject Uri(string uri) => new JObject { ["uri"] = uri };

    private static List<string> Names(SkillsExtension extension) =>
        extension.List()["skills"].Select(skill => skill["frontmatter"].Value<string>("name")).ToList();

    [RepoSkillsFact]
    public void EveryShippedSkillIsServedWithExactlyANameAndADescription() {
        var served = new SkillsExtension(RepoSkills.Directory).List()["skills"];
        var shipped = Directory.GetDirectories(RepoSkills.Directory).Count(path => File.Exists(Path.Combine(path, "SKILL.md")));

        Assert.Equal(shipped, served.Count());
        Assert.All(served, skill => Assert.Equal(
            new[] { "name", "description" },
            skill["frontmatter"].Children<JProperty>().Select(property => property.Name)));
    }

    [RepoSkillsFact]
    public void EveryShippedSkillIsListedWithAVerifiableManifest() {
        var skills = (JArray)Single(Modern(1, "skills/list"))["result"]["skills"];

        Assert.NotEmpty(skills);
        foreach (var skill in skills) {
            var name = skill["frontmatter"].Value<string>("name");
            Assert.Equal($"skill://{name}/SKILL.md", skill.Value<string>("uri"));
            var manifest = (JArray)skill["resources"];
            Assert.Equal(manifest.Count, manifest.Select(entry => entry.Value<string>("uri")).Distinct().Count());
            Assert.Contains(manifest, entry => entry.Value<string>("uri") == skill.Value<string>("uri"));
            foreach (var entry in manifest) {
                var read = Single(Modern(2, "resources/read", Uri(entry.Value<string>("uri"))))["result"];
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
        var got = Single(Modern(1, "skills/get", Uri("skill://revit-scripting/SKILL.md")))["result"];
        var list = (JArray)Single(Modern(2, "skills/list"))["result"]["skills"];
        var responses = Serve(
            Modern(3, "skills/get", Uri("skill://no-such-skill/SKILL.md")),
            Modern(4, "resources/read", Uri("skill://revit-scripting/missing.md")),
            Modern(5, "resources/read", Uri("skill://revit-scripting/../INSTRUCTIONS.md")),
            Modern(6, "resources/read", Uri("file:///etc/passwd")),
            Modern(7, "skills/list", new JObject { ["cursor"] = "abc" }),
            Modern(8, "resources/list", new JObject { ["cursor"] = "abc" }));

        AssertComplete(got);
        Assert.True(JToken.DeepEquals(list.Single(skill => skill.Value<string>("uri") == "skill://revit-scripting/SKILL.md"), got["skill"]));
        Assert.All(responses, AssertInvalidParams);
        Assert.Equal("skill://no-such-skill/SKILL.md", responses[0]["error"]["data"].Value<string>("uri"));
    }

    [Fact]
    public void AMissingOrNonStringUriIsAnInvalidParameter() {
        var responses = Serve(
            Modern(1, "skills/get"),
            Modern(2, "resources/read"),
            Modern(3, "resources/read", new JObject { ["uri"] = 5 }),
            Modern(4, "skills/get", new JObject { ["uri"] = new JObject() }));

        Assert.All(responses, AssertInvalidParams);
        Assert.All(responses, response => Assert.Contains("uri is required", response["error"].Value<string>("message")));
        Assert.All(responses, response => Assert.Null(response["error"]["data"]));
    }

    [RepoSkillsFact]
    public void ResourcesListHoldsEveryManifestFileOnceAndNamesSkillEntriesAfterTheirFrontMatter() {
        var result = Single(Modern(1, "resources/list"))["result"];
        var list = (JArray)Single(Modern(2, "skills/list"))["result"]["skills"];

        AssertComplete(result);
        Assert.Null(result["nextCursor"]);
        var expected = list.SelectMany(skill => skill["resources"]).Select(entry => entry.Value<string>("uri")).OrderBy(uri => uri, StringComparer.Ordinal).ToList();
        var listed = result["resources"].Select(entry => entry.Value<string>("uri")).OrderBy(uri => uri, StringComparer.Ordinal).ToList();
        Assert.Equal(expected, listed);
        Assert.All(result["resources"], entry => Assert.Equal("text/markdown", entry.Value<string>("mimeType")));
        foreach (var skill in list) {
            var entry = result["resources"].Single(resource => resource.Value<string>("uri") == skill.Value<string>("uri"));
            Assert.Equal(skill["frontmatter"].Value<string>("name"), entry.Value<string>("name"));
            Assert.Equal(skill["frontmatter"].Value<string>("description"), entry.Value<string>("description"));
        }
        var other = result["resources"].First(resource => !resource.Value<string>("uri").EndsWith("/SKILL.md"));
        Assert.Contains("/", other.Value<string>("name"));
        Assert.Null(other["description"]);
    }

    [Fact]
    public void UserSkillsAreNeverListedOrReachableByUri() {
        var userSkill = Path.Combine(host.AgentDir, "skills", "planted-user-skill");
        Directory.CreateDirectory(userSkill);
        File.WriteAllText(Path.Combine(userSkill, "SKILL.md"), TempSkills.Skill("planted-user-skill"));

        var list = Single(Modern(1, "skills/list"))["result"]["skills"];
        var read = Single(Modern(2, "resources/read", Uri("skill://planted-user-skill/SKILL.md")));
        var get = Single(Modern(3, "skills/get", Uri("skill://planted-user-skill/SKILL.md")));

        Assert.DoesNotContain(list, skill => skill.Value<string>("uri").Contains("planted-user-skill"));
        AssertInvalidParams(read);
        AssertInvalidParams(get);
    }

    [Fact]
    public void ABomAndCrlfRoundTripByteForByte() {
        using var skills = new TempSkills();
        var bom = new byte[] { 0xEF, 0xBB, 0xBF };
        var skill = bom.Concat(Encoding.UTF8.GetBytes("---\r\nname: crlf-skill\r\ndescription: café ✓\r\n---\r\nBody\r\n")).ToArray();
        var extra = Encoding.UTF8.GetBytes("# Extra\r\nline\r\n");
        skills.Plant("crlf-skill", skill, ("notes/extra.md", extra));
        var extension = new SkillsExtension(skills.Root);

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

    [Fact]
    public void ASimpleQuotedOrPlainValueIsServedWithTheContentAYamlParserWouldProduce() {
        using var skills = new TempSkills();
        skills.Plant("plain", "---\nname: plain\ndescription: Use when it's fine, e.g. \"x\" and a:b\n---\n");
        skills.Plant("double", "---\nname: double\ndescription: \"Use when double: quoted # not a comment\"\n---\n");
        skills.Plant("single", "---\nname: single\ndescription: 'Use when single \"quoted\"'\n---\n");

        var descriptions = new SkillsExtension(skills.Root).List()["skills"]
            .ToDictionary(skill => skill["frontmatter"].Value<string>("name"), skill => skill["frontmatter"].Value<string>("description"));

        Assert.Equal("Use when it's fine, e.g. \"x\" and a:b", descriptions["plain"]);
        Assert.Equal("Use when double: quoted # not a comment", descriptions["double"]);
        Assert.Equal("Use when single \"quoted\"", descriptions["single"]);
    }

    [Fact]
    public void AMissingSkillsFolderIsAnEmptyList() {
        Assert.Empty(new SkillsExtension(null).List()["skills"]);
        Assert.Empty(new SkillsExtension(Path.Combine(Path.GetTempPath(), "pyrevit-no-such-folder-" + Guid.NewGuid())).List()["skills"]);
    }

    [Theory]
    [InlineData("double-quoted unicode escape", "---\nname: bad\ndescription: \"Use \\u0052evit\"\n---\n")]
    [InlineData("double-quoted escaped quote", "---\nname: bad\ndescription: \"say \\\"hi\\\"\"\n---\n")]
    [InlineData("double-quoted backslash", "---\nname: bad\ndescription: \"a\\nb\"\n---\n")]
    [InlineData("double-quoted embedded quote", "---\nname: bad\ndescription: \"a\" b\"\n---\n")]
    [InlineData("single-quoted doubled quote", "---\nname: bad\ndescription: 'it''s'\n---\n")]
    [InlineData("quote never closed", "---\nname: bad\ndescription: \"open\n---\n")]
    [InlineData("text after the closing quote", "---\nname: bad\ndescription: \"a\" b\n---\n")]
    [InlineData("tag", "---\nname: bad\ndescription: !!str guidance\n---\n")]
    [InlineData("anchor", "---\nname: bad\ndescription: &a x\n---\n")]
    [InlineData("alias", "---\nname: bad\ndescription: *a\n---\n")]
    [InlineData("directive character", "---\nname: bad\ndescription: %x\n---\n")]
    [InlineData("reserved at sign", "---\nname: bad\ndescription: @x\n---\n")]
    [InlineData("reserved backtick", "---\nname: bad\ndescription: `x\n---\n")]
    [InlineData("explicit key indicator", "---\nname: bad\ndescription: ? x\n---\n")]
    [InlineData("nested mapping", "---\nname: bad\ndescription: a: b\n---\n")]
    [InlineData("trailing colon", "---\nname: bad\ndescription: a:\n---\n")]
    [InlineData("indented", "---\nname: bad\ndescription: x\nmetadata:\n  author: y\n---\n")]
    [InlineData("list item", "---\nname: bad\ndescription: x\ntags:\n- a\n---\n")]
    [InlineData("comment line", "---\nname: bad\n# note\ndescription: x\n---\n")]
    [InlineData("empty value", "---\nname: bad\ndescription: x\nlicense:\n---\n")]
    [InlineData("folded scalar", "---\nname: bad\ndescription: >\n  text\n---\n")]
    [InlineData("literal scalar", "---\nname: bad\ndescription: |\n  text\n---\n")]
    [InlineData("flow sequence", "---\nname: bad\ndescription: x\ntags: [a, b]\n---\n")]
    [InlineData("flow mapping", "---\nname: bad\ndescription: x\nmeta: {a: b}\n---\n")]
    [InlineData("trailing comment", "---\nname: bad\ndescription: x # note\n---\n")]
    [InlineData("duplicate key", "---\nname: bad\ndescription: x\ndescription: y\n---\n")]
    [InlineData("duplicate key in another case", "---\nname: bad\ndescription: x\nDescription: y\n---\n")]
    [InlineData("upper case name key", "---\nNAME: bad\ndescription: x\n---\n")]
    [InlineData("upper case description key", "---\nname: bad\nDESCRIPTION: x\n---\n")]
    [InlineData("missing description", "---\nname: bad\n---\n")]
    [InlineData("quoted empty description", "---\nname: bad\ndescription: \"\"\n---\n")]
    [InlineData("name differing from the folder", "---\nname: other\ndescription: x\n---\n")]
    [InlineData("front matter never closed", "---\nname: bad\ndescription: x\n")]
    public void ASkillThatTheFlatFrontMatterCannotRepresentFaithfullyIsSkippedWithAStderrLine(string reason, string skill) {
        using var skills = new TempSkills();
        skills.Plant("bad", skill);
        skills.Plant("good", TempSkills.Skill("good"));
        using var console = new ConsoleCapture();

        var names = Names(new SkillsExtension(skills.Root));

        Assert.Equal(new[] { "good" }, names);
        Assert.Contains("bad", console.Error);
        Assert.Single(console.Error.Split('\n', StringSplitOptions.RemoveEmptyEntries));
        Assert.Equal(string.Empty, console.Out);
        Assert.False(string.IsNullOrEmpty(reason));
    }

    [Fact]
    public void ASkillHoldingAFileThatIsNotServedIsSkippedBecauseItsManifestWouldBeIncomplete() {
        using var skills = new TempSkills();
        skills.Plant("script", TempSkills.Skill("script"), ("tool.py", Encoding.UTF8.GetBytes("print(1)")));
        skills.Plant("nested", TempSkills.Skill("nested"), ("deep/more/data.json", Encoding.UTF8.GetBytes("{}")));
        skills.Plant("notes", TempSkills.Skill("notes"), ("deep/extra.md", Encoding.UTF8.GetBytes("# ok\n")));
        using var console = new ConsoleCapture();

        var names = Names(new SkillsExtension(skills.Root));

        Assert.Equal(new[] { "notes" }, names);
        Assert.Contains("script", console.Error);
        Assert.Contains("nested", console.Error);
        Assert.Equal(string.Empty, console.Out);
    }

    [Fact]
    public void ASkillOverTheFileCountOrSizeLimitIsSkippedWithAStderrLine() {
        using var skills = new TempSkills();
        var many = Enumerable.Range(0, 256).Select(index => ($"extra/{index}.md", Encoding.UTF8.GetBytes("x"))).ToArray();
        var exactlyAtTheCap = Enumerable.Range(0, 255).Select(index => ($"extra/{index}.md", Encoding.UTF8.GetBytes("x"))).ToArray();
        skills.Plant("too-many", TempSkills.Skill("too-many"), many);
        skills.Plant("at-the-cap", TempSkills.Skill("at-the-cap"), exactlyAtTheCap);
        skills.Plant("too-big", TempSkills.Skill("too-big"), ("big.md", new byte[128 * 1024 + 1]));
        skills.Plant("max-size", TempSkills.Skill("max-size"), ("big.md", Enumerable.Repeat((byte)'a', 128 * 1024).ToArray()));
        using var console = new ConsoleCapture();

        var names = Names(new SkillsExtension(skills.Root));

        Assert.Equal(new[] { "at-the-cap", "max-size" }, names);
        Assert.Contains("too-many", console.Error);
        Assert.Contains("too-big", console.Error);
        Assert.Equal(string.Empty, console.Out);
    }

    [Fact]
    public void AFileThatIsNotUtf8SkipsItsSkillWithAStderrLine() {
        using var skills = new TempSkills();
        skills.Plant("broken", TempSkills.Skill("broken"), ("latin.md", new byte[] { 0x63, 0x61, 0x66, 0xE9 }));
        using var console = new ConsoleCapture();

        Assert.Empty(Names(new SkillsExtension(skills.Root)));
        Assert.Contains("broken", console.Error);
        Assert.Equal(string.Empty, console.Out);
    }
}
