using System;
using System.IO;
using pyRevitLabs.Configurations.Ini;

namespace pyRevitLabs.Configurations.Ini.Tests;

/// <summary>
/// Covers the config-file discovery primitive that the loader and CLI share via
/// PyRevitConfigService, so both resolve the same file. Uses a temp directory to
/// avoid touching the real %APPDATA%/%ProgramData% locations.
/// </summary>
public class PyRevitConfigPathsTests
{
    private static string NewTempDir()
    {
        var dir = Path.Combine(Path.GetTempPath(), "paths_" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(dir);
        return dir;
    }

    [Fact]
    public void FindConfigFileInDirectory_ReturnsDefaultNamedFile()
    {
        var dir = NewTempDir();
        try
        {
            var expected = Path.Combine(dir, "pyRevit_config.ini");
            File.WriteAllText(expected, "[core]\n");

            Assert.Equal(expected, PyRevitConfigPaths.FindConfigFileInDirectory(dir));
        }
        finally
        {
            Directory.Delete(dir, true);
        }
    }

    [Theory]
    [InlineData("pyRevit_config.ini")]
    [InlineData("config.ini")]
    [InlineData("pyrevit.ini")]
    public void FindConfigFileInDirectory_MatchesConfigNamePattern(string fileName)
    {
        var dir = NewTempDir();
        try
        {
            var path = Path.Combine(dir, fileName);
            File.WriteAllText(path, "[core]\n");

            Assert.Equal(path, PyRevitConfigPaths.FindConfigFileInDirectory(dir));
        }
        finally
        {
            Directory.Delete(dir, true);
        }
    }

    [Fact]
    public void FindConfigFileInDirectory_IgnoresUnrelatedFiles()
    {
        var dir = NewTempDir();
        try
        {
            File.WriteAllText(Path.Combine(dir, "notes.txt"), "x");
            File.WriteAllText(Path.Combine(dir, "data.json"), "{}");

            Assert.Null(PyRevitConfigPaths.FindConfigFileInDirectory(dir));
        }
        finally
        {
            Directory.Delete(dir, true);
        }
    }

    [Fact]
    public void FindConfigFileInDirectory_MissingDirectory_ReturnsNull()
    {
        Assert.Null(PyRevitConfigPaths.FindConfigFileInDirectory(
            Path.Combine(Path.GetTempPath(), "does_not_exist_" + Guid.NewGuid().ToString("N"))));
    }

    [Fact]
    public void Roots_AreUnderTheExpectedSpecialFolders()
    {
        Assert.Equal(
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "pyRevit"),
            PyRevitConfigPaths.PyRevitAppDataPath);
        Assert.Equal(
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData), "pyRevit"),
            PyRevitConfigPaths.PyRevitProgramDataPath);
    }
}
