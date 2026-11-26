using pyRevitLabs.Common;
using pyRevitLabs.Configurations.Ini;
using pyRevitLabs.Configurations.Sections;
using pyRevitLabs.PyRevit;

namespace pyRevitCLI.Tests;

/// <summary>
///     Verifies that <c>pyrevit clones delete &lt;name&gt; --clearconfigs</c> keeps the user config and the other clones (#4219).
/// </summary>
[Collection(CliGlobalState.Name)]
[Trait("Environment", "HostFree")]
[Trait("Level", "Integration")]
public class CloneDeleteCommandTests : IDisposable {
    private readonly string temp = Path.Combine(Path.GetTempPath(), "pyRevit-clone-delete-tests-" + Guid.NewGuid());
    private readonly string previousPyRevitPath = Environment.GetEnvironmentVariable(PyRevitLabsConsts.PyRevitPathOverrideEnvVar);
    private readonly string previousProgramDataPath = Environment.GetEnvironmentVariable(PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar);
    private readonly string firstClonePath;
    private readonly string secondClonePath;

    /// <summary>
    ///     Initializes a new instance of the <see cref="CloneDeleteCommandTests"/> class with two registered clones and a saved setting in an isolated user config.
    /// </summary>
    public CloneDeleteCommandTests() {
        Environment.SetEnvironmentVariable(PyRevitLabsConsts.PyRevitPathOverrideEnvVar, Path.Combine(temp, "AppDataPyRevit"));
        Environment.SetEnvironmentVariable(PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar, Path.Combine(temp, "ProgramDataPyRevit"));
        PyRevitInstallScope.ClearCachedInstallScope();
        PyRevitInstallScope.SetRuntimeInstallRoot(null);
        PyRevitConfigService.Reload();
        Directory.CreateDirectory(PyRevitLabsConsts.PyRevitPath);

        firstClonePath = CreateClone("first");
        secondClonePath = CreateClone("second");
        var config = PyRevitConfigs.GetConfigFile();
        config.SaveSection(new EnvironmentSection {
            Clones = new Dictionary<string, string> {
                { "first", firstClonePath },
                { "second", secondClonePath },
            }
        });
        config.SaveSection(new CoreSection { UserLocale = "de_de" });
    }

    /// <inheritdoc />
    public void Dispose() {
        PyRevitConfigService.Reload();
        PyRevitInstallScope.ClearCachedInstallScope();
        PyRevitInstallScope.SetRuntimeInstallRoot(null);
        Environment.SetEnvironmentVariable(PyRevitLabsConsts.PyRevitPathOverrideEnvVar, previousPyRevitPath);
        Environment.SetEnvironmentVariable(PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar, previousProgramDataPath);
        Directory.Delete(temp, true);
    }

    private string CreateClone(string name) {
        var clonePath = Path.Combine(temp, name);
        Directory.CreateDirectory(Path.Combine(clonePath, "pyrevitlib", "pyrevit"));
        return clonePath;
    }

    /// <summary>
    ///     Verifies that deleting one clone with <c>--clearconfigs</c> removes only that clone, keeps the other clone and the saved setting, and warns on stderr.
    /// </summary>
    [Fact]
    public void ClearConfigsOnASingleCloneKeepsTheConfigAndTheOtherClones() {
        var error = new StringWriter();

        PyRevitCLICloneDeletion.Delete(allClones: false, cloneName: "first", clearConfigs: true, error);

        Assert.False(Directory.Exists(firstClonePath));
        Assert.True(Directory.Exists(secondClonePath));
        PyRevitConfigService.Reload();
        Assert.Equal(new[] { "second" }, PyRevitClones.GetRegisteredClones().Select(clone => clone.Name).ToArray());
        Assert.Equal("de_de", PyRevitConfigs.GetConfigFile().Core.UserLocale);
        Assert.Contains(PyRevitCLICloneDeletion.ClearConfigsIgnoredWarning, error.ToString());
    }

    /// <summary>
    ///     Verifies that deleting every clone with <c>--clearconfigs</c> still discards the saved setting.
    /// </summary>
    [Fact]
    public void ClearConfigsWithAllDiscardsTheSavedSetting() {
        PyRevitCLICloneDeletion.Delete(allClones: true, cloneName: null, clearConfigs: true, new StringWriter());

        Assert.False(Directory.Exists(firstClonePath));
        Assert.False(Directory.Exists(secondClonePath));
        PyRevitConfigService.Reload();
        Assert.Null(PyRevitConfigs.GetConfigFile().Core.UserLocale);
        Assert.Empty(PyRevitClones.GetRegisteredClones());
    }
}
