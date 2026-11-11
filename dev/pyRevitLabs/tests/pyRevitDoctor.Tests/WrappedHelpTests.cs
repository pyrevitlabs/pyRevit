using pyRevitDoctor;

namespace pyRevitDoctor.Tests;

/// <summary>
/// Coverage for the help text <c>pyrevit doctor --help</c> derives from the standalone doctor help.
/// </summary>
[Trait("Level", "Unit")]
[Trait("Environment", "HostFree")]
public class WrappedHelpTests {
    private const string Help = "Fix potential or real problems\n\nUsage:\n"
        + "    pyrevit-doctor (-V | --version)\n"
        + "    pyrevit-doctor (-h | --help)\n"
        + "    pyrevit-doctor <doctor_command> [--dryrun]\n";

    [Theory]
    [InlineData("\n")]
    [InlineData("\r\n")]
    public void TheVersionUsageLineIsDroppedWhateverTheLineEndings(string lineEnding) {
        var wrapped = WrappedHelp.From(Help.Replace("\n", lineEnding));

        Assert.DoesNotContain("--version", wrapped);
        Assert.DoesNotContain("-V", wrapped);
    }

    [Fact]
    public void TheCommandIsNamedAsPyrevitSubcommand() {
        var wrapped = WrappedHelp.From(Help);

        Assert.DoesNotContain("pyrevit-doctor", wrapped);
        Assert.Contains("pyrevit doctor (-h | --help)", wrapped);
        Assert.Contains("pyrevit doctor <doctor_command> [--dryrun]", wrapped);
    }
}
