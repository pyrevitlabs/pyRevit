using pyRevitDoctor;

namespace pyRevitDoctor.Tests;

/// <summary>
/// Verifies the doctor finds its command whatever the position of the options (#4050).
/// </summary>
[Trait("Level", "Unit")]
[Trait("Environment", "HostFree")]
public class DoctorArgumentsTests {
    [Theory]
    [InlineData("purge-installs", "purge-installs")]
    [InlineData("purge-installs --dryrun", "purge-installs")]
    [InlineData("--dryrun purge-installs", "purge-installs")]
    [InlineData("--dryrun", null)]
    [InlineData("--dryrun bogus", "bogus")]
    public void FindCommandNameSkipsOptions(string commandLine, string expected) {
        Assert.Equal(expected, DoctorArguments.FindCommandName(commandLine.Split(' ')));
    }
}
