using pyRevitLabs.Common;
using pyRevitLabs.Configurations;
using pyRevitLabs.Configurations.Ini.Extensions;
using pyRevitLabs.PyRevit;

namespace pyRevitCLI.Tests;

[Collection(CliGlobalState.Name)]
[Trait("Environment", "HostFree")]
[Trait("Level", "Integration")]
public class AgentSessionStartConfigTests : IDisposable {
    private readonly string configPath = Path.Combine(Path.GetTempPath(), $"pyrevit-session-start-{Guid.NewGuid():N}.ini");

    public AgentSessionStartConfigTests() {
        PyRevitConfigStore.Reset();
    }

    public void Dispose() {
        PyRevitConfigStore.Reset();
        File.Delete(configPath);
    }

    private void UseConfig(string content) {
        File.WriteAllText(configPath, content);
        PyRevitConfigStore.SetFactory(() => new ConfigurationBuilder(false).AddIniConfiguration(configPath).Build());
    }

    [Fact]
    public void SessionsStartInThePanelWhenNotConfigured() {
        UseConfig("[agent]\npolicy = ask\n");

        Assert.Equal("user", PyRevitConfigs.GetAgentSessionStart());
    }

    [Fact]
    public void SessionsStartAutomaticallyWhenSetToAutoInAnyCase() {
        UseConfig("[agent]\nsession_start = AUTO\n");

        Assert.Equal("auto", PyRevitConfigs.GetAgentSessionStart());
    }

    [Fact]
    public void AnyOtherValueStartsSessionsInThePanel() {
        UseConfig("[agent]\nsession_start = automatic\n");

        Assert.Equal("user", PyRevitConfigs.GetAgentSessionStart());
    }

    [Fact]
    public void TheRemovedRequireSessionSettingIsIgnored() {
        UseConfig("[agent]\nrequire_session = no\n");

        Assert.Equal("user", PyRevitConfigs.GetAgentSessionStart());
    }

    [Fact]
    public void SettingTheSessionStartPersistsAndRefusesOtherValues() {
        UseConfig("[agent]\n");

        PyRevitConfigs.SetAgentSessionStart("auto");
        PyRevitConfigStore.Reload();
        Assert.Equal("auto", PyRevitConfigs.GetAgentSessionStart());

        PyRevitConfigs.SetAgentSessionStart("user");
        PyRevitConfigStore.Reload();
        Assert.Equal("user", PyRevitConfigs.GetAgentSessionStart());
        Assert.Throws<PyRevitException>(() => PyRevitConfigs.SetAgentSessionStart("always"));
    }
}
