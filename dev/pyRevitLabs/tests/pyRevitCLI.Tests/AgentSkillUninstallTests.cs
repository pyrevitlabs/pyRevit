using System.Text;
using pyRevitCLI;
using pyRevitLabs.Common;
using pyRevitLabs.Json.Linq;

namespace pyRevitCLI.Tests;

[Trait("Environment", "HostFree")]
[Trait("Level", "Unit")]
public class AgentSkillUninstallTests : SkillInstallFixture {
    [Fact]
    public void UninstallKeepsAnEditedOrExtendedCopyUntilForce() {
        Install();
        File.WriteAllText(AgentsSkill("alpha", "notes.txt"), "my notes");
        File.AppendAllText(AgentsSkill("beta", "SKILL.md"), "my edit");

        var kept = Uninstall();

        Assert.All(kept.Actions, action => Assert.Equal(SkillState.Edited, action.State));
        Assert.True(File.Exists(AgentsSkill("alpha", "notes.txt")));
        Assert.Contains("my edit", File.ReadAllText(AgentsSkill("beta", "SKILL.md")));

        var removed = Uninstall(force: true);

        Assert.All(removed.Actions, action => Assert.Equal(SkillState.Removed, action.State));
        Assert.Contains(removed.Warnings, warning => warning.Contains("notes.txt"));
        Assert.False(Directory.Exists(AgentsSkill("alpha")));
        Assert.False(Directory.Exists(AgentsSkill("beta")));
    }

    [Fact]
    public void UninstallRemovesOnlyOwnedFoldersAndKeepsTheSkillsFolder() {
        Install();
        var skills = Skills(project, ".agents", "skills");
        var foreign = MakeForeign("mine");
        Directory.CreateDirectory(Path.Combine(skills, ".pyrevit-tmp-leftover"));
        Age(Path.Combine(skills, ".pyrevit-tmp-leftover"));

        Uninstall();

        Assert.False(Directory.Exists(Path.Combine(skills, "alpha")));
        Assert.False(Directory.Exists(Path.Combine(skills, "beta")));
        Assert.False(Directory.Exists(Path.Combine(skills, ".pyrevit-tmp-leftover")));
        Assert.True(File.Exists(Path.Combine(foreign, "SKILL.md")));
    }

    [Fact]
    public void UninstallLeavesAFolderWithoutTheMarkerAlone() {
        var foreign = MakeForeign("alpha");

        Uninstall(force: true);

        Assert.True(File.Exists(Path.Combine(foreign, "SKILL.md")));
    }

    [Fact]
    public void ALeftoverCopyIsPutBackWhenTheDestinationIsMissingAndRemovedWhenItIsNot() {
        Install();
        Directory.Move(AgentsSkill("alpha"), AgentsSkill(".pyrevit-tmp-crash1"));
        CopyDirectory(AgentsSkill("beta"), AgentsSkill(".pyrevit-tmp-crash2"));
        Age(AgentsSkill(".pyrevit-tmp-crash1"));
        Age(AgentsSkill(".pyrevit-tmp-crash2"));

        var report = Install();

        Assert.Equal(SkillState.Current, StateOf(report, "alpha"));
        Assert.Contains(report.Warnings, warning => warning.Contains("Restored"));
        Assert.Empty(Directory.GetDirectories(Skills(project, ".agents", "skills"), ".pyrevit-tmp-*"));
    }

    [Fact]
    public void UninstallSweepsLeftoverCopiesThatCarryAMarker() {
        Install();
        Directory.Move(AgentsSkill("alpha"), AgentsSkill(".pyrevit-tmp-crash"));
        Age(AgentsSkill(".pyrevit-tmp-crash"));

        Uninstall();

        Assert.Empty(Directory.GetDirectories(Skills(project, ".agents", "skills")));
    }

    [Fact]
    public void AFreshLeftoverFolderIsNotSweptButAnOldOneIs() {
        Install();
        Directory.Move(AgentsSkill("alpha"), AgentsSkill(".pyrevit-tmp-live"));
        Directory.SetLastWriteTimeUtc(AgentsSkill(".pyrevit-tmp-live"), DateTime.UtcNow);

        var fresh = Install();

        Assert.True(Directory.Exists(AgentsSkill(".pyrevit-tmp-live")));
        Assert.Equal(SkillState.Installed, StateOf(fresh, "alpha"));

        Uninstall();
        Assert.True(Directory.Exists(AgentsSkill(".pyrevit-tmp-live")));

        Age(AgentsSkill(".pyrevit-tmp-live"));
        Uninstall();
        Assert.False(Directory.Exists(AgentsSkill(".pyrevit-tmp-live")));
    }

    [Fact]
    public void ALeftoverWhoseContentDoesNotMatchItsMarkerIsNeverPutBack() {
        Install();
        Directory.Move(AgentsSkill("alpha"), AgentsSkill(".pyrevit-tmp-forged"));
        File.WriteAllText(AgentsSkill(".pyrevit-tmp-forged", "SKILL.md"), "evil");
        Age(AgentsSkill(".pyrevit-tmp-forged"));

        var report = Install();

        Assert.Equal(SkillState.Installed, StateOf(report, "alpha"));
        Assert.DoesNotContain("evil", File.ReadAllText(AgentsSkill("alpha", "SKILL.md")));
        Assert.True(Directory.Exists(AgentsSkill(".pyrevit-tmp-forged")));
    }

    [Theory]
    [InlineData("../x")]
    [InlineData("C:/Windows/Temp/x")]
    public void ALeftoverWithAForgedInstalledNameIsNeverMovedOutsideTheSkillsFolder(string installedName) {
        Install();
        Directory.Move(AgentsSkill("alpha"), AgentsSkill(".pyrevit-tmp-forged"));
        var markerPath = AgentsSkill(".pyrevit-tmp-forged", ".pyrevit-skill.json");
        var marker = JObject.Parse(File.ReadAllText(markerPath));
        marker["installedName"] = installedName;
        File.WriteAllText(markerPath, marker.ToString());
        Age(AgentsSkill(".pyrevit-tmp-forged"));

        Install();

        Assert.False(Directory.Exists(Skills(project, ".agents", "x")));
        Assert.False(Directory.Exists("C:/Windows/Temp/x"));
    }
}
