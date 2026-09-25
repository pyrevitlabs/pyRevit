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
public class PyRevitConfigServiceMigrationTests {
    private static string NewTempDir() {
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
    public void MergeAdminConfigFiles_BringsClonesAndMissingExtensionSectionsIntoTarget() {
        var dir = NewTempDir();
        try {
            var source = Path.Combine(dir, "source.ini");
            var target = Path.Combine(dir, "target.ini");

            File.WriteAllText(source,
                "[environment]\r\nclones = {\"master\":\"C:\\\\TestClone\"}\r\n" +
                "[pyRevitTags.extension]\r\ndisabled = true\r\n");
            File.WriteAllText(target,
                "[pyRevitTemplates.extension]\r\ndisabled = true\r\n");

            Assert.True(PyRevitConfigService.MergeAdminConfigFiles(source, target, out bool credsLeft));
            Assert.False(credsLeft);

            var merged = File.ReadAllText(target);
            Assert.Contains("clones", merged);
            Assert.Contains("TestClone", merged);
            Assert.Contains("pyRevitTags.extension", merged);
            Assert.Contains("pyRevitTemplates.extension", merged);
        }
        finally {
            Directory.Delete(dir, recursive: true);
        }
    }

    /// <summary>
    /// Target already owns the clone registry and the shared extension with its own
    /// values, so the merge from source must not overwrite either.
    /// </summary>
    [Fact]
    public void MergeAdminConfigFiles_DoesNotOverwriteExistingTargetSectionsOrClones() {
        var dir = NewTempDir();
        try {
            var source = Path.Combine(dir, "source.ini");
            var target = Path.Combine(dir, "target.ini");

            File.WriteAllText(source,
                "[environment]\r\nclones = {\"master\":\"C:\\\\SourceClone\"}\r\n" +
                "[shared.extension]\r\ndisabled = true\r\n");
            File.WriteAllText(target,
                "[environment]\r\nclones = {\"master\":\"C:\\\\TargetClone\"}\r\n" +
                "[shared.extension]\r\ndisabled = false\r\n");

            Assert.False(PyRevitConfigService.MergeAdminConfigFiles(source, target, out _));

            var merged = File.ReadAllText(target);
            Assert.Contains("TargetClone", merged);
            Assert.DoesNotContain("SourceClone", merged);
            Assert.DoesNotContain("true", merged);
        }
        finally {
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
    public void RepairSplitAdminConfig_KeepsUserConfig_WhenNothingWasMerged() {
        var dir = NewTempDir();
        try {
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
        finally {
            Directory.Delete(dir, recursive: true);
        }
    }

    [Fact]
    public void RepairSplitAdminConfig_RetiresUserConfig_WhenSettingsMoved() {
        var dir = NewTempDir();
        try {
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
        finally {
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
    public void RepairSplitAdminConfig_IsInertOnASecondPass() {
        var dir = NewTempDir();
        try {
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
        finally {
            Directory.Delete(dir, recursive: true);
        }
    }

    [Fact]
    public void RepairSplitAdminConfig_PromotesUserConfig_WhenMachineConfigMissing() {
        var dir = NewTempDir();
        try {
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
        finally {
            Directory.Delete(dir, recursive: true);
        }
    }

    /// <summary>
    /// The promote path copies the whole per-user file, so a credential comes with
    /// it. A machine config sits in ProgramData where every local user can read
    /// it, so the credential has to be stripped on the way in.
    /// </summary>
    [Fact]
    public void RepairSplitAdminConfig_StripsCredentialsFromPromotedMachineConfig() {
        var dir = NewTempDir();
        try {
            var userConfig = Path.Combine(dir, "user.ini");
            var machineConfig = Path.Combine(dir, "machine.ini");

            File.WriteAllText(userConfig,
                "[environment]\r\nclones = {\"master\":\"C:\\\\Clone\"}\r\n" +
                "[Private.extension]\r\ndisabled = false\r\nprivate_repo = true\r\n" +
                "credential = \"SEALED-BLOB\"\r\ntoken = \"ghp_plaintext\"\r\n" +
                "password = \"ghp_plaintext\"\r\nusername = \"oauth2\"\r\n");

            PyRevitConfigService.RepairSplitAdminConfig(userConfig, machineConfig);

            var promoted = File.ReadAllText(machineConfig);
            Assert.DoesNotContain("SEALED-BLOB", promoted);
            Assert.DoesNotContain("ghp_plaintext", promoted);
            Assert.DoesNotContain("username", promoted);
            // Non-credential settings are still carried across.
            Assert.Contains("Private.extension", promoted);
            Assert.Contains("disabled", promoted);
        }
        finally {
            Directory.Delete(dir, recursive: true);
        }
    }

    /// <summary>
    /// Credentials are never copied to a machine config, so the per-user file is
    /// still their only copy and must not be retired. Retiring it would destroy a
    /// working token and silently make the user re-enter it.
    /// </summary>
    [Fact]
    public void RepairSplitAdminConfig_KeepsUserConfig_WhenItHoldsTheOnlyCredential() {
        var dir = NewTempDir();
        try {
            var userConfig = Path.Combine(dir, "user.ini");
            var machineConfig = Path.Combine(dir, "machine.ini");

            File.WriteAllText(userConfig,
                "[Private.extension]\r\ndisabled = false\r\ncredential = \"SEALED-BLOB\"\r\n");
            File.WriteAllText(machineConfig, "[Templates.extension]\r\ndisabled = true\r\n");

            PyRevitConfigService.RepairSplitAdminConfig(userConfig, machineConfig);

            Assert.True(File.Exists(userConfig));
            Assert.Contains("SEALED-BLOB", File.ReadAllText(userConfig));
            Assert.DoesNotContain("SEALED-BLOB", File.ReadAllText(machineConfig));
        }
        finally {
            Directory.Delete(dir, recursive: true);
        }
    }

    /// <summary>
    /// A machine config merged from an older build may already carry a plaintext
    /// token. The merge is the one place that re-reads it, so it is the place
    /// that has to clean it up.
    /// </summary>
    [Fact]
    public void MergeAdminConfigFiles_StripsPreExistingPlaintextFromTarget() {
        var dir = NewTempDir();
        try {
            var source = Path.Combine(dir, "source.ini");
            var target = Path.Combine(dir, "target.ini");

            File.WriteAllText(source,
                "[environment]\r\nclones = {\"master\":\"C:\\\\Source\"}\r\n");
            File.WriteAllText(target,
                "[Legacy.extension]\r\ndisabled = false\r\nprivate_repo = true\r\n" +
                "token = \"ghp_legacy\"\r\nusername = \"oauth2\"\r\n");

            Assert.True(PyRevitConfigService.MergeAdminConfigFiles(source, target, out _));

            var merged = File.ReadAllText(target);
            Assert.DoesNotContain("ghp_legacy", merged);
            Assert.DoesNotContain("username", merged);
            Assert.Contains("Legacy.extension", merged);
        }
        finally {
            Directory.Delete(dir, recursive: true);
        }
    }

    /// <summary>
    /// The merge reports that a credential stayed behind, so the caller knows not
    /// to retire the only copy of it.
    /// </summary>
    [Fact]
    public void MergeAdminConfigFiles_ReportsCredentialsLeftBehind() {
        var dir = NewTempDir();
        try {
            var source = Path.Combine(dir, "source.ini");
            var target = Path.Combine(dir, "target.ini");

            File.WriteAllText(source,
                "[environment]\r\nclones = {\"master\":\"C:\\\\Source\"}\r\n" +
                "[Private.extension]\r\ncredential = \"SEALED-BLOB\"\r\ndisabled = false\r\n");
            File.WriteAllText(target, "[Templates.extension]\r\ndisabled = true\r\n");

            Assert.True(PyRevitConfigService.MergeAdminConfigFiles(source, target, out bool credsLeft));
            Assert.True(credsLeft);
        }
        finally {
            Directory.Delete(dir, recursive: true);
        }
    }

    /// <summary>
    /// A section with no credential must not be mistaken for one, or every
    /// user on a machine install would keep a stale split config forever.
    /// </summary>
    [Fact]
    public void MergeAdminConfigFiles_NoCredentialsMeansNothingLeftBehind() {
        var dir = NewTempDir();
        try {
            var source = Path.Combine(dir, "source.ini");
            var target = Path.Combine(dir, "target.ini");

            File.WriteAllText(source,
                "[environment]\r\nclones = {\"master\":\"C:\\\\Source\"}\r\n" +
                "[Public.extension]\r\ndisabled = false\r\nprivate_repo = true\r\n");
            File.WriteAllText(target, "[Templates.extension]\r\ndisabled = true\r\n");

            Assert.True(PyRevitConfigService.MergeAdminConfigFiles(source, target, out bool credsLeft));
            Assert.False(credsLeft);
        }
        finally {
            Directory.Delete(dir, recursive: true);
        }
    }
}
