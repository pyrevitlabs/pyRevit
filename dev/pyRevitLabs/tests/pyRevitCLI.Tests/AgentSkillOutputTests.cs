using pyRevitCLI;

namespace pyRevitCLI.Tests;

[Trait("Environment", "HostFree")]
[Trait("Level", "Unit")]
public class AgentSkillOutputTests {
    [Fact]
    public void StateLabelsAreTheWordsTheCliPrintsAndJsonReports() {
        var labels = Enum.GetValues<SkillState>().Select(state => state.Label()).ToArray();

        Assert.Equal(new[] { "installed", "updated", "current", "stale", "edited", "missing", "foreign", "removed", "failed" }, labels);
    }

    [Fact]
    public void PrintableStripsControlAndBidiCharactersButKeepsOrdinaryText() {
        var hostile = "notes" + (char)0x1b + "[31m" + (char)0x202E + "gnp.txt" + (char)0x7f + (char)0x2028 + (char)0x200F + "end";

        var clean = SkillFiles.Printable(hostile);

        Assert.Equal("notes[31mgnp.txtend", clean);
        Assert.Equal("caf" + (char)0xe9 + " skill-1", SkillFiles.Printable("caf" + (char)0xe9 + " skill-1"));
        Assert.Null(SkillFiles.Printable(null));
    }
}
