using pyRevitLabs.Common;
using pyRevitLabs.PyRevit;

namespace pyRevitCLI.Tests;

/// <summary>
///     Verifies the Revit language check that <c>pyrevit launch</c> runs before it prepares a launch directory (#3949).
/// </summary>
[Trait("Environment", "HostFree")]
[Trait("Level", "Unit")]
public class LaunchLanguageTests {
    /// <summary>
    ///     Verifies that a three-letter code is trimmed and a blank one means Revit's own choice.
    /// </summary>
    [Theory]
    [InlineData(" ENU ", "ENU")]
    [InlineData("deu", "deu")]
    [InlineData(null, null)]
    [InlineData("  ", null)]
    public void AValidLanguageIsTrimmed(string language, string expected) {
        Assert.Equal(expected, PyRevitLauncher.ParseLanguage(language));
    }

    /// <summary>
    ///     Verifies that anything but a three-letter code is refused.
    /// </summary>
    [Theory]
    [InlineData("EN")]
    [InlineData("ENU /nosplash")]
    [InlineData("EN1")]
    public void AnInvalidLanguageIsRefused(string language) {
        var error = Assert.Throws<PyRevitException>(() => PyRevitLauncher.ParseLanguage(language));
        Assert.Contains("three-letter code", error.Message);
    }
}
