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
    /// <summary>
    /// Exercises every rung of the selection ladder documented in userconfig.py.
    /// </summary>
    /// <remarks>
    /// Local always wins regardless of every other signal. An admin-locked machine
    /// config binds every scope and process. For an elevated all-users install,
    /// %ProgramData% is the authoritative writable target whether or not it exists
    /// yet or the user already has a config of their own. For a standard user on an
    /// all-users install, %ProgramData% is never targeted: a per-user copy is seeded
    /// from the machine config once, then reused. For a per-user install, an unlocked
    /// admin config seeds the per-user copy once; absent that, an existing user
    /// config is reused, and a fresh install falls back to a new per-user config.
    /// </remarks>
    [Theory]
    [InlineData(true, false, false, false, false, false, PyRevitConfigService.ConfigSelection.Local)]
    [InlineData(true, true, true, true, true, true, PyRevitConfigService.ConfigSelection.Local)]
    [InlineData(false, true, true, true, true, true, PyRevitConfigService.ConfigSelection.AdminLockdown)]
    [InlineData(false, true, false, true, true, true, PyRevitConfigService.ConfigSelection.AdminLockdown)]
    [InlineData(false, false, false, true, true, true, PyRevitConfigService.ConfigSelection.AdminLockdown)]
    [InlineData(false, false, false, true, true, false, PyRevitConfigService.ConfigSelection.AdminLockdown)]
    [InlineData(false, true, true, true, false, false, PyRevitConfigService.ConfigSelection.AdminInstall)]
    [InlineData(false, true, true, true, false, true, PyRevitConfigService.ConfigSelection.AdminInstall)]
    [InlineData(false, true, true, false, false, true, PyRevitConfigService.ConfigSelection.AdminInstall)]
    [InlineData(false, true, false, true, false, false, PyRevitConfigService.ConfigSelection.Seed)]
    [InlineData(false, true, false, true, false, true, PyRevitConfigService.ConfigSelection.User)]
    [InlineData(false, true, false, false, false, true, PyRevitConfigService.ConfigSelection.User)]
    [InlineData(false, true, false, false, false, false, PyRevitConfigService.ConfigSelection.New)]
    [InlineData(false, false, false, true, false, false, PyRevitConfigService.ConfigSelection.Seed)]
    [InlineData(false, false, false, true, false, true, PyRevitConfigService.ConfigSelection.User)]
    [InlineData(false, false, false, false, false, true, PyRevitConfigService.ConfigSelection.User)]
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
