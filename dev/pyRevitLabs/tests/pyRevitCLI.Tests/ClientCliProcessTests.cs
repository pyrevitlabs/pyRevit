using System.Diagnostics;

namespace pyRevitCLI.Tests;

[Trait("Environment", "HostFree")]
[Trait("Level", "Integration")]
public sealed class ClientCliProcessTests : IDisposable {
    private readonly TimeSpan savedTimeout = PyRevitCLIAgentCmds.ClientCliTimeout;

    public void Dispose() {
        PyRevitCLIAgentCmds.ClientCliTimeout = savedTimeout;
    }

    [Fact]
    public void AHelperThatKeepsTheOutputOpenDoesNotOutlastTheDeadline() {
        PyRevitCLIAgentCmds.ClientCliTimeout = TimeSpan.FromSeconds(3);
        var watch = Stopwatch.StartNew();

        PyRevitCLIAgentCmds.RunClientCliProcess(
            "cmd", "/d /c start \"\" /b ping -n 20 127.0.0.1 & exit 0", ignoreFailure: false);

        Assert.True(watch.Elapsed < TimeSpan.FromSeconds(10), $"The call took {watch.Elapsed}.");
    }
}
