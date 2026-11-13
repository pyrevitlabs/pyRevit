using pyRevitLabs.Common;

namespace pyRevitCLI.Tests;

/// <summary>
///     Verifies URLs are started through the shell so they open on .NET 8 and later (#4050).
/// </summary>
[Trait("Environment", "HostFree")]
[Trait("Level", "Unit")]
public class OpenUrlTests {
    [Theory]
    [InlineData("https://pyrevitlabs.io", "https://pyrevitlabs.io")]
    [InlineData("http://pyrevitlabs.io/docs", "http://pyrevitlabs.io/docs")]
    [InlineData("pyrevitlabs.io", "http://pyrevitlabs.io")]
    public void UrlStartInfoUsesTheShellAndAnHttpUrl(string url, string expected) {
        var startInfo = CommonUtils.CreateUrlStartInfo(url);

        Assert.True(startInfo.UseShellExecute);
        Assert.Equal(expected, startInfo.FileName);
    }
}
