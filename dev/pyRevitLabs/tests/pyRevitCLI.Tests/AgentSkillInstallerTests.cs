using System.Diagnostics;
using pyRevitCLI;
using pyRevitLabs.Common;
using pyRevitLabs.Json.Linq;

namespace pyRevitCLI.Tests;

[Collection(CliGlobalState.Name)]
[Trait("Environment", "HostFree")]
[Trait("Level", "Unit")]
public class AgentSkillInstallerTests : IDisposable {
    private readonly string previousDirectory = Environment.CurrentDirectory;
    private readonly string temp = Directory.CreateTempSubdirectory("pyrevit-skill-install-").FullName;
    private readonly string shipped;
    private readonly string project;
    private readonly string home;
    private readonly List<string> junctions = new List<string>();

    public AgentSkillInstallerTests() {
        shipped = Directory.CreateDirectory(Path.Combine(temp, "shipped")).FullName;
        project = Directory.CreateDirectory(Path.Combine(temp, "project")).FullName;
        home = Directory.CreateDirectory(Path.Combine(temp, "home")).FullName;
        Environment.CurrentDirectory = project;
        WriteShipped("alpha", "Use when testing alpha.", "alpha body");
        WriteShipped("beta", "Use when testing beta.", "beta body");
        File.WriteAllText(Path.Combine(shipped, "alpha", "extra.md"), "extra");
        File.WriteAllText(Path.Combine(shipped, "alpha", "notes.txt"), "not markdown");
    }

    public void Dispose() {
        Environment.CurrentDirectory = previousDirectory;
        foreach (var junction in junctions.Where(Directory.Exists))
            Directory.Delete(junction);
        Directory.Delete(temp, recursive: true);
    }

    private void WriteShipped(string name, string description, string body) {
        var directory = Directory.CreateDirectory(Path.Combine(shipped, name)).FullName;
        File.WriteAllText(Path.Combine(directory, "SKILL.md"), $"---\nname: {name}\ndescription: {description}\n---\n{body}\n");
    }

    private string Skills(string root, params string[] parts) => Path.Combine(new[] { root }.Concat(parts).ToArray());

    private SkillsReport Install(string targets = "agents", string scope = "project", bool force = false, bool prefix = false) =>
        PyRevitAgentSkillInstaller.Install(PyRevitAgentSkillInstaller.ParseTargets(targets), scope, project, home, shipped, force, prefix);

    private SkillsReport Status(string targets = "agents", string scope = "project") =>
        PyRevitAgentSkillInstaller.Status(PyRevitAgentSkillInstaller.ParseTargets(targets), scope, project, home, shipped);

    private SkillsReport Uninstall(string targets = "agents", string scope = "project") =>
        PyRevitAgentSkillInstaller.Uninstall(PyRevitAgentSkillInstaller.ParseTargets(targets), scope, project, home);

    private static string StateOf(SkillsReport report, string skill) => report.Actions.Single(action => action.Skill == skill).State;

    [Fact]
    public void InstallCopiesMarkdownFilesAndWritesTheMarkerIntoTheAgentsFolder() {
        var report = Install();

        Assert.Equal("installed", StateOf(report, "alpha"));
        var alpha = Skills(project, ".agents", "skills", "alpha");
        Assert.True(File.Exists(Path.Combine(alpha, "SKILL.md")));
        Assert.Equal("extra", File.ReadAllText(Path.Combine(alpha, "extra.md")));
        Assert.False(File.Exists(Path.Combine(alpha, "notes.txt")));
        var marker = JObject.Parse(File.ReadAllText(Path.Combine(alpha, ".pyrevit-skill.json")));
        Assert.Equal("pyrevit", marker.Value<string>("source"));
        Assert.Matches("^[0-9a-f]{64}$", marker.Value<string>("sha256"));
        Assert.Empty(Directory.GetDirectories(Skills(project, ".agents", "skills"), ".pyrevit-tmp-*"));
    }

