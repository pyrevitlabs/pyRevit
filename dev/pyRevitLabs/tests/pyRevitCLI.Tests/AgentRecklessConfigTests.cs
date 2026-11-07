using pyRevitLabs.Configurations;
using pyRevitLabs.Configurations.Ini.Extensions;
using pyRevitLabs.PyRevit;

namespace pyRevitCLI.Tests;

[Collection(CliGlobalState.Name)]
[Trait("Environment", "HostFree")]
[Trait("Level", "Integration")]
public class AgentRecklessConfigTests : IDisposable {
    private readonly string configPath = Path.Combine(Path.GetTempPath(), $"pyrevit-reckless-{Guid.NewGuid():N}.ini");

    public AgentRecklessConfigTests() {
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
    public void RecklessIsOffWhenNotConfigured() {
        UseConfig("[agent]\npolicy = ask\n");

        Assert.False(PyRevitConfigs.GetAgentReckless());
    }

    [Fact]
    public void RecklessIsOnOnlyWhenSetToTrue() {
        UseConfig("[agent]\nreckless = true\n");

        Assert.True(PyRevitConfigs.GetAgentReckless());
    }

    [Fact]
    public void SettingRecklessPersistsAndCanBeTurnedOff() {
        UseConfig("[agent]\n");

        PyRevitConfigs.SetAgentReckless(true);
        Assert.True(PyRevitConfigs.GetAgentReckless());
        PyRevitConfigStore.Reload();
        Assert.True(PyRevitConfigs.GetAgentReckless());

        PyRevitConfigs.SetAgentReckless(false);
        PyRevitConfigStore.Reload();
        Assert.False(PyRevitConfigs.GetAgentReckless());
    }
}
