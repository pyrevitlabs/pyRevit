using pyRevitLabs.Common;
using pyRevitLabs.Configurations;
using pyRevitLabs.Configurations.Ini.Extensions;
using pyRevitLabs.PyRevit;

namespace pyRevitCLI.Tests;

[Collection(CliGlobalState.Name)]
[Trait("Environment", "HostFree")]
[Trait("Level", "Integration")]
public class AgentRecordingStartConfigTests : IDisposable {
    private readonly string configPath = Path.Combine(Path.GetTempPath(), $"pyrevit-recording-start-{Guid.NewGuid():N}.ini");

    public AgentRecordingStartConfigTests() {
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

    private static string Printed(Action command) {
        var original = Console.Out;
        var captured = new StringWriter();
        Console.SetOut(captured);
        try {
            command();
        }
        finally {
            Console.SetOut(original);
        }
        return captured.ToString();
    }

    [Fact]
    public void RecordingsStartInThePanelWhenNotConfigured() {
        UseConfig("[agent]\nsession_start = auto\n");

        Assert.Equal("user", PyRevitConfigs.GetAgentRecordingStart());
    }

    [Fact]
    public void RecordingsStartAutomaticallyWhenSetToAutoInAnyCase() {
        UseConfig("[agent]\nrecording_start = AUTO\n");

        Assert.Equal("auto", PyRevitConfigs.GetAgentRecordingStart());
        Assert.Equal("user", PyRevitConfigs.GetAgentSessionStart());
    }

    [Fact]
    public void AnyOtherValueStartsRecordingsInThePanel() {
        UseConfig("[agent]\nrecording_start = always\n");

        Assert.Equal("user", PyRevitConfigs.GetAgentRecordingStart());
    }

    [Fact]
    public void SettingTheRecordingStartPersistsAndRefusesOtherValues() {
        UseConfig("[agent]\n");

        PyRevitConfigs.SetAgentRecordingStart("auto");
        PyRevitConfigStore.Reload();
        Assert.Equal("auto", PyRevitConfigs.GetAgentRecordingStart());

        PyRevitConfigs.SetAgentRecordingStart("user");
        PyRevitConfigStore.Reload();
        Assert.Equal("user", PyRevitConfigs.GetAgentRecordingStart());
        Assert.Throws<PyRevitException>(() => PyRevitConfigs.SetAgentRecordingStart("always"));
    }

    [Fact]
    public void TheCommandSetsTheValueAndPrintsItWithoutOne() {
        UseConfig("[agent]\n");

        var set = Printed(() => PyRevitCLIAgentCmds.ConfigureRecordingStart("auto"));
        PyRevitConfigStore.Reload();
        var read = Printed(() => PyRevitCLIAgentCmds.ConfigureRecordingStart(null));

        Assert.Contains("Reload pyRevit", set);
        Assert.Equal("Recordings start: auto", read.Trim());
    }
}
