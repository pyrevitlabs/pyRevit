using System.Text;
using pyRevitCLI;
using pyRevitLabs.Common;
using pyRevitLabs.Json.Linq;

namespace pyRevitCLI.Tests;

[Trait("Environment", "HostFree")]
[Trait("Level", "Unit")]
public class AgentSkillPrefixTests : SkillInstallFixture {
    [Fact]
    public void PrefixInstallsAClashingSkillUnderAPrefixedNameWithTheNameLineRewritten() {
        var foreign = MakeForeign("alpha");

        var report = Install(prefix: true);

        Assert.Equal(SkillState.Installed, StateOf(report, "alpha"));
        Assert.Equal("mine", File.ReadAllText(Path.Combine(foreign, "SKILL.md")));
        var prefixed = File.ReadAllText(AgentsSkill("pyrevit-alpha", "SKILL.md"));
        Assert.Contains("name: pyrevit-alpha\n", prefixed);
        Assert.DoesNotContain("name: alpha", prefixed);
        Assert.True(Directory.Exists(AgentsSkill("beta")));
        Assert.Equal(SkillState.Current, StateOf(Status(), "alpha"));
        Assert.Equal(SkillState.Current, StateOf(Install(prefix: true), "alpha"));
    }

    [Fact]
    public void PrefixWithTheSameNameStillTakenSaysSoInsteadOfAskingForPrefix() {
        MakeForeign("alpha");
        MakeForeign("pyrevit-alpha");

        var report = Install(prefix: true);

        Assert.Equal(SkillState.Foreign, StateOf(report, "alpha"));
        var warning = Assert.Single(report.Warnings, text => text.Contains("pyrevit-alpha"));
        Assert.DoesNotContain("Use --prefix", warning);
    }

    [Fact]
    public void ANamedFileWithCrlfAndABomSurvivesPrefixingByteForByte() {
        var text = "---\r\nname: \"alpha\"\r\ndescription: Use when testing.\r\n---\r\nbody\r\n";
        File.WriteAllBytes(Path.Combine(shipped, "alpha", "SKILL.md"), new UTF8Encoding(true).GetPreamble().Concat(Encoding.UTF8.GetBytes(text)).ToArray());
        MakeForeign("alpha");

        Install(prefix: true);

        var bytes = File.ReadAllBytes(AgentsSkill("pyrevit-alpha", "SKILL.md"));
        var expected = new UTF8Encoding(true).GetPreamble().Concat(Encoding.UTF8.GetBytes(text.Replace("name: \"alpha\"", "name: pyrevit-alpha"))).ToArray();
        Assert.Equal(expected, bytes);
        Assert.Equal(SkillState.Current, StateOf(Status(), "alpha"));
    }

    [Fact]
    public void AnOwnedPrefixedCopyIsRefreshedInPlaceWhenThePlainNameIsFree() {
        var foreign = MakeForeign("alpha");
        Install(prefix: true);
        Directory.Delete(foreign, recursive: true);
        File.WriteAllText(Path.Combine(shipped, "alpha", "extra.md"), "extra v2");

        Assert.Equal(SkillState.Stale, StateOf(Status(), "alpha"));
        var report = Install();

        Assert.Equal(SkillState.Updated, StateOf(report, "alpha"));
        Assert.False(Directory.Exists(AgentsSkill("alpha")));
        Assert.Equal("extra v2", File.ReadAllText(AgentsSkill("pyrevit-alpha", "extra.md")));
    }

    [Fact]
    public void AnEditedPrefixedCopyIsKeptUntilForce() {
        MakeForeign("alpha");
        Install(prefix: true);
        File.AppendAllText(AgentsSkill("pyrevit-alpha", "SKILL.md"), "my edit");

        Assert.Equal(SkillState.Edited, StateOf(Status(), "alpha"));
        Assert.Equal(SkillState.Edited, StateOf(Install(prefix: true), "alpha"));
        Assert.Equal(SkillState.Updated, StateOf(Install(prefix: true, force: true), "alpha"));
    }

    [Fact]
    public void ANameLineIndentedUnderAnotherKeyIsLeftAloneWhenPrefixing() {
        File.WriteAllText(Path.Combine(shipped, "alpha", "SKILL.md"), "---\nmetadata:\n  name: other\nname: alpha\ndescription: d\n---\nbody\n");
        MakeForeign("alpha");

        Install(prefix: true);

        var text = File.ReadAllText(AgentsSkill("pyrevit-alpha", "SKILL.md"));
        Assert.Contains("  name: other\n", text);
        Assert.Contains("\nname: pyrevit-alpha\n", text);
    }

    [Fact]
    public void AShippedSkillWithoutFrontMatterIsNotCorruptedByPrefixing() {
        File.WriteAllText(Path.Combine(shipped, "alpha", "SKILL.md"), "no front matter\nname: alpha\n");
        MakeForeign("alpha");

        var report = Install(prefix: true);

        Assert.Equal(SkillState.Failed, StateOf(report, "alpha"));
        Assert.False(Directory.Exists(AgentsSkill("pyrevit-alpha")));
    }
}
