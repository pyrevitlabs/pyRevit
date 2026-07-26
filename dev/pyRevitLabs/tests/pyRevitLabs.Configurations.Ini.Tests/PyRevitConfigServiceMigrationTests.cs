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

    [Fact]
    public void MergeAdminConfigFiles_BringsClonesAndMissingExtensionSectionsIntoTarget()
    {
        var dir = NewTempDir();
        try
        {
            var source = Path.Combine(dir, "source.ini");
            var target = Path.Combine(dir, "target.ini");

            // Per-user (split) config: has the clone registry and one extension.
            File.WriteAllText(source,
                "[environment]\r\nclones = {\"master\":\"C:\\\\TestClone\"}\r\n" +
                "[pyRevitTags.extension]\r\ndisabled = true\r\n");
            // Machine config: has a different extension, no clones.
            File.WriteAllText(target,
                "[pyRevitTemplates.extension]\r\ndisabled = true\r\n");

            PyRevitConfigService.MergeAdminConfigFiles(source, target);

            var merged = File.ReadAllText(target);
            Assert.Contains("clones", merged);
            Assert.Contains("TestClone", merged);
            Assert.Contains("pyRevitTags.extension", merged);      // brought over
            Assert.Contains("pyRevitTemplates.extension", merged); // preserved
        }
        finally
        {
            Directory.Delete(dir, recursive: true);
        }
    }

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
            // Target already owns clones and the shared extension with its own values.
            File.WriteAllText(target,
                "[environment]\r\nclones = {\"master\":\"C:\\\\TargetClone\"}\r\n" +
                "[shared.extension]\r\ndisabled = false\r\n");

            PyRevitConfigService.MergeAdminConfigFiles(source, target);

            var merged = File.ReadAllText(target);
            Assert.Contains("TargetClone", merged);   // existing clone registry kept
            Assert.DoesNotContain("SourceClone", merged);
            Assert.DoesNotContain("true", merged);    // existing shared.extension disabled=false kept
        }
        finally
        {
            Directory.Delete(dir, recursive: true);
        }
    }
}
