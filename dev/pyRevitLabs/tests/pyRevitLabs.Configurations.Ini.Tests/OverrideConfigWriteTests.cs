using System;
using System.IO;
using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Ini.Extensions;
using pyRevitLabs.Configurations.Sections;

namespace pyRevitLabs.Configurations.Ini.Tests;

/// <summary>
/// Covers writes aimed at a named override configuration (the per-Revit-version
/// file layered over the default one), where the same key is also present in the
/// default config.
/// </summary>
public class OverrideConfigWriteTests : IDisposable
{
    private const string OverrideName = "2025";

    private readonly string _defaultPath;
    private readonly string _overridePath;

    public OverrideConfigWriteTests()
    {
        _defaultPath = Path.Combine(Path.GetTempPath(), $"override_{Guid.NewGuid():N}.ini");
        _overridePath = Path.ChangeExtension(_defaultPath, OverrideName + IniConfiguration.DefaultFileExtension);
    }

    public void Dispose()
    {
        File.Delete(_defaultPath);
        File.Delete(_overridePath);
    }

    private IConfigurationService Build() =>
        new ConfigurationBuilder(false)
            .AddIniConfiguration(_defaultPath, ConfigurationService.DefaultConfigurationName)
            .AddIniConfiguration(_overridePath, OverrideName)
            .Build();

    [Fact]
    public void SaveSection_ToOverride_WritesValueAlreadyHeldByDefaultConfig()
    {
        File.WriteAllText(_defaultPath, "[core]\ncheckupdates = false\n");
        File.WriteAllText(_overridePath, "[core]\ncheckupdates = true\n");

        Build().SaveSection(OverrideName, new CoreSection {CheckUpdates = false});

        // The override, not the default, is the file that must change; the layered
        // read then resolves to the newly written value.
        Assert.False(IniConfiguration.Create(_overridePath).GetValue<bool>("core", "checkupdates"));
        Assert.False(Build().Core.CheckUpdates);
    }

    [Fact]
    public void SaveSection_ToOverride_MaterializesKeyNotStoredThere()
    {
        // rocketmode is declared default-true, so writing false is a real change
        // rather than a default the write path deliberately declines to persist.
        File.WriteAllText(_defaultPath, "[core]\nrocketmode = true\n");
        File.WriteAllText(_overridePath, "[core]\n");

        Build().SaveSection(OverrideName, new CoreSection {RocketMode = false});

        Assert.False(IniConfiguration.Create(_overridePath).GetValue<bool>("core", "rocketmode"));
        Assert.True(IniConfiguration.Create(_defaultPath).GetValue<bool>("core", "rocketmode"));
    }
}
