using pyRevitLabs.Common;
using pyRevitLabs.PyRevit;

namespace pyRevitCLI.Tests;

[Trait("Environment", "HostFree")]
[Trait("Level", "Unit")]
public class AgentLockCmdsTests {
    [Fact]
    public void LockingASettingWithoutAValueIsRejectedBeforeAnythingIsWritten() {
        var error = Assert.Throws<PyRevitException>(
            () => PyRevitCLIAgentCmds.ConfigureLock(PyRevitConsts.ConfigsAgentEnabledKey, null));

        Assert.Contains("value", error.Message);
    }

    [Fact]
    public void ManagedSettingExceptionNamesTheSettingAndTheAdministrator() {
        var error = new PyRevitSettingManagedException(PyRevitConsts.ConfigsAgentPolicyKey);

        Assert.Equal(PyRevitConsts.ConfigsAgentPolicyKey, error.SettingName);
        Assert.Contains("administrator", error.Message);
    }
}
