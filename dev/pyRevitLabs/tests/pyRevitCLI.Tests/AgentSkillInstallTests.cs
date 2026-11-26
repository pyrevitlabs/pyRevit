using System.Text;
using pyRevitCLI;
using pyRevitLabs.Common;
using pyRevitLabs.Json.Linq;

namespace pyRevitCLI.Tests;

[Trait("Environment", "HostFree")]
[Trait("Level", "Unit")]
public class AgentSkillInstallTests : SkillInstallFixture {
    [Fact]
    public void InstallCopiesMarkdownFilesAndWritesTheMarkerIntoTheAgentsFolder() {
        var report = Install();

        Assert.Equal(SkillState.Installed, StateOf(report, "alpha"));
        Assert.True(File.Exists(AgentsSkill("alpha", "SKILL.md")));
        Assert.Equal("extra", File.ReadAllText(AgentsSkill("alpha", "extra.md")));
        Assert.False(File.Exists(AgentsSkill("alpha", "notes.txt")));
        var marker = JObject.Parse(File.ReadAllText(AgentsSkill("alpha", ".pyrevit-skill.json")));
        Assert.Equal("pyrevit", marker.Value<string>("source"));
        Assert.Equal("alpha", marker.Value<string>("name"));
        Assert.Matches("^[0-9a-f]{64}$", marker.Value<string>("sha256"));
        Assert.Empty(Directory.GetDirectories(Skills(project, ".agents", "skills"), ".pyrevit-tmp-*"));
    }

    [Fact]
    public void InstallAgainReportsCurrentAndDoesNotRewriteTheFiles() {
        Install();
        var old = new DateTime(2001, 1, 1, 0, 0, 0, DateTimeKind.Utc);
        File.SetLastWriteTimeUtc(AgentsSkill("alpha", "SKILL.md"), old);

        var report = Install();

        Assert.Equal(SkillState.Current, StateOf(report, "alpha"));
        Assert.Equal(old, File.GetLastWriteTimeUtc(AgentsSkill("alpha", "SKILL.md")));
    }

    [Fact]
    public void InstallRefreshesAStaleOwnedCopy() {
        Install();
        File.WriteAllText(Path.Combine(shipped, "alpha", "extra.md"), "extra v2");
        Assert.Equal(SkillState.Stale, StateOf(Status(), "alpha"));

        var report = Install();

        Assert.Equal(SkillState.Updated, StateOf(report, "alpha"));
        Assert.Equal("extra v2", File.ReadAllText(AgentsSkill("alpha", "extra.md")));
        Assert.Equal(SkillState.Current, StateOf(Status(), "alpha"));
        Assert.Empty(Directory.GetDirectories(Skills(project, ".agents", "skills"), ".pyrevit-tmp-*"));
    }

    [Fact]
    public void AFolderWithoutTheMarkerIsSkippedAndLeftUntouched() {
        var foreign = MakeForeign("alpha");

        var report = Install(force: true);

        Assert.Equal(SkillState.Foreign, StateOf(report, "alpha"));
        Assert.Equal(SkillState.Installed, StateOf(report, "beta"));
        Assert.Equal("mine", File.ReadAllText(Path.Combine(foreign, "SKILL.md")));
        Assert.Contains(report.Warnings, warning => warning.Contains(foreign) && warning.Contains("--prefix"));
        Assert.Equal(SkillState.Foreign, StateOf(Status(), "alpha"));
    }

    [Fact]
    public void APlainFileNamedLikeASkillIsForeignAndTheRunGoesOn() {
        Directory.CreateDirectory(Skills(project, ".agents", "skills"));
        File.WriteAllText(AgentsSkill("alpha"), "a file");

        var report = Install();

        Assert.Equal(SkillState.Foreign, StateOf(report, "alpha"));
        Assert.Equal(SkillState.Installed, StateOf(report, "beta"));
        Assert.Equal("a file", File.ReadAllText(AgentsSkill("alpha")));
        Assert.Equal(SkillState.Foreign, StateOf(Status(), "alpha"));
        Uninstall();
        Assert.Equal("a file", File.ReadAllText(AgentsSkill("alpha")));
    }

