using pyRevitLabs.Common;
using pyRevitLabs.PyRevit;

namespace pyRevitLabs.PyRevit.Tests;

/// <summary>
///     Verifies that a session started with <c>pyrevit launch --isolated</c> does not pick up a config stored in its clone.
/// </summary>
[TestFixture]
[NonParallelizable]
[Category("HostFree")]
[Category("Integration")]
public class LaunchIsolationTests {
    private readonly string cloneDirectory = Path.Combine(Path.GetTempPath(), "pyRevit-launch-tests-" + Guid.NewGuid());
    private readonly string? previousSetting = Environment.GetEnvironmentVariable(PyRevitLabsConsts.PyRevitIgnoreLocalConfigEnvVar);

    /// <summary>
    ///     Points the runtime install root at a clone that carries its own config.
    /// </summary>
    [SetUp]
    public void SetUp() {
        Directory.CreateDirectory(cloneDirectory);
        File.WriteAllText(Path.Combine(cloneDirectory, "pyRevitfile"), string.Empty);
        File.WriteAllText(Path.Combine(cloneDirectory, PyRevitLabsConsts.DefaultConfigsFileName), string.Empty);
        PyRevitInstallScope.SetRuntimeInstallRoot(cloneDirectory);
    }

    /// <summary>
    ///     Restores the process-wide state the test changed and deletes its folder.
    /// </summary>
    [TearDown]
    public void TearDown() {
        Environment.SetEnvironmentVariable(PyRevitLabsConsts.PyRevitIgnoreLocalConfigEnvVar, previousSetting);
        PyRevitInstallScope.SetRuntimeInstallRoot(null);
        Directory.Delete(cloneDirectory, true);
    }

    /// <summary>
    ///     Verifies that a clone-local config is found when the session is not isolated.
    /// </summary>
    [Test]
    public void ACloneLocalConfigIsFoundByDefault() {
        Environment.SetEnvironmentVariable(PyRevitLabsConsts.PyRevitIgnoreLocalConfigEnvVar, null);

        Assert.That(PyRevitInstallScope.GetLocalConfigFilePath(), Is.EqualTo(Path.Combine(cloneDirectory, PyRevitLabsConsts.DefaultConfigsFileName)));
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
    [Test]
    public void AnIsolatedLaunchSetsTheSessionOverrides() {
        var startInfo = ChildOf();

        PyRevitLauncher.ConfigureEnvironment(startInfo, @"C:\launch\pyRevit.addin", 2026, @"C:\launch\pyRevit");

        var environment = startInfo.EnvironmentVariables;
        Assert.That(environment[PyRevitConsts.LaunchManifestEnvVar], Is.EqualTo(@"C:\launch\pyRevit.addin"));
        Assert.That(environment[PyRevitConsts.LaunchRevitYearEnvVar], Is.EqualTo("2026"));
        Assert.That(environment[PyRevitLabsConsts.PyRevitPathOverrideEnvVar], Is.EqualTo(@"C:\launch\pyRevit"));
        Assert.That(environment[PyRevitLabsConsts.PyRevitIgnoreLocalConfigEnvVar], Is.EqualTo("1"));
        Assert.That(environment[PyRevitLabsConsts.PyRevitAgentDirOverrideEnvVar], Is.EqualTo(PyRevitLabsConsts.AgentPath));
    }

    /// <summary>
    ///     Verifies that a launch that is not isolated, started from an isolated session, does not inherit the parent's overrides.
    /// </summary>
    [Test]
    public void ALaunchFromAnIsolatedSessionDropsTheInheritedConfigOverrides() {
        var startInfo = ChildOf(
            (PyRevitLabsConsts.PyRevitIgnoreLocalConfigEnvVar, "1"),
            (PyRevitLabsConsts.PyRevitPathOverrideEnvVar, @"C:\parent\pyRevit"),
            (PyRevitLabsConsts.PyRevitAgentDirOverrideEnvVar, @"C:\agent"));

        PyRevitLauncher.ConfigureEnvironment(startInfo, @"C:\launch\pyRevit.addin", 2026, configRoot: null);

        var environment = startInfo.EnvironmentVariables;
        Assert.That(environment.ContainsKey(PyRevitLabsConsts.PyRevitIgnoreLocalConfigEnvVar), Is.False);
        Assert.That(environment.ContainsKey(PyRevitLabsConsts.PyRevitPathOverrideEnvVar), Is.False);
        Assert.That(environment[PyRevitLabsConsts.PyRevitAgentDirOverrideEnvVar], Is.EqualTo(@"C:\agent"));
        Assert.That(environment[PyRevitConsts.LaunchManifestEnvVar], Is.EqualTo(@"C:\launch\pyRevit.addin"));
    }

    /// <summary>
    ///     Verifies that a deliberate config override survives a launch that is not isolated and has no isolated parent.
    /// </summary>
    [Test]
    public void ADeliberateConfigOverrideSurvivesALaunchThatIsNotIsolated() {
        var startInfo = ChildOf((PyRevitLabsConsts.PyRevitPathOverrideEnvVar, @"C:\mine\pyRevit"));

        PyRevitLauncher.ConfigureEnvironment(startInfo, @"C:\launch\pyRevit.addin", 2026, configRoot: null);

        Assert.That(startInfo.EnvironmentVariables[PyRevitLabsConsts.PyRevitPathOverrideEnvVar], Is.EqualTo(@"C:\mine\pyRevit"));
    }

    /// <summary>
    ///     Verifies that the isolation setting hides the clone-local config so the per-session folder is used.
    /// </summary>
    [Test]
    public void ACloneLocalConfigIsIgnoredInAnIsolatedSession() {
        Environment.SetEnvironmentVariable(PyRevitLabsConsts.PyRevitIgnoreLocalConfigEnvVar, "1");

        Assert.That(PyRevitInstallScope.GetLocalConfigFilePath(), Is.Null);
    }
}
