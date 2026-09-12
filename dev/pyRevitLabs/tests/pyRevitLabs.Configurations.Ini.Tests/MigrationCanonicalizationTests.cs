using System;
using System.Collections.Generic;
using System.IO;
using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Ini.Extensions;

namespace pyRevitLabs.Configurations.Ini.Tests;

/// <summary>
/// Covers the migrator rewriting a legacy Python single-quoted list to canonical
/// JSON: the value survives, it is reported as converted (not reset), and a
/// second pass is a no-op because the canonical form is not detected as legacy.
/// </summary>
public class MigrationCanonicalizationTests
{
    private static string WriteTemp(string content)
    {
        string path = Path.Combine(Path.GetTempPath(), $"canon_{Guid.NewGuid():N}.ini");
        File.WriteAllText(path, content);
        return path;
    }

    private static IConfigurationService Build(string path) =>
        new ConfigurationBuilder(false)
            .AddIniConfiguration(path)
            .Build();

    [Fact]
    public void Migration_CanonicalizesLegacySingleQuotedList()
    {
        string path = WriteTemp("[core]\nuserextensions = ['C:\\Tools\\ext1','D:\\ext2']\n");
        try
        {
            var result = ConfigurationMigrator.Migrate(Build(path));

            Assert.True(result.Migrated);
            Assert.Contains("core.userextensions", result.ConvertedKeys);
            Assert.DoesNotContain("core.userextensions", result.ResetKeys);

            string text = File.ReadAllText(path);
            Assert.Contains("\"", text);
            Assert.DoesNotContain("'C:", text);

            Assert.Equal(
                new List<string> { @"C:\Tools\ext1", @"D:\ext2" },
                IniConfiguration.Create(path).GetValue<List<string>>("core", "userextensions"));
        }
        finally
        {
            File.Delete(path);
        }
    }

    [Fact]
    public void Migration_LegacyListCanonicalization_IsIdempotent()
    {
        string path = WriteTemp("[core]\nuserextensions = ['C:\\Tools\\ext1']\n");
        try
        {
            Assert.Contains("core.userextensions", ConfigurationMigrator.Migrate(Build(path)).ConvertedKeys);

            var second = ConfigurationMigrator.Migrate(Build(path));
            Assert.False(second.Migrated);
            Assert.Empty(second.ConvertedKeys);
        }
        finally
        {
            File.Delete(path);
        }
    }

    [Fact]
    public void Migration_CanonicalizesLegacySingleQuotedCloneRegistry()
    {
        string path = WriteTemp(
            "[environment]\nclones = {'dev': 'C:\\pyRevit', 'main': 'D:\\clones\\main'}\n");
        try
        {
            var result = ConfigurationMigrator.Migrate(Build(path));

            Assert.True(result.Migrated);
            Assert.Contains("environment.clones", result.ConvertedKeys);
            Assert.DoesNotContain("environment.clones", result.ResetKeys);

            string text = File.ReadAllText(path);
            Assert.DoesNotContain("'dev'", text);

            Assert.Equal(
                new Dictionary<string, string> { ["dev"] = @"C:\pyRevit", ["main"] = @"D:\clones\main" },
                IniConfiguration.Create(path).GetValue<Dictionary<string, string>>("environment", "clones"));
        }
        finally
        {
            File.Delete(path);
        }
    }

    [Fact]
    public void Migration_LegacyCloneRegistryCanonicalization_IsIdempotent()
    {
        string path = WriteTemp("[environment]\nclones = {'dev': 'C:\\pyRevit'}\n");
        try
        {
            Assert.Contains("environment.clones", ConfigurationMigrator.Migrate(Build(path)).ConvertedKeys);

            var second = ConfigurationMigrator.Migrate(Build(path));
            Assert.False(second.Migrated);
            Assert.Empty(second.ConvertedKeys);
        }
        finally
        {
            File.Delete(path);
        }
    }

    /// <summary>
    /// A clone path containing an apostrophe is spelled with double quotes even in
    /// the legacy form, so it is left alone rather than being rewritten. Detecting
    /// it as legacy would risk re-converting a canonical value on every load.
    /// </summary>
    [Fact]
    public void Migration_CloneRegistryWithApostrophe_IsLeftAlone()
    {
        string path = WriteTemp("[environment]\nclones = {\"dev\": \"C:\\\\Bob's Clone\"}\n");
        try
        {
            var result = ConfigurationMigrator.Migrate(Build(path));

            Assert.Empty(result.ConvertedKeys);
            Assert.DoesNotContain("environment.clones", result.ResetKeys);
            Assert.Equal(
                @"C:\Bob's Clone",
                IniConfiguration.Create(path).GetValue<Dictionary<string, string>>("environment", "clones")["dev"]);
        }
        finally
        {
            File.Delete(path);
            foreach (string backup in Directory.GetFiles(
                         Path.GetDirectoryName(path)!, Path.GetFileName(path) + "*.bak"))
            {
                File.Delete(backup);
            }
        }
    }

    /// <summary>
    /// The canonical empty list and dict are also the shortest legacy-looking
    /// literals. Treating either as legacy would rewrite and re-back-up the config
    /// on every load, since the rewrite reproduces the same text. The first pass
    /// still stamps the schema version even though nothing here counts as a
    /// converted legacy value.
    /// </summary>
    [Fact]
    public void Migration_CanonicalEmptyContainers_AreNotDetectedAsLegacy()
    {
        string path = WriteTemp(
            "[core]\nuserextensions = []\n\n[environment]\nsources = []\nclones = {}\n");
        try
        {
            var first = ConfigurationMigrator.Migrate(Build(path));
            Assert.Empty(first.ConvertedKeys);

            var second = ConfigurationMigrator.Migrate(Build(path));
            Assert.False(second.Migrated);
            Assert.Empty(second.ConvertedKeys);
            Assert.Null(second.BackupPath);
        }
        finally
        {
            File.Delete(path);
            foreach (string backup in Directory.GetFiles(
                         Path.GetDirectoryName(path)!, Path.GetFileName(path) + "*.bak"))
            {
                File.Delete(backup);
            }
        }
    }
}
