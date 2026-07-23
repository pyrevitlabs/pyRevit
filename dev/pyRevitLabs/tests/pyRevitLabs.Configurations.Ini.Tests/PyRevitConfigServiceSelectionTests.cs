using pyRevitLabs.Configurations.Ini;

namespace pyRevitLabs.Configurations.Ini.Tests;

/// <summary>
/// Verifies the pure config-tier selection ladder (Local, all-users install,
/// admin seed/lockdown, user, new) that <see cref="PyRevitConfigService"/> uses,
/// without touching real machine directories or install-scope detection. Order
/// mirrors the documented Python precedence in userconfig.py.
/// </summary>
public class PyRevitConfigServiceSelectionTests
{
    [Theory]
    // Local override wins regardless of every other signal.
    [InlineData(true, false, false, false, false, PyRevitConfigService.ConfigSelection.Local)]
    [InlineData(true, true, true, true, true, PyRevitConfigService.ConfigSelection.Local)]
    // All-users install: a writable (or absent) admin config is the authoritative machine config.
    [InlineData(false, true, true, true, false, PyRevitConfigService.ConfigSelection.AdminInstall)]
    [InlineData(false, true, false, false, true, PyRevitConfigService.ConfigSelection.AdminInstall)]
    // All-users install: a read-only admin config is used as a locked policy.
    [InlineData(false, true, true, false, true, PyRevitConfigService.ConfigSelection.AdminLockdown)]
    // Per-user: a writable admin config with no user config yet seeds the per-user copy.
    [InlineData(false, false, true, true, false, PyRevitConfigService.ConfigSelection.Seed)]
    // Per-user: a writable admin config but the user already has one -> use the user config.
    [InlineData(false, false, true, true, true, PyRevitConfigService.ConfigSelection.User)]
    // Per-user: a read-only admin config is a locked policy whether or not a user config exists.
    [InlineData(false, false, true, false, true, PyRevitConfigService.ConfigSelection.AdminLockdown)]
    [InlineData(false, false, true, false, false, PyRevitConfigService.ConfigSelection.AdminLockdown)]
    // Per-user: no admin config, existing user config.
    [InlineData(false, false, false, false, true, PyRevitConfigService.ConfigSelection.User)]
    // Nothing anywhere -> a fresh per-user config.
    [InlineData(false, false, false, false, false, PyRevitConfigService.ConfigSelection.New)]
    public void SelectConfig_FollowsDocumentedLadder(
        bool localExists,
        bool isAllUsers,
        bool adminExists,
        bool adminWritable,
        bool userExists,
        PyRevitConfigService.ConfigSelection expected)
    {
        Assert.Equal(
            expected,
            PyRevitConfigService.SelectConfig(localExists, isAllUsers, adminExists, adminWritable, userExists));
    }
}
