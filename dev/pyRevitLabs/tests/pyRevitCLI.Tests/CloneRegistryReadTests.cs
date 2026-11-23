using pyRevitLabs.Common;
using pyRevitLabs.Configurations.Ini;
using pyRevitLabs.Configurations.Sections;
using pyRevitLabs.PyRevit;

namespace pyRevitCLI.Tests;

/// <summary>
///     Verifies that reading the registered clones without pruning keeps registrations whose path is unavailable (#4239).
/// </summary>
[Collection(CliGlobalState.Name)]
[Trait("Environment", "HostFree")]
[Trait("Level", "Integration")]
public class CloneRegistryReadTests : IDisposable {
    private readonly string temp = Path.Combine(Path.GetTempPath(), "pyRevit-clone-registry-tests-" + Guid.NewGuid());
    private readonly string previousPyRevitPath = Environment.GetEnvironmentVariable(PyRevitLabsConsts.PyRevitPathOverrideEnvVar);
    private readonly string previousProgramDataPath = Environment.GetEnvironmentVariable(PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar);
    private readonly string previousIgnoreLocalConfig = Environment.GetEnvironmentVariable(PyRevitLabsConsts.PyRevitIgnoreLocalConfigEnvVar);
    private readonly string presentClonePath;
    private readonly string missingClonePath;

    /// <summary>
    ///     Initializes a new instance of the <see cref="CloneRegistryReadTests"/> class with one existing and one missing registered clone in an isolated user config.
    /// </summary>
    public CloneRegistryReadTests() {
        Environment.SetEnvironmentVariable(PyRevitLabsConsts.PyRevitPathOverrideEnvVar, Path.Combine(temp, "AppDataPyRevit"));
        Environment.SetEnvironmentVariable(PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar, Path.Combine(temp, "ProgramDataPyRevit"));
        Environment.SetEnvironmentVariable(PyRevitLabsConsts.PyRevitIgnoreLocalConfigEnvVar, "1");
        PyRevitInstallScope.ClearCachedInstallScope();
        PyRevitInstallScope.SetRuntimeInstallRoot(null);
        PyRevitConfigService.Reload();
        Directory.CreateDirectory(PyRevitLabsConsts.PyRevitPath);

        presentClonePath = Path.Combine(temp, "present");
        Directory.CreateDirectory(Path.Combine(presentClonePath, "pyrevitlib", "pyrevit"));
        missingClonePath = Path.Combine(temp, "missing");
        PyRevitConfigs.GetConfigFile().SaveSection(new EnvironmentSection {
            Clones = new Dictionary<string, string> {
                { "present", presentClonePath },
                { "missing", missingClonePath },
            }
        });
    }

    /// <inheritdoc />
    public void Dispose() {
        Environment.SetEnvironmentVariable(PyRevitLabsConsts.PyRevitIgnoreLocalConfigEnvVar, previousIgnoreLocalConfig);
        PyRevitConfigService.Reload();
        PyRevitInstallScope.ClearCachedInstallScope();
        PyRevitInstallScope.SetRuntimeInstallRoot(null);
        Environment.SetEnvironmentVariable(PyRevitLabsConsts.PyRevitPathOverrideEnvVar, previousPyRevitPath);
        Environment.SetEnvironmentVariable(PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar, previousProgramDataPath);
        Directory.Delete(temp, true);
    }

    /// <summary>
    ///     A read that does not prune lists only the available clone and leaves the unavailable registration in the config.
    /// </summary>
    [Fact]
    public void GetRegisteredClones_WithoutPruning_KeepsUnavailableRegistration() {
        var clones = PyRevitClones.GetRegisteredClones(pruneStoredList: false);

        Assert.Equal(new[] { "present" }, clones.Select(clone => clone.Name).ToArray());
        Assert.True(PyRevitConfigs.GetConfigFile().Environment.Clones.ContainsKey("missing"));
    }

    /// <summary>
    ///     The default read still prunes the unavailable registration.
    /// </summary>
    [Fact]
    public void GetRegisteredClones_Default_PrunesUnavailableRegistration() {
        PyRevitClones.GetRegisteredClones();

        Assert.False(PyRevitConfigs.GetConfigFile().Environment.Clones.ContainsKey("missing"));
    }
}
