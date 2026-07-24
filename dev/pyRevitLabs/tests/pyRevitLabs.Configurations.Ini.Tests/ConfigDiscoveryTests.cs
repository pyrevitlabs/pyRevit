using System;
using System.IO;
using pyRevitLabs.Common;

namespace pyRevitLabs.Configurations.Ini.Tests;

/// <summary>
/// Pins which file in a directory is treated as the main config. Version-suffixed
/// configs sort ahead of the canonical name in directory enumeration, so discovery
/// must not resolve by enumeration order alone.
/// </summary>
public class ConfigDiscoveryTests : IDisposable
{
    private readonly string _dir;

    public ConfigDiscoveryTests()
    {
        _dir = Path.Combine(Path.GetTempPath(), $"cfgdisc_{Guid.NewGuid():N}");
        Directory.CreateDirectory(_dir);
    }

    public void Dispose()
    {
        try { Directory.Delete(_dir, true); }
        catch { /* best effort */ }
    }

    private string Write(string name)
    {
        var path = Path.Combine(_dir, name);
        File.WriteAllText(path, "[core]\n");
        return path;
    }

    [Fact]
    public void CanonicalConfig_WinsOverVersionSuffixedConfig()
    {
        Write("pyRevit_config.2025.ini");
        var expected = Write(PyRevitLabsConsts.DefaultConfigsFileName);
        Write("pyRevit_config.2026.ini");

        Assert.Equal(expected, PyRevitConfigPaths.FindConfigFileInDirectory(_dir));
    }

    [Fact] // A version config alone is not the main config; its own lookup owns it.
    public void VersionSuffixedConfig_IsNotDiscoveredAsMainConfig()
    {
        Write("pyRevit_config.2025.ini");

        Assert.Null(PyRevitConfigPaths.FindConfigFileInDirectory(_dir));
    }

    [Fact] // The name match still covers configs that carry a custom name.
    public void CustomNamedConfig_IsStillDiscovered()
    {
        var expected = Write("pyrevit_admin_config.ini");

        Assert.Equal(expected, PyRevitConfigPaths.FindConfigFileInDirectory(_dir));
    }

    [Theory] // Non-canonical names still matching the config pattern are discovered.
    [InlineData("config.ini")]
    [InlineData("pyrevit.ini")]
    public void ConfigNamePattern_MatchesNonCanonicalNames(string fileName)
    {
        var expected = Write(fileName);

        Assert.Equal(expected, PyRevitConfigPaths.FindConfigFileInDirectory(_dir));
    }

    [Fact]
    public void CustomNamedConfig_LosesToCanonicalConfig()
    {
        Write("pyrevit_admin_config.ini");
        var expected = Write(PyRevitLabsConsts.DefaultConfigsFileName);

        Assert.Equal(expected, PyRevitConfigPaths.FindConfigFileInDirectory(_dir));
    }

    [Fact]
    public void EmptyDirectory_ResolvesToNull()
    {
        Assert.Null(PyRevitConfigPaths.FindConfigFileInDirectory(_dir));
    }

    [Fact]
    public void MissingDirectory_ResolvesToNull()
    {
        Assert.Null(PyRevitConfigPaths.FindConfigFileInDirectory(
            Path.Combine(_dir, "does-not-exist")));
    }

    [Fact] // Unrelated .ini files must never be mistaken for a config.
    public void UnrelatedIni_IsNotDiscovered()
    {
        Write("desktop.ini");

        Assert.Null(PyRevitConfigPaths.FindConfigFileInDirectory(_dir));
    }
}
