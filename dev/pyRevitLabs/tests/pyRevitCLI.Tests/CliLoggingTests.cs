using pyRevitLabs.NLog;
using pyRevitLabs.NLog.Config;
using pyRevitLabs.NLog.Targets;

using pyRevitCLI;

namespace pyRevitCLI.Tests;

[Trait("Level", "Unit")]
[Trait("Environment", "HostFree")]
public class CliLoggingTests {
    private static ConsoleTarget[] ConsoleTargetsFor(LoggingConfiguration config, LogLevel level) {
        return config.LoggingRules
            .Where(rule => rule.IsLoggingEnabledForLevel(level))
            .SelectMany(rule => rule.Targets)
            .Cast<ConsoleTarget>()
            .ToArray();
    }

    [Theory]
    [InlineData(false, false)]
    [InlineData(true, true)]
    public void WarnErrorAndFatalLinesGoOnlyToStderr(bool verbose, bool debug) {
        var config = PyRevitCLILogging.CreateConsoleConfiguration(verbose, debug);

        foreach (var level in new[] { LogLevel.Warn, LogLevel.Error, LogLevel.Fatal }) {
            var targets = ConsoleTargetsFor(config, level);
            var target = Assert.Single(targets);
            Assert.True(target.StdErr);
        }
    }

    [Fact]
    public void InfoAndDebugLinesStayOnStdoutAndOnlyWhenRequested() {
        var quiet = PyRevitCLILogging.CreateConsoleConfiguration(false, false);
        Assert.Empty(ConsoleTargetsFor(quiet, LogLevel.Info));
        Assert.Empty(ConsoleTargetsFor(quiet, LogLevel.Debug));

        var chatty = PyRevitCLILogging.CreateConsoleConfiguration(true, true);
        Assert.False(Assert.Single(ConsoleTargetsFor(chatty, LogLevel.Info)).StdErr);
        Assert.False(Assert.Single(ConsoleTargetsFor(chatty, LogLevel.Debug)).StdErr);
    }
}
