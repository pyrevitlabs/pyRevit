using pyRevitCLI;
using pyRevitLabs.Common;
using pyRevitLabs.Json.Linq;

namespace pyRevitCLI.Tests;

[CollectionDefinition(Name, DisableParallelization = true)]
public sealed class CliGlobalState {
    public const string Name = "CLI global state";
}

internal sealed class ClientCliRecorder : IDisposable {
    private readonly Action<string, string, bool> previous = PyRevitCLIAgentCmds.ClientCli;

    public ClientCliRecorder() {
        PyRevitCLIAgentCmds.ClientCli = (tool, arguments, ignoreFailure) => Calls.Add(tool + " " + arguments + (ignoreFailure ? " [ignore failure]" : string.Empty));
    }

    public List<string> Calls { get; } = new List<string>();

    public void Dispose() {
        PyRevitCLIAgentCmds.ClientCli = previous;
    }
}

[Collection(CliGlobalState.Name)]
public class McpProjectConfigTests : IDisposable {
    private readonly string previousDirectory = Environment.CurrentDirectory;
    private readonly string project = Directory.CreateTempSubdirectory("pyrevit-mcp-project-").FullName;
    private readonly ClientCliRecorder cli = new ClientCliRecorder();

    public McpProjectConfigTests() {
        Environment.CurrentDirectory = project;
    }

    public void Dispose() {
        cli.Dispose();
        Environment.CurrentDirectory = previousDirectory;
        Directory.Delete(project, recursive: true);
    }

    private JObject Read(params string[] parts) => JObject.Parse(File.ReadAllText(Path.Combine(new[] { project }.Concat(parts).ToArray())));

    private void Write(string text, params string[] parts) {
        var path = Path.Combine(new[] { project }.Concat(parts).ToArray());
        Directory.CreateDirectory(Path.GetDirectoryName(path));
        File.WriteAllText(path, text);
    }

    [Fact]
    public void CursorGetsAnEntryThatRunsThisExecutable() {
        PyRevitCLIAgentCmds.InstallMcp(McpClientKind.Cursor, project: true);

        var entry = Read(".cursor", "mcp.json")["mcpServers"]["pyrevit"];
        Assert.Equal(Environment.ProcessPath, entry.Value<string>("command"));
        Assert.Equal(new[] { "mcp" }, entry["args"].Select(arg => arg.Value<string>()));
    }

    [Fact]
    public void VsCodeGetsAStdioEntryUnderServers() {
        PyRevitCLIAgentCmds.InstallMcp(McpClientKind.VSCode, project: true);

        var entry = Read(".vscode", "mcp.json")["servers"]["pyrevit"];
        Assert.Equal("stdio", entry.Value<string>("type"));
        Assert.Equal(Environment.ProcessPath, entry.Value<string>("command"));
    }

    [Fact]
    public void OpenCodeGetsALocalEntryWithTheCommandAsAnArray() {
        PyRevitCLIAgentCmds.InstallMcp(McpClientKind.OpenCode, project: true);

        var entry = Read("opencode.json")["mcp"]["pyrevit"];
        Assert.Equal("local", entry.Value<string>("type"));
        Assert.Equal(new[] { Environment.ProcessPath, "mcp" }, entry["command"].Select(part => part.Value<string>()));
        Assert.True(entry.Value<bool>("enabled"));
    }

    [Fact]
    public void OpenCodeUpdatesAnExistingJsoncFileInsteadOfCreatingAJsonOne() {
        Write("{}", "opencode.jsonc");

        PyRevitCLIAgentCmds.InstallMcp(McpClientKind.OpenCode, project: true);

        Assert.NotNull(Read("opencode.jsonc")["mcp"]["pyrevit"]);
        Assert.False(File.Exists(Path.Combine(project, "opencode.json")));
    }

