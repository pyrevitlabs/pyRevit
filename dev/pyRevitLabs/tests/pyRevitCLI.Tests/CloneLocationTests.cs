using pyRevitCLI;

namespace pyRevitCLI.Tests;

/// <summary>
///     Verifies the running-inside-a-clone test matches directories, not text (#4050).
/// </summary>
[Trait("Environment", "HostFree")]
[Trait("Level", "Unit")]
public class CloneLocationTests {
    [Theory]
    [InlineData(@"C:\pyrevit\bin", @"C:\pyrevit", true)]
    [InlineData(@"C:\pyrevit", @"C:\pyrevit", true)]
    [InlineData(@"C:\pyrevit\bin\", @"C:\pyrevit\", true)]
    [InlineData(@"c:\PyRevit\bin", @"C:\pyrevit", true)]
    [InlineData(@"C:\pyrevit\bin\..\bin", @"C:\pyrevit", true)]
    [InlineData(@"C:\pyrevit2\bin", @"C:\pyrevit", false)]
    [InlineData(@"C:\pyrevit-dev\bin", @"C:\pyrevit", false)]
    [InlineData(@"C:\other\pyrevit\bin", @"C:\pyrevit", false)]
    [InlineData(@"C:\pyrevit\..\other", @"C:\pyrevit", false)]
    public void IsInsideComparesWholeDirectoriesIgnoringCase(string path, string root, bool expected) {
        Assert.Equal(expected, PyRevitCloneLocation.IsInside(path, root));
    }
}
