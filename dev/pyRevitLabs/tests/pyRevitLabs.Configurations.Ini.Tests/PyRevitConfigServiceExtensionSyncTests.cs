using System;
using System.Collections.Generic;
using System.IO;
using pyRevitLabs.Configurations.Ini;

namespace pyRevitLabs.Configurations.Ini.Tests;

/// <summary>
/// Covers the one-way sync of extension search paths from the machine config
/// into a standard user's per-user config on an all-users install (#3908).
/// Operates on explicit temp files, so it needs no install-scope state.
/// </summary>
[Trait("Environment", "HostFree")]
[Trait("Level", "Integration")]
public class PyRevitConfigServiceExtensionSyncTests {
    private const string MachineExt = @"C:\Shared\MachineExt";
    private const string OtherMachineExt = @"C:\Shared\OtherExt";
    private const string UserExt = @"C:\Users\me\UserExt";

    private static string NewTempDir() {
        var dir = Path.Combine(Path.GetTempPath(), "cfgextsync_" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(dir);
        return dir;
    }

    private static string Encode(params string[] paths) =>
        "[" + string.Join(",", Array.ConvertAll(paths, p => "\"" + p.Replace("\\", "\\\\") + "\"")) + "]";

    private static List<string> Read(string configPath, string key) =>
        IniConfiguration.Create(configPath).GetValueOrDefault<List<string>>("core", key)
        ?? new List<string>();

    private static List<string> UserExtensions(string configPath) => Read(configPath, "userextensions");

    private static List<string> Synced(string configPath) =>
        Read(configPath, PyRevitConfigService.SyncedMachineExtensionsKeyName);

    private static void Sync(string userConfigPath, string machineConfigPath) =>
        PyRevitConfigService.SyncMachineExtensionPaths(IniConfiguration.Create(userConfigPath), machineConfigPath);

    private static void Run(Action<string, string> test) {
        var dir = NewTempDir();
        try {
            test(Path.Combine(dir, "user.ini"), Path.Combine(dir, "machine.ini"));
        }
        finally {
            Directory.Delete(dir, recursive: true);
        }
    }

    [Fact]
    public void Sync_AddsMachinePathsToAConfigThatPredatesTheSyncKey() => Run((user, machine) => {
        File.WriteAllText(machine, "[core]\r\nuserextensions = " + Encode(MachineExt) + "\r\n");
        File.WriteAllText(user, "[core]\r\nuserextensions = " + Encode(UserExt) + "\r\n");

        Sync(user, machine);

        Assert.Equal(new List<string> { UserExt, MachineExt }, UserExtensions(user));
        Assert.Equal(new List<string> { MachineExt }, Synced(user));
    });

    /// <summary>
    /// The reported bug: a user removes the admin's path in Settings, and it must
    /// stay removed on the next load.
    /// </summary>
    [Fact]
    public void Sync_DoesNotRestoreAMachinePathTheUserRemoved() => Run((user, machine) => {
        File.WriteAllText(machine, "[core]\r\nuserextensions = " + Encode(MachineExt) + "\r\n");
        File.WriteAllText(user, "[core]\r\nuserextensions = " + Encode(MachineExt) + "\r\n");

        Sync(user, machine);
        var config = IniConfiguration.Create(user);
        config.SetValue("core", "userextensions", new List<string>());
        config.SaveConfiguration();

        Sync(user, machine);

        Assert.Empty(UserExtensions(user));
    });

    [Fact]
    public void Sync_OffersOnlyPathsTheAdminAddedSinceTheLastSync() => Run((user, machine) => {
        File.WriteAllText(machine, "[core]\r\nuserextensions = " + Encode(MachineExt, OtherMachineExt) + "\r\n");
        File.WriteAllText(user,
            "[core]\r\nuserextensions = " + Encode(UserExt) + "\r\n"
            + PyRevitConfigService.SyncedMachineExtensionsKeyName + " = " + Encode(MachineExt) + "\r\n");

        Sync(user, machine);

        Assert.Equal(new List<string> { UserExt, OtherMachineExt }, UserExtensions(user));
        Assert.Equal(new List<string> { MachineExt, OtherMachineExt }, Synced(user));
    });

    [Fact]
    public void Sync_DoesNotDuplicateAPathTheUserAlreadyHasInAnotherCase() => Run((user, machine) => {
        File.WriteAllText(machine, "[core]\r\nuserextensions = " + Encode(MachineExt) + "\r\n");
        File.WriteAllText(user, "[core]\r\nuserextensions = " + Encode(MachineExt.ToUpperInvariant() + "\\") + "\r\n");

        Sync(user, machine);

        Assert.Single(UserExtensions(user));
    });

    [Fact]
    public void Sync_LeavesAPathTheAdminDroppedInTheUserConfig() => Run((user, machine) => {
        File.WriteAllText(machine, "[core]\r\n");
        File.WriteAllText(user,
            "[core]\r\nuserextensions = " + Encode(MachineExt) + "\r\n"
            + PyRevitConfigService.SyncedMachineExtensionsKeyName + " = " + Encode(MachineExt) + "\r\n");

        Sync(user, machine);

        Assert.Equal(new List<string> { MachineExt }, UserExtensions(user));
        Assert.Equal(new List<string> { MachineExt }, Synced(user));
    });

    /// <summary>
    /// User removes the path, the admin drops it, then restores it: the user's
    /// removal must still hold.
    /// </summary>
    [Fact]
    public void Sync_DoesNotRestoreARemovedPathAfterTheAdminDropsAndReAddsIt() => Run((user, machine) => {
        File.WriteAllText(machine, "[core]\r\nuserextensions = " + Encode(MachineExt) + "\r\n");
        File.WriteAllText(user, "[core]\r\n");
        Sync(user, machine);

        var config = IniConfiguration.Create(user);
        config.SetValue("core", "userextensions", new List<string>());
        config.SaveConfiguration();

        File.WriteAllText(machine, "[core]\r\nuserextensions = []\r\n");
        Sync(user, machine);
        File.WriteAllText(machine, "[core]\r\nuserextensions = " + Encode(MachineExt) + "\r\n");
        Sync(user, machine);

        Assert.Empty(UserExtensions(user));
    });

    [Fact]
    public void Sync_KeepsTheNewPathsInMemoryWhenTheSaveFails() => Run((user, machine) => {
        if (!OperatingSystem.IsWindows())
            return;

        File.WriteAllText(machine, "[core]\r\nuserextensions = " + Encode(MachineExt) + "\r\n");
        File.WriteAllText(user, "[core]\r\nuserextensions = " + Encode(UserExt) + "\r\n");
        var config = IniConfiguration.Create(user);

        using (File.Open(user, FileMode.Open, FileAccess.Read, FileShare.Read))
            PyRevitConfigService.SyncMachineExtensionPaths(config, machine);

        Assert.Equal(
            new List<string> { UserExt, MachineExt },
            config.GetValue<List<string>>("core", "userextensions"));
        Assert.Equal(new List<string> { UserExt }, UserExtensions(user));
    });

    [Fact]
    public void Sync_DoesNotTouchTheUserConfigWhenNothingChanged() => Run((user, machine) => {
        File.WriteAllText(machine, "[core]\r\n");
        const string original = "[core]\r\nuserextensions = []\r\n";
        File.WriteAllText(user, original);

        Sync(user, machine);

        Assert.Equal(original, File.ReadAllText(user));
    });

    [Fact]
    public void Sync_IsANoOpWhenTheMachineConfigIsMissing() => Run((user, machine) => {
        const string original = "[core]\r\nuserextensions = []\r\n";
        File.WriteAllText(user, original);

        Sync(user, machine);

        Assert.Equal(original, File.ReadAllText(user));
        Assert.False(File.Exists(machine));
    });
}
