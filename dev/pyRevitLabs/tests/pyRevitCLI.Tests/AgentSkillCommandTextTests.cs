using pyRevitCLI;
using pyRevitLabs.Json.Linq;

namespace pyRevitCLI.Tests;

[Trait("Environment", "HostFree")]
[Trait("Level", "Unit")]
public class AgentSkillCommandTextTests : SkillInstallFixture {
    private static SkillsReport Installed() {
        var report = new SkillsReport();
        report.Actions.Add(new SkillAction { Target = "agents", Skill = "alpha", State = SkillState.Installed, Folder = "x" });
        return report;
    }

    [Fact]
    public void TheJsonOutputIsStrippedOfControlAndBidiCharactersToo() {
        var hostile = "a" + (char)0x202E + "b" + (char)0x1b + "c";
        var report = new SkillsReport();
        report.Actions.Add(new SkillAction { Target = "agents", Skill = hostile, State = SkillState.Current, Folder = hostile });
        report.Warnings.Add(hostile);

        var json = PyRevitCLIAgentCmds.SkillsJson(report);

        var parsed = JObject.Parse(json);
        Assert.Equal("abc", parsed["skills"][0].Value<string>("skill"));
        Assert.Equal("abc", parsed["skills"][0].Value<string>("folder"));
        Assert.Equal("abc", parsed["warnings"][0].Value<string>());
    }

    [Fact]
    public void TheClaudeAndAntigravityHintsAreIndependent() {
        var both = PyRevitCLIAgentCmds.SkillsAdvice(Context("claude,antigravity"), Installed());
        var agents = PyRevitCLIAgentCmds.SkillsAdvice(Context("agents"), Installed());
        var claudeOnly = PyRevitCLIAgentCmds.SkillsAdvice(Context("claude"), Installed());

        Assert.Single(both);
        Assert.Contains("/skills reload", both[0]);
        Assert.Equal(2, agents.Count);
        Assert.Empty(claudeOnly);
        Assert.Empty(PyRevitCLIAgentCmds.SkillsAdvice(Context("agents"), new SkillsReport()));
    }

    [Fact]
    public void TheRefreshCommandRepeatsTheInspectedScopeTargetsAndPath() {
        Assert.Equal("pyrevit agent skills install --scope=user --target=claude", PyRevitCLIAgentCmds.RefreshCommand("user", "claude", null));
        Assert.Equal("pyrevit agent skills install --scope=project --target=agents --path=\"C:\\my proj\"", PyRevitCLIAgentCmds.RefreshCommand("project", "agents", "C:\\my proj"));
    }
}