    [Fact]
    public void InstallAgainReportsCurrentAndDoesNotRewriteTheFiles() {
        Install();
        var skillFile = Skills(project, ".agents", "skills", "alpha", "SKILL.md");
        var old = new DateTime(2001, 1, 1, 0, 0, 0, DateTimeKind.Utc);
        File.SetLastWriteTimeUtc(skillFile, old);

        var report = Install();

        Assert.Equal("current", StateOf(report, "alpha"));
        Assert.Equal(old, File.GetLastWriteTimeUtc(skillFile));
    }

    [Fact]
    public void InstallRefreshesAStaleOwnedCopy() {
        Install();
        File.WriteAllText(Path.Combine(shipped, "alpha", "extra.md"), "extra v2");
        Assert.Equal("stale", StateOf(Status(), "alpha"));

        var report = Install();

        Assert.Equal("updated", StateOf(report, "alpha"));
        Assert.Equal("extra v2", File.ReadAllText(Skills(project, ".agents", "skills", "alpha", "extra.md")));
        Assert.Equal("current", StateOf(Status(), "alpha"));
        Assert.Empty(Directory.GetDirectories(Skills(project, ".agents", "skills"), ".pyrevit-tmp-*"));
    }

    [Fact]
    public void AFolderWithoutTheMarkerIsSkippedAndLeftUntouched() {
        var foreign = Skills(project, ".agents", "skills", "alpha");
        Directory.CreateDirectory(foreign);
        File.WriteAllText(Path.Combine(foreign, "SKILL.md"), "mine");

        var report = Install(force: true);

        Assert.Equal("foreign", StateOf(report, "alpha"));
        Assert.Equal("installed", StateOf(report, "beta"));
        Assert.Equal("mine", File.ReadAllText(Path.Combine(foreign, "SKILL.md")));
        Assert.Contains(report.Warnings, warning => warning.Contains(foreign));
        Assert.Equal("foreign", StateOf(Status(), "alpha"));
    }

    [Fact]
    public void PrefixInstallsAClashingSkillUnderAPrefixedNameWithTheNameLineRewritten() {
        var foreign = Skills(project, ".agents", "skills", "alpha");
        Directory.CreateDirectory(foreign);
        File.WriteAllText(Path.Combine(foreign, "SKILL.md"), "mine");

        var report = Install(prefix: true);

        Assert.Equal("installed", StateOf(report, "alpha"));
        Assert.Equal("mine", File.ReadAllText(Path.Combine(foreign, "SKILL.md")));
        var prefixed = File.ReadAllText(Skills(project, ".agents", "skills", "pyrevit-alpha", "SKILL.md"));
        Assert.Contains("name: pyrevit-alpha\n", prefixed);
        Assert.DoesNotContain("name: alpha", prefixed);
        Assert.True(Directory.Exists(Skills(project, ".agents", "skills", "beta")));
        Assert.Equal("current", StateOf(Status(), "alpha"));
        Assert.Equal("current", StateOf(Install(prefix: true), "alpha"));
    }

    [Fact]
    public void WithoutPrefixTheInstalledNameIsTheShippedName() {
        Install();

        Assert.True(Directory.Exists(Skills(project, ".agents", "skills", "alpha")));
        Assert.False(Directory.Exists(Skills(project, ".agents", "skills", "pyrevit-alpha")));
    }

    [Fact]
    public void AHandEditedOwnedCopyIsKeptUntilForceRepairsIt() {
        Install();
        var skillFile = Skills(project, ".agents", "skills", "alpha", "SKILL.md");
        File.AppendAllText(skillFile, "my edit");

        Assert.Equal("edited", StateOf(Status(), "alpha"));
        Assert.Equal("edited", StateOf(Install(), "alpha"));
        Assert.Contains("my edit", File.ReadAllText(skillFile));

        Assert.Equal("updated", StateOf(Install(force: true), "alpha"));
        Assert.DoesNotContain("my edit", File.ReadAllText(skillFile));
    }

