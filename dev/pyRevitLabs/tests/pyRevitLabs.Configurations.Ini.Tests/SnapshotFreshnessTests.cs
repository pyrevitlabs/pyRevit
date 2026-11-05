using System;
using System.Collections.Generic;
using System.IO;
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
        catch { }
    }

    private IConfigurationService Service(string content)
    {
        File.WriteAllText(_path, content);
        return new ConfigurationBuilder(false)
            .AddIniConfiguration(_path)
            .Build();
    }

    /// <summary>
    /// Reproduces the Extensions dialog: set_option writes raw, then save_changes
    /// hands the typed snapshot to SaveSection. The typed snapshot is read below
    /// before the raw write, so this proves the later write is not reverted rather
    /// than never having been overwritten in the first place.
    /// </summary>
    [Fact]
    public void RawWriteThenSaveSection_DoesNotRevertTheWrite()
    {
        var service = Service("[core]\nuserextensions = " + @"[""C:\\A""]" + "\n");
        var cfg = service.Configuration;

        Assert.Equal(new List<string> { @"C:\A" }, service.Core.UserExtensions);

        cfg.SetRawValue("core", "userextensions", @"[""C:\\A"",""C:\\B""]");

        service.SaveSection(service.Core);
        cfg.SaveConfiguration();

        var reread = IniConfiguration.Create(_path);
        Assert.Equal(
            new List<string> { @"C:\A", @"C:\B" },
            reread.GetValue<List<string>>("core", "userextensions"));
    }

    /// <summary>
    /// Reproduces the Settings dialog Save: typed edits are written through with
    /// ApplySection (no flush), then an unrelated dynamic-section write (e.g.
    /// tabcoloring) bumps the store's revision and rebuilds the typed snapshots
    /// mid-save — the read of <c>service.Core.RocketMode</c> below forces that
    /// rebuild, as the dialog does when it reads a typed value afterward. A single
    /// flush at the end must still persist every typed edit, across all three typed
    /// sections. Values are chosen to contradict the section defaults so a silent
    /// revert to the default is detectable.
    /// </summary>
    [Fact]
    public void ApplySectionAcrossSections_SurvivesInterveningDynamicWrite_OnSingleFlush()
    {
        var service = Service("[core]\nrocketmode = true\n");
        var cfg = service.Configuration;

        service.ApplySection(
            new CoreSection { RocketMode = false });
        service.ApplySection(
            new RoutesSection { Port = 1234 });
        service.ApplySection(
            new TelemetrySection { TelemetryServerUrl = "http://example/" });

        cfg.SetRawValue("tabcoloring", "sort_colorize_docs", "true");
        _ = service.Core.RocketMode;

        cfg.SaveConfiguration();

        var reread = IniConfiguration.Create(_path);
        Assert.False(reread.GetValue<bool>("core", "rocketmode"));
        Assert.Equal(1234, reread.GetValue<int>("routes", "port"));
        Assert.Equal("http://example/", reread.GetValue<string>("telemetry", "telemetry_server_url"));
    }

    [Fact]
    public void RawWrite_IsVisibleOnTypedSection_WithoutExplicitReload()
    {
        var service = Service("[core]\nrocketmode = true\n");
        Assert.True(service.Core.RocketMode);

        service.Configuration
            .SetRawValue("core", "rocketmode", "false");

        Assert.False(service.Core.RocketMode);
    }

    /// <summary>
    /// 10 is CoreSection.StartupLogTimeout's declared [DefaultValue].
    /// </summary>
    [Fact]
    public void RemovingAnOption_IsVisibleOnTypedSection()
    {
        var service = Service("[core]\nstartuplogtimeout = 99\n");
        Assert.Equal(99, service.Core.StartupLogTimeout);

        service.Configuration.RemoveOption("core", "startuplogtimeout");

        Assert.Equal(10, service.Core.StartupLogTimeout);
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
        var cfg = service.Configuration;

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

    /// <summary>
    /// A no-op removal changed nothing, so derived state stays valid.
    /// </summary>
    [Fact]
    public void Revision_DoesNotAdvanceOnNoOpMutation()
    {
        var service = Service("[core]\nrocketmode = true\n");
        var cfg = service.Configuration;

        long start = cfg.Revision;

        Assert.False(cfg.RemoveOption("core", "absent"));
        Assert.False(cfg.RemoveSection("absent"));

        Assert.Equal(start, cfg.Revision);
    }
}
