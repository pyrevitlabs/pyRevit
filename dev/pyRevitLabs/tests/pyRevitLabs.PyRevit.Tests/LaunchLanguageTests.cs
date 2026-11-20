using pyRevitLabs.Common;
using pyRevitLabs.PyRevit;

namespace pyRevitLabs.PyRevit.Tests;

/// <summary>
///     Verifies the Revit language check that <c>pyrevit launch</c> runs before it prepares a launch directory (#3949).
/// </summary>
[TestFixture]
[Category("HostFree")]
[Category("Unit")]
public class LaunchLanguageTests {
    /// <summary>
    ///     Verifies that a three-letter code is trimmed and a blank one means Revit's own choice.
    /// </summary>
    [TestCase(" ENU ", "ENU")]
    [TestCase("deu", "deu")]
    [TestCase(null, null)]
    [TestCase("  ", null)]
    public void AValidLanguageIsTrimmed(string? language, string? expected) {
        Assert.That(PyRevitLauncher.ParseLanguage(language), Is.EqualTo(expected));
    }

    /// <summary>
    ///     Verifies that anything but a three-letter code is refused.
    /// </summary>
    [TestCase("EN")]
    [TestCase("ENU /nosplash")]
    [TestCase("EN1")]
    public void AnInvalidLanguageIsRefused(string language) {
        var error = Assert.Throws<PyRevitException>(() => PyRevitLauncher.ParseLanguage(language));
        Assert.That(error!.Message, Does.Contain("three-letter code"));
    }
}
