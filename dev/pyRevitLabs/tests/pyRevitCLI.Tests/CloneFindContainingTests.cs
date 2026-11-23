using pyRevitLabs.Common;
using pyRevitLabs.Common.Extensions;
using pyRevitLabs.Configurations.Ini;
using pyRevitLabs.Configurations.Sections;
using pyRevitLabs.PyRevit;

namespace pyRevitCLI.Tests;

/// <summary>
///     Verifies that the clone found for a runner path is the nearest clone, also when it lies inside another registered clone.
/// </summary>
[Collection(CliGlobalState.Name)]
[Trait("Environment", "HostFree")]
[Trait("Level", "Integration")]
public class CloneFindContainingTests : IDisposable {
    private readonly string temp = Path.Combine(Path.GetTempPath(), "pyRevit-find-containing-tests-" + Guid.NewGuid());
    private readonly string previousPyRevitPath = Environment.GetEnvironmentVariable(PyRevitLabsConsts.PyRevitPathOverrideEnvVar);
    private readonly string previousProgramDataPath = Environment.GetEnvironmentVariable(PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar);
    private readonly string previousIgnoreLocalConfig = Environment.GetEnvironmentVariable(PyRevitLabsConsts.PyRevitIgnoreLocalConfigEnvVar);
    private readonly string outerClonePath;
    private readonly string nestedClonePath;

    /// <summary>
    ///     Initializes a new instance of the <see cref="CloneFindContainingTests"/> class with a registered clone that contains an unregistered clone.
    /// </summary>
    public CloneFindContainingTests() {
        Environment.SetEnvironmentVariable(PyRevitLabsConsts.PyRevitPathOverrideEnvVar, Path.Combine(temp, "AppDataPyRevit"));
        Environment.SetEnvironmentVariable(PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar, Path.Combine(temp, "ProgramDataPyRevit"));
        Environment.SetEnvironmentVariable(PyRevitLabsConsts.PyRevitIgnoreLocalConfigEnvVar, "1");
        PyRevitInstallScope.ClearCachedInstallScope();
        PyRevitInstallScope.SetRuntimeInstallRoot(null);
        PyRevitConfigService.Reload();
        Directory.CreateDirectory(PyRevitLabsConsts.PyRevitPath);

        outerClonePath = Path.Combine(temp, "outer");
        nestedClonePath = Path.Combine(outerClonePath, "worktrees", "inner");
        Directory.CreateDirectory(Path.Combine(outerClonePath, "pyrevitlib", "pyrevit"));
        Directory.CreateDirectory(Path.Combine(nestedClonePath, "pyrevitlib", "pyrevit"));
        PyRevitConfigs.GetConfigFile().SaveSection(new EnvironmentSection {
            Clones = new Dictionary<string, string> { { "outer", outerClonePath } }
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
    ///     A runner inside the nested clone belongs to the nested clone, not to the registered clone around it.
    /// </summary>
    [Fact]
    public void FindContaining_RunnerInNestedClone_ReturnsTheNestedClone() {
        var runnerPath = Path.Combine(nestedClonePath, "bin", "engines", "IPY342", "pyRevitRunner.dll");

        var clone = PyRevitClones.FindContaining(runnerPath);

        Assert.True(clone.ClonePath.IsSamePathAs(nestedClonePath));
        Assert.Equal("inner", clone.Name);
    }

    /// <summary>
    ///     A runner in a clone whose folder name is reserved still belongs to that clone, not to the registered clone around it.
    /// </summary>
    [Fact]
    public void FindContaining_RunnerInNestedCloneWithReservedFolderName_ReturnsTheNestedClone() {
        var reservedClonePath = Path.Combine(outerClonePath, "worktrees", "docs");
        Directory.CreateDirectory(Path.Combine(reservedClonePath, "pyrevitlib", "pyrevit"));
        var runnerPath = Path.Combine(reservedClonePath, "bin", "engines", "IPY342", "pyRevitRunner.dll");

        var clone = PyRevitClones.FindContaining(runnerPath);

        Assert.True(clone.ClonePath.IsSamePathAs(reservedClonePath));
    }

    /// <summary>
    ///     Looking up the clone of a runner never rewrites the stored clones list, even when it holds a stale entry.
    /// </summary>
    [Fact]
    public void FindContaining_StaleRegistration_DoesNotPruneTheStoredList() {
        var staleClonePath = Path.Combine(temp, "gone");
        PyRevitConfigs.GetConfigFile().SaveSection(new EnvironmentSection {
            Clones = new Dictionary<string, string> { { "outer", outerClonePath }, { "stale", staleClonePath } }
        });
        var runnerPath = Path.Combine(outerClonePath, "bin", "engines", "IPY342", "pyRevitRunner.dll");

        PyRevitClones.FindContaining(runnerPath);

        Assert.True(PyRevitConfigs.GetConfigFile().Environment.Clones.ContainsKey("stale"));
    }

    /// <summary>
    ///     A runner inside a registered clone returns that registration with its name.
    /// </summary>
    [Fact]
    public void FindContaining_RunnerInRegisteredClone_KeepsTheRegisteredName() {
        var runnerPath = Path.Combine(outerClonePath, "bin", "engines", "IPY342", "pyRevitRunner.dll");

        var clone = PyRevitClones.FindContaining(runnerPath);

        Assert.Equal("outer", clone.Name);
    }
}
