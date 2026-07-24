using System;
using System.Collections.Generic;
using System.IO;
using pyRevitLabs.Configurations;
using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Ini.Extensions;
using pyRevitLabs.Configurations.Sections;

namespace pyRevitLabs.Configurations.Ini.Tests;

/// <summary>
/// The typed section snapshots are derived state. A write straight to the
/// configuration (what the Python compat wrapper does via SetRawValue) must not
/// leave a reader holding values older than that write, or the next save writes
/// the stale copy back over it.
/// </summary>
public class SnapshotFreshnessTests : IDisposable
{
    private readonly string _path;

    public SnapshotFreshnessTests()
    {
        _path = Path.Combine(Path.GetTempPath(), $"snapfresh_{Guid.NewGuid():N}.ini");
    }

    public void Dispose()
    {
        try { File.Delete(_path); }
        catch { /* best effort */ }
    }

    private IConfigurationService Service(string content)
    {
        File.WriteAllText(_path, content);
        return new ConfigurationBuilder(false)
            .AddIniConfiguration(_path, ConfigurationService.DefaultConfigurationName)
            .Build();
    }

    // Reproduces the Extensions dialog: set_option writes raw, then save_changes
    // hands the typed snapshot to SaveSection.
    [Fact]
    public void RawWriteThenSaveSection_DoesNotRevertTheWrite()
    {
        var service = Service("[core]\nuserextensions = " + @"[""C:\\A""]" + "\n");
        var cfg = service[ConfigurationService.DefaultConfigurationName];

        // snapshot is built here, before the raw write
        Assert.Equal(new List<string> { @"C:\A" }, service.Core.UserExtensions);

        cfg.SetRawValue("core", "userextensions", @"[""C:\\A"",""C:\\B""]");

        service.SaveSection(ConfigurationService.DefaultConfigurationName, service.Core);
        cfg.SaveConfiguration();

        var reread = IniConfiguration.Create(_path);
        Assert.Equal(
            new List<string> { @"C:\A", @"C:\B" },
            reread.GetValue<List<string>>("core", "userextensions"));
    }

    [Fact]
    public void RawWrite_IsVisibleOnTypedSection_WithoutExplicitReload()
    {
        var service = Service("[core]\nrocketmode = true\n");
        Assert.True(service.Core.RocketMode);

        service[ConfigurationService.DefaultConfigurationName]
            .SetRawValue("core", "rocketmode", "false");

        Assert.False(service.Core.RocketMode);
    }

    [Fact]
    public void RemovingAnOption_IsVisibleOnTypedSection()
    {
        var service = Service("[core]\nstartuplogtimeout = 99\n");
        Assert.Equal(99, service.Core.StartupLogTimeout);

        service[ConfigurationService.DefaultConfigurationName].RemoveOption("core", "startuplogtimeout");

        Assert.Equal(10, service.Core.StartupLogTimeout); // [DefaultValue(10)]
    }

    [Fact]
    public void UnchangedStore_ReturnsTheSameSnapshotInstance()
    {
        var service = Service("[core]\nrocketmode = true\n");

        Assert.Same(service.Core, service.Core);
    }

    [Fact]
    public void Revision_AdvancesOnEachMutationKind()
    {
        var service = Service("[core]\nrocketmode = true\n");
        var cfg = service[ConfigurationService.DefaultConfigurationName];

        long start = cfg.Revision;

        cfg.SetValue("core", "startuplogtimeout", 42);
        long afterSet = cfg.Revision;
        Assert.True(afterSet > start);

        cfg.SetRawValue("core", "user_locale", "\"en_us\"");
        long afterRaw = cfg.Revision;
        Assert.True(afterRaw > afterSet);

        cfg.AddSection("MyTool.extension");
        long afterAdd = cfg.Revision;
        Assert.True(afterAdd > afterRaw);

        cfg.RemoveOption("core", "startuplogtimeout");
        long afterRemoveOption = cfg.Revision;
        Assert.True(afterRemoveOption > afterAdd);

        cfg.RemoveSection("MyTool.extension");
        Assert.True(cfg.Revision > afterRemoveOption);
    }

    [Fact] // A no-op removal changed nothing, so derived state stays valid.
    public void Revision_DoesNotAdvanceOnNoOpMutation()
    {
        var service = Service("[core]\nrocketmode = true\n");
        var cfg = service[ConfigurationService.DefaultConfigurationName];

        long start = cfg.Revision;

        Assert.False(cfg.RemoveOption("core", "absent"));
        Assert.False(cfg.RemoveSection("absent"));

        Assert.Equal(start, cfg.Revision);
    }
}
