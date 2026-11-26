using System.Text;
using pyRevitCLI;
using pyRevitLabs.Common;
using pyRevitLabs.Json.Linq;

namespace pyRevitCLI.Tests;

[Trait("Environment", "HostFree")]
[Trait("Level", "Unit")]
public class AgentSkillEditedTests : SkillInstallFixture {
    [Fact]
    public void AHandEditedOwnedCopyIsKeptUntilForceRepairsIt() {
        Install();
        File.AppendAllText(AgentsSkill("alpha", "SKILL.md"), "my edit");

        Assert.Equal(SkillState.Edited, StateOf(Status(), "alpha"));
        Assert.Equal(SkillState.Edited, StateOf(Install(), "alpha"));
        Assert.Contains("my edit", File.ReadAllText(AgentsSkill("alpha", "SKILL.md")));

        Assert.Equal(SkillState.Updated, StateOf(Install(force: true), "alpha"));
        Assert.DoesNotContain("my edit", File.ReadAllText(AgentsSkill("alpha", "SKILL.md")));
    }

    [Fact]
    public void ExtraFilesInAnOwnedFolderMakeItEditedAndSurviveUntilForce() {
        Install();
        File.WriteAllText(AgentsSkill("alpha", "notes.txt"), "my notes");
        Directory.CreateDirectory(AgentsSkill("alpha", "scripts"));
        File.WriteAllText(AgentsSkill("alpha", "scripts", "x.py"), "print(1)");
        File.WriteAllText(Path.Combine(shipped, "alpha", "extra.md"), "extra v2");

        Assert.Equal(SkillState.Edited, StateOf(Status(), "alpha"));
        var kept = Install();
        Assert.Equal(SkillState.Edited, StateOf(kept, "alpha"));
        Assert.Contains(kept.Warnings, warning => warning.Contains("notes.txt") && warning.Contains("scripts/x.py"));
        Assert.True(File.Exists(AgentsSkill("alpha", "notes.txt")));
        Assert.True(File.Exists(AgentsSkill("alpha", "scripts", "x.py")));

        var forced = Install(force: true);
        Assert.Equal(SkillState.Updated, StateOf(forced, "alpha"));
        Assert.Contains(forced.Warnings, warning => warning.Contains("deletes") && warning.Contains("notes.txt"));
        Assert.False(File.Exists(AgentsSkill("alpha", "notes.txt")));
        Assert.Equal(SkillState.Current, StateOf(Status(), "alpha"));
    }

    [Fact]
    public void AFolderCopiedWithItsMarkerIsNeverRemovedByUninstall() {
        Install();
        CopyDirectory(AgentsSkill("alpha"), AgentsSkill("my-alpha"));
        File.AppendAllText(AgentsSkill("my-alpha", "SKILL.md"), "my edit");

        Uninstall(force: true);

        Assert.Contains("my edit", File.ReadAllText(AgentsSkill("my-alpha", "SKILL.md")));
    }

    [Fact]
    public void AFolderCopiedWithItsMarkerIsNeverReplacedByForceInstall() {
        Install();
        CopyDirectory(AgentsSkill("alpha"), AgentsSkill("pyrevit-alpha"));
        File.AppendAllText(AgentsSkill("pyrevit-alpha", "SKILL.md"), "my edit");
        Directory.Delete(AgentsSkill("alpha"), recursive: true);

        var report = Install(force: true);

        Assert.Contains("my edit", File.ReadAllText(AgentsSkill("pyrevit-alpha", "SKILL.md")));
        Assert.Equal(SkillState.Installed, StateOf(report, "alpha"));
    }

    [Fact]
    public void ACopiedMarkerDoesNotMakeAFolderRemovable() {
        Install();
        var forged = Directory.CreateDirectory(AgentsSkill("mine")).FullName;
        File.WriteAllText(Path.Combine(forged, "SKILL.md"), "my own skill");
        File.Copy(AgentsSkill("beta", ".pyrevit-skill.json"), Path.Combine(forged, ".pyrevit-skill.json"));

        var report = Uninstall();

        Assert.DoesNotContain(report.Actions, action => action.Skill == "mine");
        Assert.Equal("my own skill", File.ReadAllText(Path.Combine(forged, "SKILL.md")));
    }

    [Fact]
    public void TheForceWarningsAlwaysSayTheWholeFolderIsDeleted() {
        Install();
        File.AppendAllText(AgentsSkill("alpha", "SKILL.md"), "my edit");

        var replaced = Install(force: true);
        File.AppendAllText(AgentsSkill("alpha", "SKILL.md"), "my edit");
        var removed = Uninstall(force: true);

        Assert.Contains(replaced.Warnings, warning => warning.Contains("with --force deletes the whole folder, including your edits."));
        Assert.Contains(removed.Warnings, warning => warning.Contains("with --force deletes the whole folder, including your edits."));
    }
}
