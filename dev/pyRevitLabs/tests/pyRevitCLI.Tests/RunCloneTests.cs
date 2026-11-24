using pyRevitLabs.Common;
using pyRevitLabs.PyRevit;
using pyRevitLabs.TargetApps.Revit;

namespace pyRevitCLI.Tests;

/// <summary>
///     Verifies that <c>pyrevit run --clone</c> can use a clone the machine is not attached to.
/// </summary>
[Trait("Environment", "HostFree")]
[Trait("Level", "Unit")]
public sealed class RunCloneTests {
    private static IDictionary<string, DocoptNet.ValueObject> Parse(params string[] argv) {
        var usage = File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "UsagePatterns.txt"));
        return new DocoptNet.Docopt().Apply(usage, argv, help: false, exit: false);
    }

    /// <summary>
    ///     Verifies that the clone selector is accepted with a script, with a model and with a model list.
    /// </summary>
    [Fact]
    public void TheCloneSelectorIsAcceptedByEveryRunPattern() {
        Assert.Equal("dev", Parse("run", "script.py", "--clone=dev")["--clone"].Value);
        Assert.Equal("dev", Parse("run", "script.py", "model.rvt", "--revit=2026", "--clone=dev")["--clone"].Value);
        Assert.Equal("dev", Parse("run", "script.py", "--models=list.txt", "--revit=2026", "--clone=dev")["--clone"].Value);
    }

    /// <summary>
    ///     Verifies that a run without the selector keeps using the attached clone.
    /// </summary>
    [Fact]
    public void WithoutTheSelectorTheCloneIsNotSet() {
        Assert.True(Parse("run", "script.py")["--clone"].IsNullOrEmpty);
    }

    /// <summary>
    ///     Verifies that a Revit year older than this pyRevit line supports is refused before any clone is read.
    /// </summary>
    [Fact]
    public void AnUnsupportedRevitYearIsRefused() {
        var error = Assert.Throws<PyRevitException>(
            () => PyRevitAttachments.ForClone(null, PyRevitEngineVersion.Default, 2010));

        Assert.Contains("this pyRevit line supports Revit", error.Message);
    }

    /// <summary>
    ///     Verifies that an add-in description built in memory has no file behind it.
    /// </summary>
    [Fact]
    public void AnInMemoryManifestHasNoFile() {
        var manifest = new RevitAddonManifest("pyRevit", @"C:\clone\bin\engines\IPY2712\pyRevitLoader.dll", "id", "Loader.App", "vendor");

        Assert.Null(manifest.FilePath);
        Assert.Equal("pyRevit", manifest.Name);
        Assert.EndsWith("pyRevitLoader.dll", manifest.Assembly);
    }
}