    [Fact]
    public void WithoutPrefixTheInstalledNameIsTheShippedName() {
        Install();

        Assert.True(Directory.Exists(AgentsSkill("alpha")));
        Assert.False(Directory.Exists(AgentsSkill("pyrevit-alpha")));
    }

    [Fact]
    public void AShippedFileOverTheLimitIsRefusedAndNothingIsInstalled() {
        File.WriteAllText(Path.Combine(shipped, "alpha", "big.md"), new string('x', 129 * 1024));

        Assert.Throws<PyRevitException>(() => Install());

        Assert.False(Directory.Exists(AgentsSkill("alpha")));
    }

    [Fact]
    public void ASkillWhoseNameDiffersFromItsFolderIsNotInstalled() {
        Directory.CreateDirectory(Path.Combine(shipped, "gamma"));
        File.WriteAllText(Path.Combine(shipped, "gamma", "SKILL.md"), "---\nname: ../evil\ndescription: x\n---\n");

        var report = Install();

        Assert.DoesNotContain(report.Actions, action => action.Skill == "gamma" && action.State == SkillState.Installed);
        Assert.False(Directory.Exists(Skills(project, ".agents", "evil")));
    }

    [Fact]
    public void InstallAndStatusWarnAboutAnInstalledDescriptionOverTheLimit() {
        WriteShipped("alpha", new string('d', 241), "alpha body");

        var report = Install();

        Assert.Contains(report.Warnings, warning => warning.Contains("alpha") && warning.Contains("241"));
        Assert.Contains(Status().Warnings, warning => warning.Contains("alpha") && warning.Contains("241"));
    }

    [Fact]
    public void StatusReportsMissingForSkillsNotInstalled() {
        var report = Status();

        Assert.All(report.Actions, action => Assert.Equal(SkillState.Missing, action.State));
        Assert.Equal(2, report.Actions.Count);
    }

    [Theory]
    [InlineData("{\"source\":{\"a\":1},\"sha256\":\"x\"}")]
    [InlineData("{\"source\":[\"pyrevit\"],\"sha256\":[1]}")]
    [InlineData("[1,2]")]
    [InlineData("not json")]
    public void AMalformedMarkerMakesTheFolderForeignWithoutThrowing(string markerText) {
        var foreign = MakeForeign("alpha");
        File.WriteAllText(Path.Combine(foreign, ".pyrevit-skill.json"), markerText);

        var report = Install();

        Assert.Equal(SkillState.Foreign, StateOf(report, "alpha"));
        Assert.Equal(SkillState.Installed, StateOf(report, "beta"));
        Assert.Equal("mine", File.ReadAllText(Path.Combine(foreign, "SKILL.md")));
    }

    [Fact]
    public void AnUnwritableSkillsFolderFailsOnlyItsOwnTarget() {
        File.WriteAllText(Skills(project, ".claude"), "a file where the folder should be");

        var report = Install("agents,claude");

        Assert.Equal(SkillState.Installed, StateOf(report.Actions.Where(action => action.Target == "agents").ToList(), "alpha"));
        Assert.Contains(report.Actions, action => action.Target == "claude" && action.State == SkillState.Failed);
        Assert.True(File.Exists(AgentsSkill("alpha", "SKILL.md")));
    }

    [WindowsFact]
    public void ALockedFileFailsOnlyThatSkillAndTheOldCopyStays() {
        Install();
        File.WriteAllText(Path.Combine(shipped, "alpha", "extra.md"), "extra v2");
        File.WriteAllText(Path.Combine(shipped, "beta", "extra.md"), "beta extra");

        SkillsReport report;
        using (new FileStream(AgentsSkill("alpha", "extra.md"), FileMode.Open, FileAccess.Read, FileShare.Read))
            report = Install();

        Assert.Equal(SkillState.Failed, StateOf(report, "alpha"));
        Assert.Equal(SkillState.Updated, StateOf(report, "beta"));
        Assert.Equal("extra", File.ReadAllText(AgentsSkill("alpha", "extra.md")));
        Assert.Equal(SkillState.Stale, StateOf(Status(), "alpha"));
        Assert.Empty(Directory.GetDirectories(Skills(project, ".agents", "skills"), ".pyrevit-tmp-*"));
        Assert.Contains(report.Warnings, warning => warning.Contains("alpha"));
    }
}