    [Fact]
    public void InstallingKeepsOtherServersAndOtherKeys() {
        Write("{\"theme\":\"dark\",\"mcpServers\":{\"other\":{\"command\":\"x\"}}}", ".cursor", "mcp.json");

        PyRevitCLIAgentCmds.InstallMcp(McpClientKind.Cursor, project: true);

        var config = Read(".cursor", "mcp.json");
        Assert.Equal("dark", config.Value<string>("theme"));
        Assert.Equal("x", config["mcpServers"]["other"].Value<string>("command"));
        Assert.NotNull(config["mcpServers"]["pyrevit"]);
    }

    [Fact]
    public void InstallingTwiceLeavesOneEntry() {
        PyRevitCLIAgentCmds.InstallMcp(McpClientKind.Cursor, project: true);
        PyRevitCLIAgentCmds.InstallMcp(McpClientKind.Cursor, project: true);

        Assert.Single(((JObject)Read(".cursor", "mcp.json")["mcpServers"]).Properties());
    }

    [Fact]
    public void UninstallingRemovesOnlyThePyrevitEntry() {
        Write("{\"mcpServers\":{\"other\":{\"command\":\"x\"},\"pyrevit\":{\"command\":\"y\"}}}", ".cursor", "mcp.json");

        PyRevitCLIAgentCmds.UninstallMcp(McpClientKind.Cursor, project: true);

        var servers = (JObject)Read(".cursor", "mcp.json")["mcpServers"];
        Assert.Null(servers["pyrevit"]);
        Assert.NotNull(servers["other"]);
    }

    [Fact]
    public void UninstallingWithoutAConfigCreatesNothing() {
        foreach (var client in new[] { McpClientKind.Cursor, McpClientKind.VSCode, McpClientKind.OpenCode })
            PyRevitCLIAgentCmds.UninstallMcp(client, project: true);

        Assert.Empty(Directory.GetFileSystemEntries(project));
    }

    [Fact]
    public void AFileWithCommentsIsRefusedAndLeftUntouched() {
        var original = "{\n  // keep me\n  \"mcpServers\": {}\n}";
        Write(original, ".cursor", "mcp.json");

        var error = Assert.Throws<PyRevitException>(() => PyRevitCLIAgentCmds.InstallMcp(McpClientKind.Cursor, project: true));

        Assert.Contains("comments", error.Message);
        Assert.Equal(original, File.ReadAllText(Path.Combine(project, ".cursor", "mcp.json")));
    }

    [Fact]
    public void ASlashPairInsideAStringIsNotAComment() {
        Write("{\"mcpServers\":{\"remote\":{\"url\":\"https://example.com/mcp\"}}}", ".cursor", "mcp.json");

        PyRevitCLIAgentCmds.InstallMcp(McpClientKind.Cursor, project: true);

        Assert.Equal("https://example.com/mcp", Read(".cursor", "mcp.json")["mcpServers"]["remote"].Value<string>("url"));
    }

    [Fact]
    public void AnUnparseableFileIsRefused() {
        Write("{ not json", ".cursor", "mcp.json");

        var error = Assert.Throws<PyRevitException>(() => PyRevitCLIAgentCmds.InstallMcp(McpClientKind.Cursor, project: true));

        Assert.Contains("Could not parse", error.Message);
    }

    [Fact]
    public void ClaudeIsRegisteredThroughItsOwnToolAtTheRequestedScope() {
        PyRevitCLIAgentCmds.InstallMcp(McpClientKind.Claude, project: false);
        PyRevitCLIAgentCmds.InstallMcp(McpClientKind.Claude, project: true);

        Assert.Equal(new[] {
            "claude mcp remove --scope user pyrevit [ignore failure]",
            "claude mcp add --scope user pyrevit -- \"" + Environment.ProcessPath + "\" mcp",
            "claude mcp remove --scope project pyrevit [ignore failure]",
            "claude mcp add --scope project pyrevit -- \"" + Environment.ProcessPath + "\" mcp",
        }, cli.Calls);
    }

