using NUnit.Framework;
using pyRevitLabs.Common;

namespace pyRevitLabs.Common.Tests {
    [TestFixture]
    [FixtureLifeCycle(LifeCycle.InstancePerTestCase)]
    [Category("HostFree")]
    [Category("Unit")]
    public class GithubReleaseBinAPITests {
        [Test]
        public void BuildReleaseAssetUrl_ShaZip_Test() {
            var url = GithubReleaseBinAPI.BuildReleaseAssetUrl(
                "pyrevitlabs/pyRevit",
                "unsigned-bin-abc123.zip");
            Assert.That(url, Is.EqualTo("https://github.com/pyrevitlabs/pyRevit/releases/download/ci-binaries/unsigned-bin-abc123.zip"));
        }

        [Test]
        public void BuildShaAssetName_Test() {
            var name = GithubReleaseBinAPI.BuildShaAssetName("abc123def456");
            Assert.That(name, Is.EqualTo("unsigned-bin-abc123def456.zip"));
        }

        [Test]
        public void BuildBranchLatestAssetName_Test() {
            var name = GithubReleaseBinAPI.BuildBranchLatestAssetName("develop");
            Assert.That(name, Is.EqualTo("unsigned-bin-develop-latest.zip"));
        }

        [Test]
        public void BuildVersionTagBinAssetName_Test() {
            var name = GithubReleaseBinAPI.BuildVersionTagBinAssetName("v6.5.3.26176+2017");
            Assert.That(name, Is.EqualTo("bin-v6.5.3.26176+2017.zip"));
        }

        [Test]
        public void BuildReleaseAssetUrl_VersionTagEncodesPlus_Test() {
            var url = GithubReleaseBinAPI.BuildReleaseAssetUrl(
                "pyrevitlabs/pyRevit",
                "bin-v6.5.3.26176+2017.zip",
                "v6.5.3.26176+2017");
            Assert.That(url, Is.EqualTo("https://github.com/pyrevitlabs/pyRevit/releases/download/v6.5.3.26176%2B2017/bin-v6.5.3.26176%2B2017.zip"));
        }
    }
}
