using NUnit.Framework;
using pyRevitLabs.Common;

namespace pyRevitLabs.Common.Tests {
    [TestFixture]
    [FixtureLifeCycle(LifeCycle.InstancePerTestCase)]
    [Category("HostFree")]
    [Category("Unit")]
    public class GithubNuGetBinAPITests {
        [Test]
        public void BuildPackageVersion_Test() {
            var version = GithubNuGetBinAPI.BuildPackageVersion("abcdef1234567890abcdef1234567890abcdef12");
            Assert.That(version, Is.EqualTo("1.0.0-ci-abcdef1"));
        }

        [Test]
        public void BuildPackageDownloadUrl_Test() {
            var url = GithubNuGetBinAPI.BuildPackageDownloadUrl(
                "pyrevitlabs/pyRevit",
                "1.0.0-ci-abcdef1");
            Assert.That(url, Is.EqualTo("https://nuget.pkg.github.com/pyrevitlabs/download/pyrevit.unsignedbin/1.0.0-ci-abcdef1/PyRevit.UnsignedBin.1.0.0-ci-abcdef1.nupkg"));
        }
    }
}