    [Fact]
    public void StatusReportsMissingForSkillsNotInstalled() {
        var report = Status();

        Assert.All(report.Actions, action => Assert.Equal("missing", action.State));
        Assert.Equal(2, report.Actions.Count);
    }

    [Fact]
    public void UninstallRemovesOnlyOwnedFoldersAndKeepsTheSkillsFolder() {
        Install();
        var skills = Skills(project, ".agents", "skills");
        var foreign = Directory.CreateDirectory(Path.Combine(skills, "mine")).FullName;
        File.WriteAllText(Path.Combine(foreign, "SKILL.md"), "mine");
        Directory.CreateDirectory(Path.Combine(skills, ".pyrevit-tmp-leftover"));

        Uninstall();

        Assert.False(Directory.Exists(Path.Combine(skills, "alpha")));
        Assert.False(Directory.Exists(Path.Combine(skills, "beta")));
        Assert.False(Directory.Exists(Path.Combine(skills, ".pyrevit-tmp-leftover")));
        Assert.True(File.Exists(Path.Combine(foreign, "SKILL.md")));
    }

    [Fact]
    public void UninstallLeavesAFolderWithoutTheMarkerAlone() {
        var foreign = Skills(project, ".agents", "skills", "alpha");
        Directory.CreateDirectory(foreign);
        File.WriteAllText(Path.Combine(foreign, "SKILL.md"), "mine");

        Uninstall();

        Assert.True(File.Exists(Path.Combine(foreign, "SKILL.md")));
    }

    [Theory]
    [InlineData("agents", ".agents/skills")]
    [InlineData("claude", ".claude/skills")]
    [InlineData("copilot", ".github/skills")]
    [InlineData("opencode", ".opencode/skills")]
    [InlineData("antigravity", ".agents/skills")]
    public void ProjectScopeWritesTheClientFolderUnderTheProjectRoot(string target, string folder) {
        Install(target);

        Assert.True(File.Exists(Skills(project, folder.Split('/').Concat(new[] { "alpha", "SKILL.md" }).ToArray())));
    }

    [Theory]
    [InlineData("agents", ".agents/skills")]
    [InlineData("claude", ".claude/skills")]
    [InlineData("copilot", ".copilot/skills")]
    [InlineData("opencode", ".config/opencode/skills")]
    [InlineData("antigravity", ".gemini/config/skills")]
    public void UserScopeWritesTheClientFolderUnderTheProfile(string target, string folder) {
        Install(target, scope: "user");

        Assert.True(File.Exists(Skills(home, folder.Split('/').Concat(new[] { "alpha", "SKILL.md" }).ToArray())));
        Assert.False(Directory.Exists(Skills(project, ".agents")));
    }

    [Fact]
    public void SeveralTargetsAreInstalledAndASharedFolderIsWrittenOnce() {
        var report = Install("agents,antigravity,claude");

        Assert.Equal(4, report.Actions.Count);
        Assert.True(File.Exists(Skills(project, ".claude", "skills", "alpha", "SKILL.md")));
    }

    [Fact]
    public void AnUnknownTargetOrScopeNamesTheValidValues() {
        var target = Assert.Throws<PyRevitException>(() => PyRevitAgentSkillInstaller.ParseTargets("agents,nope"));
        Assert.Contains("nope", target.Message);
        Assert.Contains("opencode", target.Message);

        var scope = Assert.Throws<PyRevitException>(() => Install(scope: "everywhere"));
        Assert.Contains("project", scope.Message);
        Assert.Contains("user", scope.Message);
    }

    [Fact]
    public void ProjectScopeNeedsAnExistingProjectRootAndUserScopeNeedsAProfile() {
        Assert.Throws<PyRevitException>(() =>
            PyRevitAgentSkillInstaller.Install(new[] { "agents" }, "project", Path.Combine(temp, "missing"), home, shipped, false, false));
        Assert.Throws<PyRevitException>(() =>
            PyRevitAgentSkillInstaller.Install(new[] { "agents" }, "user", project, string.Empty, shipped, false, false));
    }

