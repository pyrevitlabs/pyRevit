using pyRevitLabs.Configurations;
using pyRevitLabs.Configurations.Ini.Extensions;
using pyRevitLabs.PyRevit;

namespace pyRevitCLI.Tests;

/// <summary>
/// A fresh clone stores <c>disabled</c> for shipped extensions whose manifest sets
/// <c>default_enabled=false</c>, without overwriting a choice the user already made.
/// </summary>
[Collection(CliGlobalState.Name)]
[Trait("Environment", "HostFree")]
[Trait("Level", "Integration")]
public sealed class ShippedExtensionDefaultsTests : IDisposable {
    private readonly string root = Directory.CreateTempSubdirectory("pyrevit-seed-").FullName;
    private readonly string configPath;

    public ShippedExtensionDefaultsTests() {
        configPath = Path.Combine(root, "pyRevit_config.ini");
        File.WriteAllText(configPath, "[core]\n[Kept.extension]\ndisabled = false\n");
        PyRevitConfigStore.Reset();
        PyRevitConfigStore.SetFactory(() => new ConfigurationBuilder(false).AddIniConfiguration(configPath).Build());
    }

    public void Dispose() {
        PyRevitConfigStore.Reset();
        Directory.Delete(root, recursive: true);
    }

    private void Shipped(string name, string type, bool? defaultEnabled) {
        var directory = Directory.CreateDirectory(
            Path.Combine(root, PyRevitConsts.ExtensionsDirName, name + "." + type)).FullName;
        var enabled = defaultEnabled.HasValue
            ? ", \"default_enabled\": \"" + (defaultEnabled.Value ? "true" : "false") + "\""
            : string.Empty;
        File.WriteAllText(
            Path.Combine(directory, PyRevitConsts.ExtensionDefFileName),
            "{\"name\": \"" + name + "\", \"type\": \"" + type + "\"" + enabled + "}");
    }

    private bool? Disabled(string section) =>
        PyRevitConfigs.GetConfigFile().GetSectionKeyValueOrDefault<bool?>(section, PyRevitConsts.ExtensionDisabledKey);

    [Fact]
    public void OnlyDisabledByDefaultExtensionsWithoutAStoredChoiceAreSeeded() {
        Shipped("Optional", "extension", defaultEnabled: false);
        Shipped("OptionalLib", "lib", defaultEnabled: false);
        Shipped("Kept", "extension", defaultEnabled: false);
        Shipped("Default", "extension", defaultEnabled: null);

        PyRevitConfigs.SeedShippedExtensionDefaults(root);

        Assert.True(Disabled("Optional.extension"));
        Assert.True(Disabled("OptionalLib.lib"));
        Assert.False(Disabled("Kept.extension"));
        Assert.Null(Disabled("Default.extension"));
    }

    [Fact]
    public void AMissingExtensionsFolderSeedsNothing() {
        PyRevitConfigs.SeedShippedExtensionDefaults(Path.Combine(root, "no-clone"));

        Assert.Null(Disabled("Optional.extension"));
    }
}
