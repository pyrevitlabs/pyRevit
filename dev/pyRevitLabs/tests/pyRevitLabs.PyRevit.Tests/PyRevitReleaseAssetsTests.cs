using pyRevitLabs.Json;
using pyRevitLabs.PyRevit;

namespace pyRevitLabs.PyRevit.Tests;

/// <summary>
///     Verifies which release assets the updater offers as installers and which releases it lists (#2215).
/// </summary>
[TestFixture]
[Category("HostFree")]
[Category("Unit")]
public class PyRevitReleaseAssetsTests {
    private const string ReleaseJson = @"{
        ""name"": ""pyRevit v7.0.1"",
        ""tag_name"": ""v7.0.1.26312+1155"",
        ""prerelease"": false,
        ""assets"": [
            { ""name"": ""bin-v7.0.1.26312+1155.zip"", ""browser_download_url"": ""https://example.test/bin.zip"" },
            { ""name"": ""pyrevit-cli.7.0.1.26312.nupkg"", ""browser_download_url"": ""https://example.test/cli.nupkg"" },
            { ""name"": ""pyRevit_7.0.1.26312_admin_signed.exe"", ""browser_download_url"": ""https://example.test/admin.exe"" },
            { ""name"": ""pyRevit_7.0.1.26312_signed.exe"", ""browser_download_url"": ""https://example.test/user.exe"" },
            { ""name"": ""pyRevit_CLI_7.0.1.26312_admin_signed.exe"", ""browser_download_url"": ""https://example.test/cli-admin.exe"" },
            { ""name"": ""pyRevit_CLI_7.0.1.26312_signed.exe"", ""browser_download_url"": ""https://example.test/cli-user.exe"" }
        ]
    }";

    private static PyRevitRelease ParseRelease(string json) =>
        JsonConvert.DeserializeObject<PyRevitRelease>(json)!;

    [Test]
    public void GetInstallerURL_DefaultsToUserInstaller_Issue2215() {
        Assert.That(ParseRelease(ReleaseJson).GetInstallerURL(), Is.EqualTo("https://example.test/user.exe"));
    }

    [Test]
    public void GetInstallerURL_AdminPicksAdminInstaller_Issue2215() {
        Assert.That(ParseRelease(ReleaseJson).GetInstallerURL(admin: true), Is.EqualTo("https://example.test/admin.exe"));
    }

    [Test]
    public void GetInstallerURL_WithoutInstallerAsset_ReturnsNull_Issue2215() {
        var release = ParseRelease(@"{ ""tag_name"": ""ci-binaries"", ""assets"": [
            { ""name"": ""unsigned-bin-abc.zip"", ""browser_download_url"": ""https://example.test/x.zip"" } ] }");
        Assert.That(release.GetInstallerURL(), Is.Null);
    }

    [Test]
    public void GetInstallerURL_WithoutAssets_ReturnsNull_Issue2215() {
        Assert.That(ParseRelease(@"{ ""tag_name"": ""v1.0.0"" }").GetInstallerURL(), Is.Null);
    }

    [Test]
    public void FilterPyRevitReleases_HidesPreReleasesUnlessRequested_Issue2215() {
        var releases = new[] {
            ParseRelease(@"{ ""name"": ""stable"", ""tag_name"": ""v7.0.1"", ""prerelease"": false }"),
            ParseRelease(@"{ ""name"": ""rolling"", ""tag_name"": ""ci-binaries"", ""prerelease"": true }"),
            ParseRelease(@"{ ""name"": ""cli"", ""tag_name"": ""cli-v7.0.1"", ""prerelease"": false }")
        };

        Assert.That(
            PyRevitReleases.FilterPyRevitReleases(releases, includePreRelease: false).Select(r => r.Name),
            Is.EqualTo(new[] { "stable" }));
        Assert.That(
            PyRevitReleases.FilterPyRevitReleases(releases, includePreRelease: true).Select(r => r.Name),
            Is.EqualTo(new[] { "stable", "rolling" }));
    }
}
