using System;
using System.IO;
using pyRevitLabs.Configurations.Ini;

namespace pyRevitLabs.Configurations.Ini.Tests;

/// <summary>
/// Covers the split-config repair: on a machine install whose clone registry
/// and per-extension settings live in the per-user config, merge the clone
/// registry and any missing extension sections into the machine config.
/// Operates on explicit temp files, so it needs no install-scope state and is
/// safe to run in parallel.
/// </summary>
public class PyRevitConfigServiceMigrationTests
{
    private static string NewTempDir()
    {
        var dir = Path.Combine(Path.GetTempPath(), "cfgmerge_" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(dir);
        return dir;
    }

    /// <summary>
    /// Source is a per-user (split) config holding the clone registry and one
    /// extension section; target is the machine config with a different extension
    /// and no clones.
    /// </summary>
    [Fact]
    public void MergeAdminConfigFiles_BringsClonesAndMissingExtensionSectionsIntoTarget()
    {
        var dir = NewTempDir();
        try
        {
            var source = Path.Combine(dir, "source.ini");
            var target = Path.Combine(dir, "target.ini");

            File.WriteAllText(source,
                "[environment]\r\nclones = {\"master\":\"C:\\\\TestClone\"}\r\n" +
                "[pyRevitTags.extension]\r\ndisabled = true\r\n");
            File.WriteAllText(target,
                "[pyRevitTemplates.extension]\r\ndisabled = true\r\n");

            Assert.True(PyRevitConfigService.MergeAdminConfigFiles(source, target));

            var merged = File.ReadAllText(target);
            Assert.Contains("clones", merged);
            Assert.Contains("TestClone", merged);
            Assert.Contains("pyRevitTags.extension", merged);
            Assert.Contains("pyRevitTemplates.extension", merged);
        }
        finally
        {
            Directory.Delete(dir, recursive: true);
        }
    }

    /// <summary>
    /// Target already owns the clone registry and the shared extension with its own
    /// values, so the merge from source must not overwrite either.
    /// </summary>
    [Fact]
    public void MergeAdminConfigFiles_DoesNotOverwriteExistingTargetSectionsOrClones()
    {
        var dir = NewTempDir();
        try
        {
            var source = Path.Combine(dir, "source.ini");
            var target = Path.Combine(dir, "target.ini");

            File.WriteAllText(source,
                "[environment]\r\nclones = {\"master\":\"C:\\\\SourceClone\"}\r\n" +
                "[shared.extension]\r\ndisabled = true\r\n");
            File.WriteAllText(target,
                "[environment]\r\nclones = {\"master\":\"C:\\\\TargetClone\"}\r\n" +
                "[shared.extension]\r\ndisabled = false\r\n");

            Assert.False(PyRevitConfigService.MergeAdminConfigFiles(source, target));

            var merged = File.ReadAllText(target);
            Assert.Contains("TargetClone", merged);
            Assert.DoesNotContain("SourceClone", merged);
            Assert.DoesNotContain("true", merged);
        }
        finally
        {
            Directory.Delete(dir, recursive: true);
        }
    }

    private static string[] RetiredCopies(string userConfigPath) =>
        Directory.GetFiles(
            Path.GetDirectoryName(userConfigPath)!,
            Path.GetFileName(userConfigPath) + ".split-admin.*.bak");

    /// <summary>
    /// The per-user config holds settings the merge never carries ([core], [routes],
    /// [telemetry]). Retiring it when nothing moved into the machine config would
    /// discard the only copy of those, and would do so again every load.
    /// </summary>
    [Fact]
    public void RepairSplitAdminConfig_KeepsUserConfig_WhenNothingWasMerged()
    {
        var dir = NewTempDir();
        try
        {
            var userConfig = Path.Combine(dir, "user.ini");
            var machineConfig = Path.Combine(dir, "machine.ini");

            File.WriteAllText(userConfig,
                "[environment]\r\nclones = {\"master\":\"C:\\\\Clone\"}\r\n" +
                "[core]\r\ncheckupdates = true\r\n");
            File.WriteAllText(machineConfig,
                "[environment]\r\nclones = {\"master\":\"C:\\\\Clone\"}\r\n");

            PyRevitConfigService.RepairSplitAdminConfig(userConfig, machineConfig);

            Assert.True(File.Exists(userConfig));
            Assert.Empty(RetiredCopies(userConfig));
            Assert.Contains("checkupdates", File.ReadAllText(userConfig));
        }
        finally
        {
            Directory.Delete(dir, recursive: true);
        }
    }

    [Fact]
    public void RepairSplitAdminConfig_RetiresUserConfig_WhenSettingsMoved()
    {
        var dir = NewTempDir();
        try
        {
            var userConfig = Path.Combine(dir, "user.ini");
            var machineConfig = Path.Combine(dir, "machine.ini");

            File.WriteAllText(userConfig,
                "[environment]\r\nclones = {\"master\":\"C:\\\\Clone\"}\r\n");
            File.WriteAllText(machineConfig, "[core]\r\ncheckupdates = true\r\n");

            PyRevitConfigService.RepairSplitAdminConfig(userConfig, machineConfig);

            Assert.False(File.Exists(userConfig));
            Assert.Single(RetiredCopies(userConfig));
            Assert.Contains("Clone", File.ReadAllText(machineConfig));
        }
        finally
        {
            Directory.Delete(dir, recursive: true);
        }
    }

    /// <summary>
    /// A second pass over an already-repaired install must be inert: the machine
    /// config already owns everything the merge carries, so no further copy is
    /// retired and the config in use is left alone. The user-config file is
    /// rewritten mid-test to stand in for whatever config the next session would
    /// resolve to.
    /// </summary>
    [Fact]
    public void RepairSplitAdminConfig_IsInertOnASecondPass()
    {
        var dir = NewTempDir();
        try
        {
            var userConfig = Path.Combine(dir, "user.ini");
            var machineConfig = Path.Combine(dir, "machine.ini");

            File.WriteAllText(userConfig,
                "[environment]\r\nclones = {\"master\":\"C:\\\\Clone\"}\r\n");
            File.WriteAllText(machineConfig, "[core]\r\ncheckupdates = true\r\n");

            PyRevitConfigService.RepairSplitAdminConfig(userConfig, machineConfig);

            File.WriteAllText(userConfig, "[core]\r\ncheckupdates = false\r\n");
            PyRevitConfigService.RepairSplitAdminConfig(userConfig, machineConfig);

            Assert.True(File.Exists(userConfig));
            Assert.Single(RetiredCopies(userConfig));
        }
        finally
        {
            Directory.Delete(dir, recursive: true);
        }
    }

    [Fact]
    public void RepairSplitAdminConfig_PromotesUserConfig_WhenMachineConfigMissing()
    {
        var dir = NewTempDir();
        try
        {
            var userConfig = Path.Combine(dir, "user.ini");
            var machineConfig = Path.Combine(dir, "machine.ini");

            File.WriteAllText(userConfig,
                "[environment]\r\nclones = {\"master\":\"C:\\\\Clone\"}\r\n");

            PyRevitConfigService.RepairSplitAdminConfig(userConfig, machineConfig);

            Assert.True(File.Exists(machineConfig));
            Assert.Contains("Clone", File.ReadAllText(machineConfig));
            Assert.False(File.Exists(userConfig));
            Assert.Single(RetiredCopies(userConfig));
        }
        finally
        {
            Directory.Delete(dir, recursive: true);
        }
    }
}
