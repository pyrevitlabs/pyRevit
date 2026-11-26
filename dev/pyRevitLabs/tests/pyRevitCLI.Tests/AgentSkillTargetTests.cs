using System.Text;
using pyRevitCLI;
using pyRevitLabs.Common;
using pyRevitLabs.Json.Linq;

namespace pyRevitCLI.Tests;

[Trait("Environment", "HostFree")]
[Trait("Level", "Unit")]
public class AgentSkillTargetTests : SkillInstallFixture {
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
        var target = Assert.Throws<PyRevitException>(() => SkillTargets.ParseTargets("agents,nope"));
        Assert.Contains("nope", target.Message);
        Assert.Contains("opencode", target.Message);

        var scope = Assert.Throws<PyRevitException>(() => Context(scope: "everywhere"));
        Assert.Contains("project", scope.Message);
        Assert.Contains("user", scope.Message);
    }

    [Fact]
    public void ThePathOptionBelongsToTheProjectScopeAndBothRootsMustExist() {
        var withPath = Assert.Throws<PyRevitException>(() => SkillContext.Create("agents", "user", project, project, home, shipped));
        Assert.Contains("--path", withPath.Message);
        Assert.Throws<PyRevitException>(() => SkillContext.Create("agents", "project", Path.Combine(temp, "missing"), project, home, shipped));
        Assert.Throws<PyRevitException>(() => SkillContext.Create("agents", "user", null, project, string.Empty, shipped));
        Assert.Equal(Path.GetFullPath(project), SkillContext.Create("agents", "project", null, project, home, shipped).BaseRoot);
    }

    [Fact]
    public void StatusWarnsWhenOneClientReadsTheSameOwnedSkillFromTwoFolders() {
        Install("agents,claude");

        var report = Status();

        Assert.Contains(report.Warnings, warning => warning.Contains("OpenCode") && warning.Contains("alpha"));
    }

    [Fact]
    public void TheOverlapWarningAlsoCatchesAPlainAndAPrefixedCopyOfTheSameSkill() {
        var foreign = Directory.CreateDirectory(Skills(project, ".claude", "skills", "alpha")).FullName;
        File.WriteAllText(Path.Combine(foreign, "SKILL.md"), "mine");
        Install("claude", prefix: true);
        Install("agents");

        var report = Status("agents");

        Assert.Contains(report.Warnings, warning => warning.Contains("OpenCode") && warning.Contains("'alpha'") && warning.Contains("pyrevit-alpha"));
    }

    [Fact]
    public void EveryTargetIsDocumentedInTheHelpTextAndTheDocs() {
        var help = PyRevitCLIAppHelps.HelpText(PyRevitCLICommandType.Agent);
        var docs = File.ReadAllText(Path.Combine(RepositoryRoot(), "docs", "agent-runtime.md"));

        foreach (var target in SkillTargets.TargetNames) {
            Assert.Contains(target, help);
            Assert.Contains($"| `{target}` |", docs);
        }
    }

    private static string RepositoryRoot() {
        for (var directory = new DirectoryInfo(AppContext.BaseDirectory); directory != null; directory = directory.Parent)
            if (File.Exists(Path.Combine(directory.FullName, "docs", "agent-runtime.md")))
                return directory.FullName;
        throw new DirectoryNotFoundException("docs/agent-runtime.md not found above " + AppContext.BaseDirectory);
    }
}
