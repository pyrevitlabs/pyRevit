using System;
using System.IO;

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
    [InlineData("HTTPS://pyrevitlabs.io", "HTTPS://pyrevitlabs.io")]
    [InlineData("  pyrevitlabs.io  ", "http://pyrevitlabs.io")]
    public void UrlStartInfoUsesTheShellAndAnHttpUrl(string url, string expected) {
        var startInfo = CommonUtils.CreateUrlStartInfo(url);

        Assert.True(startInfo.UseShellExecute);
        Assert.Equal(expected, startInfo.FileName);
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public void OpeningAMissingUrlDoesNotThrow(string url) {
        var exception = Record.Exception(() => CommonUtils.OpenUrl(url));

        Assert.Null(exception);
    }

    [Theory]
    [InlineData(@"C:\docs\help.html")]
    [InlineData("file:///C:/docs/help.html")]
    [InlineData("mailto:help@pyrevitlabs.io")]
    public void ShellStartInfoKeepsTheTargetUnchanged(string target) {
        var startInfo = CommonUtils.CreateShellStartInfo(target);

        Assert.True(startInfo.UseShellExecute);
        Assert.Equal(target, startInfo.FileName);
    }

    [Fact]
    public void OpeningATargetNoHandlerCanOpenDoesNotThrow() {
        var missing = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N"), "missing.html");

        var exception = Record.Exception(() => CommonUtils.OpenWithShell(missing));

        Assert.Null(exception);
    }
}
