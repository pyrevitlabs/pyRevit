using pyRevitLabs.PyRevit;

namespace pyRevitCLI.Tests;

/// <summary>
///     Verifies that <c>pyrevit launch --isolated</c> can tell from a session's seeded config whether the agent host will start (#4137).
/// </summary>
[Trait("Environment", "HostFree")]
[Trait("Level", "Integration")]
public class LaunchAgentStateTests : IDisposable {
    private readonly string directory = Path.Combine(Path.GetTempPath(), "pyRevit-launch-agent-tests-" + Guid.NewGuid());
    private readonly string configFile;

    /// <summary>
    ///     Initializes a new instance of the <see cref="LaunchAgentStateTests"/> class with an empty directory for config files.
    /// </summary>
    public LaunchAgentStateTests() {
        Directory.CreateDirectory(directory);
        configFile = Path.Combine(directory, "pyRevit_config.ini");
    }

    /// <inheritdoc />
    public void Dispose() {
        Directory.Delete(directory, true);
    }

    /// <summary>
    ///     Verifies that a config with the agent switched on reports it as enabled.
    /// </summary>
    [Fact]
    public void AConfigWithTheAgentEnabledIsReportedAsEnabled() {
        File.WriteAllText(configFile, "[agent]\nenabled = true\n");

        Assert.True(PyRevitLauncher.ReadAgentEnabled(configFile));
    }

    /// <summary>
    ///     Verifies that a config with the agent switched off reports it as disabled.
    /// </summary>
    [Fact]
    public void AConfigWithTheAgentDisabledIsReportedAsDisabled() {
        File.WriteAllText(configFile, "[agent]\nenabled = false\n");

        Assert.False(PyRevitLauncher.ReadAgentEnabled(configFile));
    }

    /// <summary>
    ///     Verifies that a config with no agent section, such as one that only sets user extensions, reports the agent as disabled.
    /// </summary>
    [Fact]
    public void AConfigWithoutAnAgentSectionIsReportedAsDisabled() {
        File.WriteAllText(configFile, "[core]\nuserextensions = []\n");

        Assert.False(PyRevitLauncher.ReadAgentEnabled(configFile));
    }

    /// <summary>
    ///     Verifies that a session seeded with no config at all reports the agent as disabled.
    /// </summary>
    [Fact]
    public void AMissingConfigIsReportedAsDisabled() {
        Assert.False(PyRevitLauncher.ReadAgentEnabled(configFile));
    }
}
