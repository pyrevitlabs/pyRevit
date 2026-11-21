using System.Reflection;

using pyRevitLabs.TargetApps.Revit;

namespace pyRevitCLI.Tests;

/// <summary>
///     Verifies how an installed Revit executable is identified without a Revit installation.
/// </summary>
[Trait("Environment", "HostFree")]
[Trait("Level", "Unit")]
public class RevitProductFileVersionTests {
    [Fact]
    public void ReadBinaryFileVersionIsNullWithoutAnExecutable() {
        Assert.Null(RevitProduct.ReadBinaryFileVersion(null));
    }

    [Fact]
    public void ReadBinaryFileVersionIsNullForAMissingFile() {
        var missing = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N"), "Revit.exe");

        Assert.Null(RevitProduct.ReadBinaryFileVersion(missing));
    }

    [Fact]
    public void ReadBinaryFileVersionReadsTheFileVersionOfAnExistingBinary() {
        var binary = Assembly.GetExecutingAssembly().Location;

        Assert.False(string.IsNullOrEmpty(RevitProduct.ReadBinaryFileVersion(binary)));
    }

    [Fact]
    public void FindRevitProductIsNullWhenNeitherVersionNorBinaryIsKnown() {
        Assert.Null(RevitProduct.FindRevitProduct(null, null, null));
    }
}
