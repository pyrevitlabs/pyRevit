using NUnit.Framework;
using pyRevitLabs.Common;

namespace pyRevitLabs.Common.Tests {
    /// <summary>Pins the package version and download URL used to fetch CI bins from the GitHub NuGet feed.</summary>
    [TestFixture]
    [FixtureLifeCycle(LifeCycle.InstancePerTestCase)]
    [Category("HostFree")]
    [Category("Integration")]
    public class GithubNuGetBinAPITests {
        /// <summary>The CI package version is <c>1.0.0-ci-</c> followed by the first seven characters of the commit hash.</summary>
        [Test]
        public void BuildPackageVersion_Test() {
            var version = GithubNuGetBinAPI.BuildPackageVersion("abcdef1234567890abcdef1234567890abcdef12");
            Assert.That(version, Is.EqualTo("1.0.0-ci-abcdef1"));
        }

        /// <summary>The download URL points at the owner's GitHub NuGet feed with the lowercase package id and versioned <c>.nupkg</c> file name.</summary>
        [Test]
        public void BuildPackageDownloadUrl_Test() {
            var url = GithubNuGetBinAPI.BuildPackageDownloadUrl(
                "pyrevitlabs/pyRevit",
                "1.0.0-ci-abcdef1");
            Assert.That(url, Is.EqualTo("https://nuget.pkg.github.com/pyrevitlabs/download/pyrevit.unsignedbin/1.0.0-ci-abcdef1/PyRevit.UnsignedBin.1.0.0-ci-abcdef1.nupkg"));
        }
    }
}