    [Fact]
    public void CodexIsRegisteredThroughItsOwnTool() {
        PyRevitCLIAgentCmds.InstallMcp(McpClientKind.Codex, project: false);

        Assert.Equal(new[] {
            "codex mcp remove pyrevit [ignore failure]",
            "codex mcp add pyrevit -- \"" + Environment.ProcessPath + "\" mcp",
        }, cli.Calls);
    }

    [Fact]
    public void ClaudeAndCodexAreUnregisteredThroughTheirOwnTool() {
        PyRevitCLIAgentCmds.UninstallMcp(McpClientKind.Claude, project: false);
        PyRevitCLIAgentCmds.UninstallMcp(McpClientKind.Claude, project: true);
        PyRevitCLIAgentCmds.UninstallMcp(McpClientKind.Codex, project: false);

        Assert.Equal(new[] {
            "claude mcp remove --scope user pyrevit",
            "claude mcp remove --scope project pyrevit",
            "codex mcp remove pyrevit",
        }, cli.Calls);
    }

    [Fact]
    public void CodexHasNoProjectScopeAndRejectsIt() {
        var error = Assert.Throws<PyRevitException>(() => PyRevitCLIAgentCmds.InstallMcp(McpClientKind.Codex, project: true));

        Assert.Contains("--project", error.Message);
        Assert.Empty(cli.Calls);
    }
}

[Collection(CliGlobalState.Name)]
public class McpOwnedUninstallTests : IDisposable {
    private readonly string root = Directory.CreateTempSubdirectory("pyrevit-mcp-profile-").FullName;
    private readonly string thisExecutable = Environment.ProcessPath;
    private readonly ClientCliRecorder cli = new ClientCliRecorder();
    private const string OtherInstall = @"C:\Other Install\bin\pyrevit.exe";

    public void Dispose() {
        cli.Dispose();
        Directory.Delete(root, recursive: true);
    }

    private string Home(string name = "home") => Path.Combine(root, name);

    private string AppData(string name = "home") => Path.Combine(Home(name), "AppData", "Roaming");

    private string CursorConfig(string name = "home") => Path.Combine(Home(name), ".cursor", "mcp.json");

    private string VsCodeConfig(string name = "home") => Path.Combine(AppData(name), "Code", "User", "mcp.json");

    private string OpenCodeConfig(string name = "home") => Path.Combine(Home(name), ".config", "opencode", "opencode.json");

    private static void Write(string path, string text) {
        Directory.CreateDirectory(Path.GetDirectoryName(path));
        File.WriteAllText(path, text);
    }

    private void RegisterEverywhere(string command, string name = "home") {
        var escaped = Quoted(command);
        Write(CursorConfig(name), "{\"mcpServers\":{\"other\":{\"command\":\"x\"},\"pyrevit\":{\"command\":" + escaped + "}}}");
        Write(VsCodeConfig(name), "{\"servers\":{\"other\":{\"command\":\"x\"},\"pyrevit\":{\"type\":\"stdio\",\"command\":" + escaped + "}}}");
        Write(OpenCodeConfig(name), "{\"mcp\":{\"other\":{\"command\":[\"x\"]},\"pyrevit\":{\"type\":\"local\",\"command\":[" + escaped + ",\"mcp\"]}}}");
    }

    private static string Quoted(string value) => pyRevitLabs.Json.JsonConvert.ToString(value);

    private static JObject Read(string path) => JObject.Parse(File.ReadAllText(path));

    private void Uninstall(string name = "home") {
        PyRevitCLIAgentCmds.UninstallMcpFromAllClients(ownedOnly: true, Home(name), AppData(name));
    }

    [Fact]
    public void RemovesTheRegistrationsOfThisInstallAndKeepsOtherServers() {
        RegisterEverywhere(thisExecutable);

        Uninstall();

        Assert.Null(Read(CursorConfig())["mcpServers"]["pyrevit"]);
        Assert.Null(Read(VsCodeConfig())["servers"]["pyrevit"]);
        Assert.Null(Read(OpenCodeConfig())["mcp"]["pyrevit"]);
        Assert.NotNull(Read(CursorConfig())["mcpServers"]["other"]);
        Assert.NotNull(Read(VsCodeConfig())["servers"]["other"]);
        Assert.NotNull(Read(OpenCodeConfig())["mcp"]["other"]);
    }

