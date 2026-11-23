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

    /// <summary>By default the installer URL is the signed per-user pyRevit installer, not the CLI or admin one.</summary>
    [Test]
    public void GetInstallerURL_DefaultsToUserInstaller_Issue2215() {
        Assert.That(ParseRelease(ReleaseJson).GetInstallerURL(), Is.EqualTo("https://example.test/user.exe"));
    }

    /// <summary>Asking for admin returns the signed all-users pyRevit installer.</summary>
    [Test]
    public void GetInstallerURL_AdminPicksAdminInstaller_Issue2215() {
        Assert.That(ParseRelease(ReleaseJson).GetInstallerURL(admin: true), Is.EqualTo("https://example.test/admin.exe"));
    }

    /// <summary>A release with assets but no installer has no installer URL.</summary>
    [Test]
    public void GetInstallerURL_WithoutInstallerAsset_ReturnsNull_Issue2215() {
        var release = ParseRelease(@"{ ""tag_name"": ""ci-binaries"", ""assets"": [
            { ""name"": ""unsigned-bin-abc.zip"", ""browser_download_url"": ""https://example.test/x.zip"" } ] }");
        Assert.That(release.GetInstallerURL(), Is.Null);
    }

    /// <summary>A release with no assets has no installer URL.</summary>
    [Test]
    public void GetInstallerURL_WithoutAssets_ReturnsNull_Issue2215() {
        Assert.That(ParseRelease(@"{ ""tag_name"": ""v1.0.0"" }").GetInstallerURL(), Is.Null);
    }

    /// <summary>Release filtering always drops CLI releases and keeps pre-releases only when requested.</summary>
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

    /// <summary>Releases are listed newest version first, not by creation time (#4216).</summary>
    [Test]
    public void SortNewestFirst_OrdersByVersionNotByCreationTime_Issue4216() {
        var releases = new[] {
            ParseRelease(@"{ ""name"": ""old, created late"", ""tag_name"": ""v4.6.9"", ""created_at"": ""2026-11-20T10:00:00Z"" }"),
            ParseRelease(@"{ ""name"": ""stable"", ""tag_name"": ""4.0-stable"", ""created_at"": ""2026-11-19T10:00:00Z"" }"),
            ParseRelease(@"{ ""name"": ""newest"", ""tag_name"": ""v7.1.0.26319+1907"", ""created_at"": ""2026-11-15T19:43:09Z"" }"),
            ParseRelease(@"{ ""name"": ""older"", ""tag_name"": ""v6.5.5.26237+2044"", ""created_at"": ""2026-08-25T18:47:09Z"" }")
        };

        Assert.That(
            PyRevitReleases.SortNewestFirst(releases).Select(r => r.Name).ToArray(),
            Is.EqualTo(new[] { "newest", "older", "old, created late", "stable" }));
    }

    /// <summary>Releases with the same version are ordered by the newest creation time first.</summary>
    [Test]
    public void SortNewestFirst_BreaksVersionTiesByNewestCreation_Issue4216() {
        var releases = new[] {
            ParseRelease(@"{ ""name"": ""first"", ""tag_name"": ""v7.0.0"", ""created_at"": ""2026-10-01T00:00:00Z"" }"),
            ParseRelease(@"{ ""name"": ""second"", ""tag_name"": ""v7.0.0"", ""created_at"": ""2026-10-02T00:00:00Z"" }")
        };

        Assert.That(
            PyRevitReleases.SortNewestFirst(releases).Select(r => r.Name).ToArray(),
            Is.EqualTo(new[] { "second", "first" }));
    }
}
