using System.Text;
using pyRevitCLI;
using pyRevitLabs.Common;
using pyRevitLabs.Json.Linq;

namespace pyRevitCLI.Tests;

[Trait("Environment", "HostFree")]
[Trait("Level", "Unit")]
public class AgentSkillLinkTests : SkillInstallFixture {
    [LinkFact]
    public void ASkillsFolderThatIsAJunctionIsRefused() {
        var elsewhere = Directory.CreateDirectory(Path.Combine(temp, "elsewhere")).FullName;
        Directory.CreateDirectory(Path.Combine(project, ".agents"));
        MakeJunction(Skills(project, ".agents", "skills"), elsewhere);

        var installed = Install();
        var status = Status();

        Assert.All(installed.Actions, action => Assert.Equal(SkillState.Failed, action.State));
        Assert.All(status.Actions, action => Assert.Equal(SkillState.Failed, action.State));
        Assert.Empty(Directory.GetFileSystemEntries(elsewhere));
    }

    [LinkFact]
    public void ALinkedSkillFolderIsForeignAndTheRestOfTheRunIsReported() {
        var elsewhere = Directory.CreateDirectory(Path.Combine(temp, "elsewhere")).FullName;
        File.WriteAllText(Path.Combine(elsewhere, "keep.md"), "keep");
        Directory.CreateDirectory(Skills(project, ".agents", "skills"));
        MakeJunction(AgentsSkill("alpha"), elsewhere);

        var installed = Install(force: true, prefix: true);
        var status = Status();
        var removed = Uninstall(force: true);

        Assert.Equal(SkillState.Foreign, StateOf(installed, "alpha"));
        Assert.Equal(SkillState.Installed, StateOf(installed, "beta"));
        Assert.Contains(installed.Warnings, warning => warning.Contains("link"));
        Assert.Equal(2, status.Actions.Count);
        Assert.Equal(SkillState.Foreign, StateOf(status, "alpha"));
        Assert.Equal(SkillState.Removed, StateOf(removed, "beta"));
        Assert.Equal("keep", File.ReadAllText(Path.Combine(elsewhere, "keep.md")));
        Assert.Equal(new[] { "keep.md" }, Directory.GetFileSystemEntries(elsewhere).Select(Path.GetFileName));
    }

    [LinkFact]
    public void AnOwnedFolderHoldingALinkIsReportedEditedAndNeverFollowed() {
        Install();
        var elsewhere = Directory.CreateDirectory(Path.Combine(temp, "elsewhere")).FullName;
        File.WriteAllText(Path.Combine(elsewhere, "keep.md"), "keep");
        MakeJunction(AgentsSkill("alpha", "linked"), elsewhere);

        Assert.Equal(SkillState.Edited, StateOf(Status(), "alpha"));
        Assert.Equal(SkillState.Failed, StateOf(Install(force: true), "alpha"));
        Uninstall(force: true);

        Assert.True(File.Exists(Path.Combine(elsewhere, "keep.md")));
        Assert.True(Directory.Exists(AgentsSkill("alpha")));
    }

    [LinkFact]
    public void ALinkedSkillsFolderFailsOnlyItsOwnTargetForInstallAndStatus() {
        var elsewhere = Directory.CreateDirectory(Path.Combine(temp, "elsewhere")).FullName;
        Directory.CreateDirectory(Path.Combine(project, ".claude"));
        MakeJunction(Skills(project, ".claude", "skills"), elsewhere);

        var installed = Install("agents,claude");
        var status = Status("agents,claude");

        Assert.Contains(installed.Actions, action => action.Target == "claude" && action.State == SkillState.Failed);
        Assert.Contains(installed.Actions, action => action.Target == "agents" && action.State == SkillState.Installed);
        Assert.Contains(status.Actions, action => action.Target == "claude" && action.State == SkillState.Failed);
        Assert.Contains(status.Actions, action => action.Target == "agents" && action.State == SkillState.Current);
        Assert.Empty(Directory.GetFileSystemEntries(elsewhere));
    }
}