    [Fact]
    public void KeepsTheRegistrationsOfAnotherInstall() {
        RegisterEverywhere(OtherInstall);

        Uninstall();

        Assert.NotNull(Read(CursorConfig())["mcpServers"]["pyrevit"]);
        Assert.NotNull(Read(VsCodeConfig())["servers"]["pyrevit"]);
        Assert.NotNull(Read(OpenCodeConfig())["mcp"]["pyrevit"]);
    }

    [Fact]
    public void ComparesThePathIgnoringCaseAndDotSegments() {
        var directory = Path.GetDirectoryName(thisExecutable);
        var spelled = Path.Combine(directory, "..", Path.GetFileName(directory), Path.GetFileName(thisExecutable)).ToUpperInvariant();
        RegisterEverywhere(spelled);

        Uninstall();

        Assert.Null(Read(CursorConfig())["mcpServers"]["pyrevit"]);
    }

    [Fact]
    public void KeepsAnEntryWhoseCommandCannotBeRead() {
        Write(CursorConfig(), "{\"mcpServers\":{\"pyrevit\":{}}}");

        Uninstall();

        Assert.NotNull(Read(CursorConfig())["mcpServers"]["pyrevit"]);
    }

    [Fact]
    public void NeverTouchesAnotherProfile() {
        RegisterEverywhere(thisExecutable, "alice");
        RegisterEverywhere(thisExecutable, "bob");
        var bobsFiles = new[] { CursorConfig("bob"), VsCodeConfig("bob"), OpenCodeConfig("bob") };
        var before = bobsFiles.Select(File.ReadAllBytes).ToList();

        Uninstall("alice");

        Assert.Null(Read(CursorConfig("alice"))["mcpServers"]["pyrevit"]);
        for (var index = 0; index < bobsFiles.Length; index++)
            Assert.Equal(before[index], File.ReadAllBytes(bobsFiles[index]));
    }

    [Fact]
    public void SkipsAConfigWithCommentsWithoutStoppingTheOthers() {
        var commented = "{\n  // mine\n  \"mcpServers\": {\"pyrevit\": {\"command\": " + Quoted(thisExecutable) + "}}\n}";
        Write(CursorConfig(), commented);
        Write(VsCodeConfig(), "{\"servers\":{\"pyrevit\":{\"command\":" + Quoted(thisExecutable) + "}}}");

        Uninstall();

        Assert.Equal(commented, File.ReadAllText(CursorConfig()));
        Assert.Null(Read(VsCodeConfig())["servers"]["pyrevit"]);
    }

    [Fact]
    public void AMissingProfileCreatesNothing() {
        Directory.CreateDirectory(Home());

        Uninstall();

        Assert.Empty(Directory.GetFileSystemEntries(Home()));
    }

    [Fact]
    public void LeavesClientsManagedByTheirOwnToolAloneWhenTheyNameAnotherInstall() {
        var claude = Path.Combine(Home(), ".claude.json");
        var codex = Path.Combine(Home(), ".codex", "config.toml");
        Write(claude, "{\"mcpServers\":{\"pyrevit\":{\"command\":" + Quoted(OtherInstall) + "}}}");
        Write(codex, "[mcp_servers.pyrevit]\ncommand = '" + OtherInstall + "'\n");
        var before = new[] { File.ReadAllBytes(claude), File.ReadAllBytes(codex) };

        Uninstall();

        Assert.Equal(before[0], File.ReadAllBytes(claude));
        Assert.Equal(before[1], File.ReadAllBytes(codex));
        Assert.Empty(cli.Calls);
    }

    [Fact]
    public void RunsNoToolForClientsThatHaveNoConfigInTheProfile() {
        Directory.CreateDirectory(Home());

        Uninstall();

        Assert.Empty(cli.Calls);
    }
}
