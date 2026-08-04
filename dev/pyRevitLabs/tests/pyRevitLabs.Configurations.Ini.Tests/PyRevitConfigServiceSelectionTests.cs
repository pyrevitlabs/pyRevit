using pyRevitLabs.Configurations.Ini;

namespace pyRevitLabs.Configurations.Ini.Tests;

/// <summary>
/// Verifies the pure config-tier selection ladder (Local, admin lock, elevated
/// all-users install, seed, user, new) that <see cref="PyRevitConfigService"/>
/// uses, without touching real machine directories or install-scope detection.
/// Order mirrors the documented Python precedence in userconfig.py.
/// </summary>
public class PyRevitConfigServiceSelectionTests
{
    [Theory]
    // Local override wins regardless of every other signal.
    [InlineData(true, false, false, false, false, false, PyRevitConfigService.ConfigSelection.Local)]
    [InlineData(true, true, true, true, true, true, PyRevitConfigService.ConfigSelection.Local)]
    // An admin-locked machine config binds every scope and every process.
    [InlineData(false, true, true, true, true, true, PyRevitConfigService.ConfigSelection.AdminLockdown)]
    [InlineData(false, true, false, true, true, true, PyRevitConfigService.ConfigSelection.AdminLockdown)]
    [InlineData(false, false, false, true, true, true, PyRevitConfigService.ConfigSelection.AdminLockdown)]
    [InlineData(false, false, false, true, true, false, PyRevitConfigService.ConfigSelection.AdminLockdown)]
    // All-users install, elevated: %ProgramData% is the authoritative writable target,
    // whether or not it exists yet and whether or not this user has a config of their own.
    [InlineData(false, true, true, true, false, false, PyRevitConfigService.ConfigSelection.AdminInstall)]
    [InlineData(false, true, true, true, false, true, PyRevitConfigService.ConfigSelection.AdminInstall)]
    [InlineData(false, true, true, false, false, true, PyRevitConfigService.ConfigSelection.AdminInstall)]
    // All-users install, standard user: never %ProgramData%. Seed a per-user copy from
    // the machine config, then keep using the per-user copy.
    [InlineData(false, true, false, true, false, false, PyRevitConfigService.ConfigSelection.Seed)]
    [InlineData(false, true, false, true, false, true, PyRevitConfigService.ConfigSelection.User)]
    [InlineData(false, true, false, false, false, true, PyRevitConfigService.ConfigSelection.User)]
    [InlineData(false, true, false, false, false, false, PyRevitConfigService.ConfigSelection.New)]
    // Per-user install: an unlocked admin config seeds the per-user copy once.
    [InlineData(false, false, false, true, false, false, PyRevitConfigService.ConfigSelection.Seed)]
    [InlineData(false, false, false, true, false, true, PyRevitConfigService.ConfigSelection.User)]
    // Per-user: no admin config, existing user config.
    [InlineData(false, false, false, false, false, true, PyRevitConfigService.ConfigSelection.User)]
    // Nothing anywhere -> a fresh per-user config.
    [InlineData(false, false, false, false, false, false, PyRevitConfigService.ConfigSelection.New)]
    public void SelectConfig_FollowsDocumentedLadder(
        bool localExists,
        bool isAllUsers,
        bool isElevated,
        bool adminExists,
        bool adminLocked,
        bool userExists,
        PyRevitConfigService.ConfigSelection expected)
    {
        Assert.Equal(
            expected,
            PyRevitConfigService.SelectConfig(
                localExists, isAllUsers, isElevated, adminExists, adminLocked, userExists));
    }

    /// <summary>
    /// An admin install seeds a machine config a standard user cannot write. That
    /// must resolve to a writable per-user copy, not a read-only config whose saves
    /// are silently discarded, so write access is not an input to the ladder at all.
    /// </summary>
    [Theory]
    [InlineData(false, PyRevitConfigService.ConfigSelection.Seed)]
    [InlineData(true, PyRevitConfigService.ConfigSelection.User)]
    public void SelectConfig_UnwritableMachineConfigIsNotALockdown(
        bool userExists, PyRevitConfigService.ConfigSelection expected)
    {
        Assert.Equal(
            expected,
            PyRevitConfigService.SelectConfig(
                localExists: false,
                isAllUsers: true,
                isElevated: false,
                adminExists: true,
                adminLocked: false,
                userExists: userExists));
    }
}
