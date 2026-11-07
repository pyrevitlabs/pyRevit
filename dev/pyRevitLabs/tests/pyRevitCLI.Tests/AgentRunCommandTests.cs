using pyRevitLabs.Common;

namespace pyRevitCLI.Tests;

[Trait("Environment", "HostFree")]
[Trait("Level", "Unit")]
public sealed class AgentRunCommandTests : IDisposable {
    private readonly string script = Path.GetTempFileName();

    public void Dispose() {
        File.Delete(script);
    }

    [Theory]
    [InlineData("NaN")]
    [InlineData("Infinity")]
    [InlineData("-Infinity")]
    [InlineData("-5")]
    [InlineData("0")]
    [InlineData("soon")]
    public void TimeoutsThatAreNotAPositiveNumberAreRefusedBeforeConnecting(string timeout) {
        var refused = Assert.Throws<PyRevitException>(
            () => PyRevitCLIAgentCmds.RunScript(script, "query", null, null, null, "no-such-revit", timeout));

        Assert.Contains("--timeout", refused.Message);
    }
}
