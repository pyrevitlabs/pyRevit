using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Exceptions;
using pyRevitLabs.Configurations.Sections;

namespace pyRevitLabs.Configurations.Ini.Tests;

/// <summary>
/// Covers reading config files as they exist in the wild rather than as the
/// writer emits them. Every case here must load: a config that refuses to parse
/// takes down the loader, the CLI, and the script engines at once, and never
/// reaches the migrator that would repair it.
/// </summary>
public class MalformedConfigToleranceTests : IDisposable
{
    private readonly List<string> _files = new();

    public void Dispose()
    {
        foreach (string file in _files)
        {
            try
            {
                File.Delete(file);
            }
            catch (IOException)
            {
            }
        }
    }

    private IConfiguration Read(string content)
    {
        string path = Path.Combine(Path.GetTempPath(), $"malformed_{Guid.NewGuid():N}.ini");
        _files.Add(path);
        File.WriteAllText(path, content, new UTF8Encoding(false));
        return IniConfiguration.Create(path);
    }

    /// <summary>
    /// Python's configparser accepts '#', so hand-edited configs carry it.
    /// </summary>
    [Fact]
    public void HashComment_IsRead()
    {
        IConfiguration config = Read("# pyRevit settings\n[core]\ndebug = true\n");

        Assert.True(config.GetValue<bool>("core", "debug"));
    }

    [Fact]
    public void SemicolonComment_IsRead()
    {
        IConfiguration config = Read("; pyRevit settings\n[core]\ndebug = true\n");

        Assert.True(config.GetValue<bool>("core", "debug"));
    }

    [Fact]
    public void DuplicateKey_LastValueWins()
    {
        IConfiguration config = Read("[core]\ndebug = true\ndebug = false\n");

        Assert.False(config.GetValue<bool>("core", "debug"));
    }

    [Fact]
    public void DuplicateSection_IsMerged()
    {
        IConfiguration config = Read("[core]\ndebug = true\n[core]\nverbose = true\n");

        Assert.True(config.GetValue<bool>("core", "debug"));
        Assert.True(config.GetValue<bool>("core", "verbose"));
    }

    [Fact]
    public void UnparsableLine_IsSkipped_AndSurroundingKeysSurvive()
    {
        IConfiguration config = Read("[core]\nthis line has no assignment\ndebug = true\n");

        Assert.True(config.GetValue<bool>("core", "debug"));
    }
}

/// <summary>
/// A read-only (admin lockdown) config must refuse writes rather than accept
/// them into memory and drop them at flush time. The service-level entry points
/// enforce that by throwing; the configuration-level raw write does not, so
/// nothing it stores ever reaches the file and a caller that must not report a
/// false success tests <see cref="IConfigurationService.ReadOnly"/> itself.
/// </summary>
public class ReadOnlyWriteGuardTests : IDisposable
{
    private readonly string _path =
        Path.Combine(Path.GetTempPath(), $"readonly_{Guid.NewGuid():N}.ini");

    public ReadOnlyWriteGuardTests() =>
        File.WriteAllText(_path, "[core]\nrocketmode = true\n", new UTF8Encoding(false));

    public void Dispose()
    {
        try
        {
            File.Delete(_path);
        }
        catch (IOException)
        {
        }
    }

    private IConfigurationService ReadOnlyService() =>
        new ConfigurationBuilder(true)
            .AddConfigurationSource(IniConfiguration.Create(_path, true))
            .Build();

    [Fact]
    public void SaveSection_OnReadOnlyConfig_Throws()
    {
        Assert.Throws<ConfigurationReadOnlyException>(() => ReadOnlyService().SaveSection(new CoreSection { RocketMode = false }));
    }

    [Fact]
    public void SetSectionKeyValue_OnReadOnlyConfig_Throws()
    {
        Assert.Throws<ConfigurationReadOnlyException>(() => ReadOnlyService().SetSectionKeyValue(
            "core", "rocketmode", false));
    }

    /// <summary>
    /// The write-through path behind user_config.core.X = value in Python.
    /// </summary>
    [Fact]
    public void ApplySection_OnReadOnlyConfig_Throws()
    {
        Assert.Throws<ConfigurationReadOnlyException>(() => ReadOnlyService().ApplySection(new CoreSection { RocketMode = false }));
    }

    [Fact]
    public void RawWrite_OnReadOnlyConfig_NeverReachesFile()
    {
        IConfigurationService service = ReadOnlyService();
        IConfiguration configuration = service.Configuration;

        configuration.SetRawValue("core", "rocketmode", "false");
        configuration.SaveConfiguration();

        Assert.Contains("rocketmode = true", File.ReadAllText(_path));
    }

    [Fact]
    public void RefusedWrite_LeavesValueUnchanged()
    {
        IConfigurationService service = ReadOnlyService();

        Assert.Throws<ConfigurationReadOnlyException>(() => service.SetSectionKeyValue(
            "core", "rocketmode", false));

        Assert.True(service.Core.RocketMode);
        Assert.Contains("rocketmode = true", File.ReadAllText(_path));
    }
}
