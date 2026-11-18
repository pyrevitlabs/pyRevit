using pyRevitCLI;
using pyRevitLabs.Common;

namespace pyRevitCLI.Tests;

/// <summary>
///     Verifies that values the CLI cannot use are rejected with an error instead of being skipped silently:
///     <c>caches clear abc</c>, <c>agent runs --limit=abc</c>, <c>configs outputcss &lt;missing file&gt;</c>
///     and <c>configs telemetry file &lt;missing folder&gt;</c> exited 0 without doing anything.
/// </summary>
[Trait("Environment", "HostFree")]
[Trait("Level", "Unit")]
public class CliInputValidationTests {
    [Fact]
    public void RevitYearParsesWholeNumbers() {
        Assert.Equal(2026, PyRevitCLIArguments.RevitYear("2026"));
    }

    [Theory]
    [InlineData("abc")]
    [InlineData("")]
    [InlineData("20x6")]
    public void RevitYearRejectsText(string text) {
        var error = Assert.Throws<PyRevitException>(() => PyRevitCLIArguments.RevitYear(text));

        Assert.Contains("Invalid Revit year", error.Message);
    }

    [Fact]
    public void LimitFallsBackToTheDefaultWhenNotGiven() {
        Assert.Equal(20, PyRevitCLIArguments.Limit(null, defaultLimit: 20));
    }

    [Fact]
    public void LimitParsesPositiveNumbers() {
        Assert.Equal(5, PyRevitCLIArguments.Limit("5", defaultLimit: 20));
    }

    [Theory]
    [InlineData("abc")]
    [InlineData("0")]
    [InlineData("-3")]
    public void LimitRejectsTextAndNonPositiveNumbers(string text) {
        var error = Assert.Throws<PyRevitException>(() => PyRevitCLIArguments.Limit(text, defaultLimit: 20));

        Assert.Contains("Invalid limit", error.Message);
    }

    [Fact]
    public void ExistingFileAndDirectoryAcceptWhatExists() {
        var folder = Path.Combine(Path.GetTempPath(), "pyrevit-cli-validation-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(folder);
        var file = Path.Combine(folder, "output.css");
        File.WriteAllText(file, "body {}");
        try {
            Assert.Equal(file, PyRevitCLIArguments.ExistingFile(file, "style sheet"));
            Assert.Equal(folder, PyRevitCLIArguments.ExistingDirectory(folder, "telemetry folder"));
        }
        finally {
            Directory.Delete(folder, recursive: true);
        }
    }

    [Fact]
    public void ExistingFileAndDirectoryRejectWhatIsMissing() {
        var missing = Path.Combine(Path.GetTempPath(), "pyrevit-cli-validation-" + Guid.NewGuid().ToString("N"));

        var fileError = Assert.Throws<PyRevitException>(() => PyRevitCLIArguments.ExistingFile(missing, "style sheet"));
        var directoryError = Assert.Throws<PyRevitException>(() => PyRevitCLIArguments.ExistingDirectory(missing, "telemetry folder"));

        Assert.Contains("style sheet", fileError.Message);
        Assert.Contains("telemetry folder", directoryError.Message);
    }
}
