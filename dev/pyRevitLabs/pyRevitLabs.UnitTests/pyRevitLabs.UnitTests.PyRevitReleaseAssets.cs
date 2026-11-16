using System.Linq;

using Microsoft.VisualStudio.TestTools.UnitTesting;

using pyRevitLabs.Json;
using pyRevitLabs.PyRevit;

namespace pyRevitLabs.UnitTests {
    [TestClass]
    [TestCategory("HostFree")]
    [TestCategory("Unit")]
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
            JsonConvert.DeserializeObject<PyRevitRelease>(json);

        [TestMethod]
        public void GetInstallerURL_DefaultsToUserInstaller_Issue2215() {
            Assert.AreEqual("https://example.test/user.exe", ParseRelease(ReleaseJson).GetInstallerURL());
        }

        [TestMethod]
        public void GetInstallerURL_AdminPicksAdminInstaller_Issue2215() {
            Assert.AreEqual("https://example.test/admin.exe", ParseRelease(ReleaseJson).GetInstallerURL(admin: true));
        }

        [TestMethod]
        public void GetInstallerURL_WithoutInstallerAsset_ReturnsNull_Issue2215() {
            var release = ParseRelease(@"{ ""tag_name"": ""ci-binaries"", ""assets"": [
                { ""name"": ""unsigned-bin-abc.zip"", ""browser_download_url"": ""https://example.test/x.zip"" } ] }");
            Assert.IsNull(release.GetInstallerURL());
        }

        [TestMethod]
        public void GetInstallerURL_WithoutAssets_ReturnsNull_Issue2215() {
            Assert.IsNull(ParseRelease(@"{ ""tag_name"": ""v1.0.0"" }").GetInstallerURL());
        }

        [TestMethod]
        public void FilterPyRevitReleases_HidesPreReleasesUnlessRequested_Issue2215() {
            var releases = new[] {
                ParseRelease(@"{ ""name"": ""stable"", ""tag_name"": ""v7.0.1"", ""prerelease"": false }"),
                ParseRelease(@"{ ""name"": ""rolling"", ""tag_name"": ""ci-binaries"", ""prerelease"": true }"),
                ParseRelease(@"{ ""name"": ""cli"", ""tag_name"": ""cli-v7.0.1"", ""prerelease"": false }")
            };

            CollectionAssert.AreEqual(
                new[] { "stable" },
                PyRevitReleases.FilterPyRevitReleases(releases, includePreRelease: false).Select(r => r.Name).ToArray());
            CollectionAssert.AreEqual(
                new[] { "stable", "rolling" },
                PyRevitReleases.FilterPyRevitReleases(releases, includePreRelease: true).Select(r => r.Name).ToArray());
        }
    }
}
