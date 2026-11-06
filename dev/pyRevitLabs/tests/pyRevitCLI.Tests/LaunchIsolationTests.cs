using pyRevitLabs.Common;

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

    /// <summary>
    ///     Verifies that the isolation setting hides the clone-local config so the per-session folder is used.
    /// </summary>
    [Fact]
    public void ACloneLocalConfigIsIgnoredInAnIsolatedSession() {
        Environment.SetEnvironmentVariable(PyRevitLabsConsts.PyRevitIgnoreLocalConfigEnvVar, "1");

        Assert.Null(PyRevitInstallScope.GetLocalConfigFilePath());
    }
}
