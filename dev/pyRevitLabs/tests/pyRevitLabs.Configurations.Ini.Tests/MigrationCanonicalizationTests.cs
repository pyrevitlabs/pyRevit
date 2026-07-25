using System;
using System.Collections.Generic;
using System.IO;
using pyRevitLabs.Configurations;
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
            .AddIniConfiguration(path, ConfigurationService.DefaultConfigurationName)
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

            // The stored form is now canonical JSON, and the values survive.
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
}