    [Fact]
    public void AShippedFileOverTheLimitIsRefusedAndNothingIsInstalledForThatSkill() {
        File.WriteAllText(Path.Combine(shipped, "alpha", "big.md"), new string('x', 129 * 1024));

        Assert.Throws<PyRevitException>(() => Install());

        Assert.False(Directory.Exists(Skills(project, ".agents", "skills", "alpha")));
        Assert.False(Directory.Exists(Skills(project, ".agents", "skills")) && Directory.GetDirectories(Skills(project, ".agents", "skills"), ".pyrevit-tmp-*").Length > 0);
    }

    [Fact]
    public void ASkillsFolderThatIsAJunctionIsRefused() {
        var elsewhere = Directory.CreateDirectory(Path.Combine(temp, "elsewhere")).FullName;
        Directory.CreateDirectory(Path.Combine(project, ".agents"));
        MakeJunction(Skills(project, ".agents", "skills"), elsewhere);

        Assert.Throws<PyRevitException>(() => Install());

        Assert.Empty(Directory.GetFileSystemEntries(elsewhere));
    }

    [Fact]
    public void AnOwnedFolderThatIsAJunctionIsNeverFollowedOrDeleted() {
        Install();
        var elsewhere = Directory.CreateDirectory(Path.Combine(temp, "elsewhere")).FullName;
        File.WriteAllText(Path.Combine(elsewhere, "keep.md"), "keep");
        var alpha = Skills(project, ".agents", "skills", "alpha");
        Directory.Delete(alpha, recursive: true);
        MakeJunction(alpha, elsewhere);

        Assert.ThrowsAny<Exception>(() => Install());
        Uninstall();

        Assert.True(File.Exists(Path.Combine(elsewhere, "keep.md")));
    }

    [Fact]
    public void ASkillWhoseNameDiffersFromItsFolderIsNotInstalled() {
        Directory.CreateDirectory(Path.Combine(shipped, "gamma"));
        File.WriteAllText(Path.Combine(shipped, "gamma", "SKILL.md"), "---\nname: ../evil\ndescription: x\n---\n");

        var report = Install();

        Assert.DoesNotContain(report.Actions, action => action.Skill == "gamma" && action.State == "installed");
        Assert.False(Directory.Exists(Skills(project, ".agents", "evil")));
    }

    [Fact]
    public void StatusWarnsWhenOneClientReadsTheSameOwnedSkillFromTwoFolders() {
        Install("agents,claude");

        var report = Status();

        Assert.Contains(report.Warnings, warning => warning.Contains("OpenCode") && warning.Contains("alpha"));
    }

    [Fact]
    public void InstallAndStatusWarnAboutAnInstalledDescriptionOverTheLimit() {
        WriteShipped("alpha", new string('d', 241), "alpha body");

        var report = Install();

        Assert.Contains(report.Warnings, warning => warning.Contains("alpha") && warning.Contains("241"));
        Assert.Contains(Status().Warnings, warning => warning.Contains("alpha") && warning.Contains("241"));
    }

    [Fact]
    public void TheShippedPyRevitSkillsInstallAndReportCurrent() {
        var real = PyRevitAgentSkills.ShippedSkillsDir;
        Assert.NotNull(real);
        var targets = new[] { "agents" };

        PyRevitAgentSkillInstaller.Install(targets, "project", project, home, real, false, false);
        var status = PyRevitAgentSkillInstaller.Status(targets, "project", project, home, real);

        Assert.True(status.Actions.Count >= 10);
        Assert.All(status.Actions, action => Assert.Equal("current", action.State));
        Assert.Empty(status.Warnings);
    }

    private void MakeJunction(string link, string target) {
        junctions.Add(link);
        var start = new ProcessStartInfo("cmd.exe", $"/c mklink /J \"{link}\" \"{target}\"") { CreateNoWindow = true, RedirectStandardOutput = true };
        using var process = Process.Start(start);
        process.WaitForExit();
        Assert.Equal(0, process.ExitCode);
    }
}
