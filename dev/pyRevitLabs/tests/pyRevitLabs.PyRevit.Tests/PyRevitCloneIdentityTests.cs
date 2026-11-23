using pyRevitLabs.Common;
using pyRevitLabs.Common.Extensions;
using pyRevitLabs.Configurations.Ini;
using pyRevitLabs.Configurations.Sections;
using pyRevitLabs.NLog;
using pyRevitLabs.NLog.Config;
using pyRevitLabs.NLog.Targets;
using pyRevitLabs.PyRevit;

namespace pyRevitLabs.PyRevit.Tests;

/// <summary>
///     Regression tests for #4041: clone identity comparisons and the reporting of rejected registered clones.
/// </summary>
[TestFixture]
[FixtureLifeCycle(LifeCycle.InstancePerTestCase)]
[NonParallelizable]
[Category("HostFree")]
[Category("Unit")]
[Category("Regression")]
public class PyRevitCloneIdentityTests {
    private string _tempRoot = string.Empty;
    private string? _previousPyRevitPathOverride;
    private string? _previousProgramDataPathOverride;
    private LoggingConfiguration? _previousLogConfiguration;

    /// <summary>Redirects pyRevit data folders to a temporary root and captures the logging configuration.</summary>
    [SetUp]
    public void Setup() {
        _tempRoot = Path.Combine(Path.GetTempPath(), "pyRevitCloneIdentity_" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(_tempRoot);
        _previousPyRevitPathOverride = Environment.GetEnvironmentVariable(PyRevitLabsConsts.PyRevitPathOverrideEnvVar);
        _previousProgramDataPathOverride = Environment.GetEnvironmentVariable(PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar);
        Environment.SetEnvironmentVariable(
            PyRevitLabsConsts.PyRevitPathOverrideEnvVar,
            Path.Combine(_tempRoot, "AppDataPyRevit"));
        Environment.SetEnvironmentVariable(
            PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar,
            Path.Combine(_tempRoot, "ProgramDataPyRevit"));
        PyRevitInstallScope.ClearCachedInstallScope();
        PyRevitInstallScope.SetRuntimeInstallRoot(null);
        PyRevitConfigService.Reload();
        Directory.CreateDirectory(PyRevitLabsConsts.PyRevitPath);
        _previousLogConfiguration = LogManager.Configuration;
    }

    /// <summary>Restores environment overrides, logging and the install scope, then deletes the temporary root.</summary>
    [TearDown]
    public void Cleanup() {
        LogManager.Configuration = _previousLogConfiguration;
        PyRevitConfigService.Reload();
        PyRevitInstallScope.ClearCachedInstallScope();
        PyRevitInstallScope.SetRuntimeInstallRoot(null);
        Environment.SetEnvironmentVariable(
            PyRevitLabsConsts.PyRevitPathOverrideEnvVar,
            _previousPyRevitPathOverride);
        Environment.SetEnvironmentVariable(
            PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar,
            _previousProgramDataPathOverride);
        if (Directory.Exists(_tempRoot))
            CommonUtils.DeleteDirectory(_tempRoot);
    }

    private string CreateClone(string name) {
        var clonePath = Path.Combine(_tempRoot, name);
        Directory.CreateDirectory(Path.Combine(clonePath, "pyrevitlib", "pyrevit"));
        return clonePath;
    }

    private static MemoryTarget CaptureLogs(LogLevel minLevel) {
        var target = new MemoryTarget("memory") { Layout = "${level}|${message}" };
        var logConfiguration = new LoggingConfiguration();
        logConfiguration.AddRule(minLevel, LogLevel.Fatal, target);
        LogManager.Configuration = logConfiguration;
        return target;
    }

    private static void RegisterClones(Dictionary<string, string> clones) {
        PyRevitConfigs.GetConfigFile().SaveSection(new EnvironmentSection { Clones = clones });
    }

    /// <summary>Null and foreign types are never equal to a clone.</summary>
    [Test]
    public void Equals_NullAndForeignTypes_AreNotEqual() {
        var clone = new PyRevitClone(CreateClone("a"), name: "a");

        Assert.That(clone.Equals(null), Is.False);
        Assert.That(clone.Equals("not a clone"), Is.False);
    }

    /// <summary>Clones whose paths differ only in case are equal and share a hash code.</summary>
    [Test]
    public void Equals_PathsDifferingOnlyInCase_AreEqualAndHashAlike() {
        var path = CreateClone("CaseClone");
        var first = new PyRevitClone(path, name: "first");
        var second = new PyRevitClone(path.ToUpperInvariant(), name: "second");

        Assert.That(first.Equals(second), Is.True);
        Assert.That(second.GetHashCode(), Is.EqualTo(first.GetHashCode()));
    }

    /// <summary>A clone matches a path differing only in case.</summary>
    [Test]
    public void Matches_PathDifferingOnlyInCase_Matches() {
        var path = CreateClone("MatchClone");
        var clone = new PyRevitClone(path, name: "named");

        Assert.That(clone.Matches(path.ToUpperInvariant()), Is.True);
        Assert.That(clone.Matches(path + "2"), Is.False);
    }

    /// <summary>A rejected clone is warned about with its path and reason and stays registered.</summary>
    [Test]
    public void GetRegisteredClones_RejectedClone_IsWarnedWithPathAndReasonAndStaysRegistered() {
        var rejectedPath = Path.Combine(_tempRoot, "rejected");
        Directory.CreateDirectory(rejectedPath);
        var validPath = CreateClone("valid");
        RegisterClones(new Dictionary<string, string> {
            { "rejected", rejectedPath },
            { "valid", validPath },
        });
        var target = CaptureLogs(LogLevel.Warn);

        var clones = PyRevitClones.GetRegisteredClones();

        Assert.That(clones.Select(c => c.Name), Is.EqualTo(new[] { "valid" }));
        var warning = target.Logs.Single(line => line.StartsWith("Warn|"));
        Assert.That(warning, Does.Contain(rejectedPath));
        Assert.That(warning, Does.Contain("not a valid"));
        Assert.That(PyRevitConfigs.GetConfigFile().Environment.Clones.ContainsKey("rejected"), Is.True);
    }

    /// <summary>The same rejected clone is warned about only once across repeated reads.</summary>
    [Test]
    public void GetRegisteredClones_SameRejectedCloneRepeatedly_IsWarnedOnce() {
        var rejectedPath = Path.Combine(_tempRoot, "rejected-repeat");
        Directory.CreateDirectory(rejectedPath);
        RegisterClones(new Dictionary<string, string> { { "rejected-repeat", rejectedPath } });
        var target = CaptureLogs(LogLevel.Warn);

        PyRevitClones.GetRegisteredClones();
        PyRevitClones.GetRegisteredClones();
        PyRevitClones.GetRegisteredClones();

        Assert.That(target.Logs.Count(line => line.StartsWith("Warn|")), Is.EqualTo(1));
    }

    /// <summary>A registered subfolder of a valid clone is accepted without a warning.</summary>
    [Test]
    public void GetRegisteredClones_RegisteredSubfolderOfValidClone_IsAcceptedWithoutWarning() {
        var parentPath = CreateClone("parent");
        var subfolder = Path.Combine(parentPath, "extensions");
        Directory.CreateDirectory(subfolder);
        RegisterClones(new Dictionary<string, string> { { "sub", subfolder } });
        var target = CaptureLogs(LogLevel.Warn);

        var clones = PyRevitClones.GetRegisteredClones();

        Assert.That(clones.Count, Is.EqualTo(1));
        Assert.That(clones[0].ClonePath.IsSamePathAs(parentPath), Is.True);
        Assert.That(target.Logs.Count, Is.EqualTo(0));
    }

    /// <summary>A clone that is repaired and then broken again is warned about again.</summary>
    [Test]
    public void GetRegisteredClones_CloneRepairedThenBrokenAgain_IsWarnedAgain() {
        var path = Path.Combine(_tempRoot, "flaky");
        Directory.CreateDirectory(path);
        RegisterClones(new Dictionary<string, string> { { "flaky", path } });
        var target = CaptureLogs(LogLevel.Warn);

        PyRevitClones.GetRegisteredClones();
        Directory.CreateDirectory(Path.Combine(path, "pyrevitlib", "pyrevit"));
        Assert.That(PyRevitClones.GetRegisteredClones().Count, Is.EqualTo(1));
        Directory.Delete(Path.Combine(path, "pyrevitlib"), true);
        PyRevitClones.GetRegisteredClones();

        Assert.That(target.Logs.Count(line => line.StartsWith("Warn|")), Is.EqualTo(2));
    }

    /// <summary>A case-differing duplicate is kept once and logged when pruned.</summary>
    [Test]
    public void GetRegisteredClones_DuplicateDifferingInCase_IsKeptOnceAndLoggedWhenPruned() {
        var path = CreateClone("dup");
        var missing = Path.Combine(_tempRoot, "missing");
        RegisterClones(new Dictionary<string, string> {
            { "first", path },
            { "alias", path.ToUpperInvariant() },
            { "gone", missing },
        });
        var target = CaptureLogs(LogLevel.Info);

        var clones = PyRevitClones.GetRegisteredClones();

        Assert.That(clones.Select(c => c.Name), Is.EqualTo(new[] { "first" }));
        var info = target.Logs.Single(line => line.StartsWith("Info|"));
        Assert.That(info, Does.Contain("alias"));
        Assert.That(info, Does.Contain("first"));
    }
}
