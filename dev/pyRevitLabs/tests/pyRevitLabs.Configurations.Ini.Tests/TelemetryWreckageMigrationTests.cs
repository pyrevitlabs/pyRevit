using System;
using System.IO;
using pyRevitLabs.Configurations;
using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Ini.Extensions;

namespace pyRevitLabs.Configurations.Ini.Tests;

/// <summary>
/// Covers migration of telemetry fields that escape-doubling reduced to quote
/// and escape artifacts. These land at 14-16 characters, so a length threshold
/// alone never reaches them, while the values they replaced are unrecoverable.
/// Legitimate short paths and URLs in the same fields must survive untouched.
/// </summary>
public class TelemetryWreckageMigrationTests : IDisposable
{
    private readonly string _dir =
        Directory.CreateDirectory(Path.Combine(Path.GetTempPath(), $"tlm_{Guid.NewGuid():N}")).FullName;

    public void Dispose() => Directory.Delete(_dir, true);

    private string WriteTemp(string content)
    {
        string path = Path.Combine(_dir, "pyRevit_config.ini");
        File.WriteAllText(path, content);
        return path;
    }

    private static IConfigurationService Build(string path) =>
        new ConfigurationBuilder(false)
            .AddIniConfiguration(path, ConfigurationService.DefaultConfigurationName)
            .Build();

    /// <summary>The three field shapes as they appear in an affected config.</summary>
    private const string Wreckage = """
        [telemetry]
        telemetry_file_dir = "\"\\\"\\\"\""
        telemetry_server_url = "\"\\\"\\\"/\"/"
        apptelemetry_server_url = "\"\\\"\\\"/\"/"

        """;

    [Fact]
    public void Migration_ResetsArtifactOnlyTelemetryFields()
    {
        string path = WriteTemp(Wreckage);
        var result = ConfigurationMigrator.Migrate(Build(path));

        Assert.True(result.Migrated);
        Assert.Contains("telemetry.telemetry_file_dir", result.ResetKeys);
        Assert.Contains("telemetry.telemetry_server_url", result.ResetKeys);
        Assert.Contains("telemetry.apptelemetry_server_url", result.ResetKeys);

        string text = File.ReadAllText(path);
        Assert.DoesNotContain("telemetry_file_dir", text);
        Assert.DoesNotContain("telemetry_server_url", text);
    }

    [Fact]
    public void Migration_ArtifactRepair_LeavesBackupAndSettles()
    {
        string path = WriteTemp(Wreckage);
        var first = ConfigurationMigrator.Migrate(Build(path));
        Assert.NotEmpty(first.ResetKeys);
        Assert.NotNull(first.BackupPath);

        var second = ConfigurationMigrator.Migrate(Build(path));
        Assert.False(second.Migrated);
        Assert.Empty(second.ResetKeys);
    }

    /// <summary>
    /// Short values that are real settings, including the canonical empty string
    /// and the legacy bare (unquoted) forms the reader still accepts.
    /// </summary>
    [Theory]
    [InlineData("telemetry_file_dir", "\"C:\\\\telemetry\"")]
    [InlineData("telemetry_file_dir", "C:\\telemetry")]
    [InlineData("telemetry_file_dir", "\"\"")]
    [InlineData("telemetry_server_url", "\"https://t.local/api/v2\"")]
    [InlineData("telemetry_server_url", "https://t.local/api/v2")]
    [InlineData("telemetry_server_url", "\"\"")]
    [InlineData("apptelemetry_server_url", "\"http://10.0.0.4:8000/\"")]
    public void Migration_PreservesLegitimateTelemetryValues(string key, string stored)
    {
        string path = WriteTemp($"[telemetry]\n{key} = {stored}\n");
        var result = ConfigurationMigrator.Migrate(Build(path));

        Assert.Empty(result.ResetKeys);
        Assert.Equal(stored, IniConfiguration.Create(path).GetRawValueOrDefault("telemetry", key));
    }

    [Fact]
    public void Migration_ResetsOverlongTelemetryField()
    {
        string path = WriteTemp("[telemetry]\ntelemetry_file_dir = \"" + new string('a', 9000) + "\"\n");
        var result = ConfigurationMigrator.Migrate(Build(path));

        Assert.Contains("telemetry.telemetry_file_dir", result.ResetKeys);
    }
}
