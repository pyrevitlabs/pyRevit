using pyRevitLabs.Common;
using pyRevitLabs.PyRevit;

namespace pyRevitCLI.Tests;

/// <summary>
///     Verifies that a session started with <c>pyrevit launch --isolated</c> does not pick up a config stored in its clone.
/// </summary>
[Collection(CliGlobalState.Name)]
public class LaunchIsolationTests : IDisposable {
    private readonly string cloneDirectory = Path.Combine(Path.GetTempPath(), "pyRevit-launch-tests-" + Guid.NewGuid());
    private readonly string previousSetting = Environment.GetEnvironmentVariable(PyRevitLabsConsts.PyRevitIgnoreLocalConfigEnvVar);

    /// <summary>
    ///     Initializes a new instance of the <see cref="LaunchIsolationTests"/> class with a clone that carries its own config.
    /// </summary>
    public LaunchIsolationTests() {
        Directory.CreateDirectory(cloneDirectory);
        File.WriteAllText(Path.Combine(cloneDirectory, "pyRevitfile"), string.Empty);
        File.WriteAllText(Path.Combine(cloneDirectory, PyRevitLabsConsts.DefaultConfigsFileName), string.Empty);
        PyRevitInstallScope.SetRuntimeInstallRoot(cloneDirectory);
    }

    /// <inheritdoc />
    public void Dispose() {
        Environment.SetEnvironmentVariable(PyRevitLabsConsts.PyRevitIgnoreLocalConfigEnvVar, previousSetting);
        PyRevitInstallScope.SetRuntimeInstallRoot(null);
        Directory.Delete(cloneDirectory, true);
    }

    /// <summary>
    ///     Verifies that a clone-local config is found when the session is not isolated.
    /// </summary>
    [Fact]
    public void ACloneLocalConfigIsFoundByDefault() {
        Environment.SetEnvironmentVariable(PyRevitLabsConsts.PyRevitIgnoreLocalConfigEnvVar, null);

        Assert.Equal(Path.Combine(cloneDirectory, PyRevitLabsConsts.DefaultConfigsFileName), PyRevitInstallScope.GetLocalConfigFilePath());
    }

    private static System.Diagnostics.ProcessStartInfo ChildOf(params (string Name, string Value)[] inherited) {
        var startInfo = new System.Diagnostics.ProcessStartInfo("revit.exe") { UseShellExecute = false };
        foreach (var (name, value) in inherited)
            startInfo.EnvironmentVariables[name] = value;
        return startInfo;
    }

    /// <summary>
    ///     Verifies that an isolated launch sets its own config folder and ignores the clone's config.
    /// </summary>
    [Fact]
    public void AnIsolatedLaunchSetsTheSessionOverrides() {
        var startInfo = ChildOf();

        PyRevitLauncher.ConfigureEnvironment(startInfo, @"C:\launch\pyRevit.addin", 2026, @"C:\launch\pyRevit");

        var environment = startInfo.EnvironmentVariables;
        Assert.Equal(@"C:\launch\pyRevit.addin", environment[PyRevitConsts.LaunchManifestEnvVar]);
        Assert.Equal("2026", environment[PyRevitConsts.LaunchRevitYearEnvVar]);
        Assert.Equal(@"C:\launch\pyRevit", environment[PyRevitLabsConsts.PyRevitPathOverrideEnvVar]);
        Assert.Equal("1", environment[PyRevitLabsConsts.PyRevitIgnoreLocalConfigEnvVar]);
        Assert.Equal(PyRevitLabsConsts.AgentPath, environment[PyRevitLabsConsts.PyRevitAgentDirOverrideEnvVar]);
    }

    /// <summary>
    ///     Verifies that a launch that is not isolated, started from an isolated session, does not inherit the parent's overrides.
    /// </summary>
    [Fact]
    public void ALaunchFromAnIsolatedSessionDropsTheInheritedConfigOverrides() {
        var startInfo = ChildOf(
            (PyRevitLabsConsts.PyRevitIgnoreLocalConfigEnvVar, "1"),
            (PyRevitLabsConsts.PyRevitPathOverrideEnvVar, @"C:\parent\pyRevit"),
            (PyRevitLabsConsts.PyRevitAgentDirOverrideEnvVar, @"C:\agent"));

        PyRevitLauncher.ConfigureEnvironment(startInfo, @"C:\launch\pyRevit.addin", 2026, configRoot: null);

        var environment = startInfo.EnvironmentVariables;
        Assert.False(environment.ContainsKey(PyRevitLabsConsts.PyRevitIgnoreLocalConfigEnvVar));
        Assert.False(environment.ContainsKey(PyRevitLabsConsts.PyRevitPathOverrideEnvVar));
        Assert.Equal(@"C:\agent", environment[PyRevitLabsConsts.PyRevitAgentDirOverrideEnvVar]);
        Assert.Equal(@"C:\launch\pyRevit.addin", environment[PyRevitConsts.LaunchManifestEnvVar]);
    }

    /// <summary>
    ///     Verifies that a deliberate config override survives a launch that is not isolated and has no isolated parent.
    /// </summary>
    [Fact]
    public void ADeliberateConfigOverrideSurvivesALaunchThatIsNotIsolated() {
        var startInfo = ChildOf((PyRevitLabsConsts.PyRevitPathOverrideEnvVar, @"C:\mine\pyRevit"));

        PyRevitLauncher.ConfigureEnvironment(startInfo, @"C:\launch\pyRevit.addin", 2026, configRoot: null);

        Assert.Equal(@"C:\mine\pyRevit", startInfo.EnvironmentVariables[PyRevitLabsConsts.PyRevitPathOverrideEnvVar]);
    }

    /// <summary>
    ///     Verifies that the isolation setting hides the clone-local config so the per-session folder is used.
    /// </summary>
    [Fact]
    public void ACloneLocalConfigIsIgnoredInAnIsolatedSession() {
        Environment.SetEnvironmentVariable(PyRevitLabsConsts.PyRevitIgnoreLocalConfigEnvVar, "1");

        Assert.Null(PyRevitInstallScope.GetLocalConfigFilePath());
    }
}
