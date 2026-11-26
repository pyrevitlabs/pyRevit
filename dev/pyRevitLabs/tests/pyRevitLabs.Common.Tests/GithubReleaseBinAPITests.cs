using NUnit.Framework;
using pyRevitLabs.Common;

namespace pyRevitLabs.Common.Tests {
    /// <summary>Pins the release asset names and URLs used to fetch CI bins, including encoding of version tags.</summary>
    [TestFixture]
    [FixtureLifeCycle(LifeCycle.InstancePerTestCase)]
    [Category("HostFree")]
    [Category("Integration")]
    public class GithubReleaseBinAPITests {
        /// <summary>Without a tag, release asset URLs point at the <c>ci-binaries</c> release.</summary>
        [Test]
        public void BuildReleaseAssetUrl_ShaZip_Test() {
            var url = GithubReleaseBinAPI.BuildReleaseAssetUrl(
                "pyrevitlabs/pyRevit",
                "unsigned-bin-abc123.zip");
            Assert.That(url, Is.EqualTo("https://github.com/pyrevitlabs/pyRevit/releases/download/ci-binaries/unsigned-bin-abc123.zip"));
        }

        /// <summary>A commit's bin asset is named <c>unsigned-bin-&lt;sha&gt;.zip</c>.</summary>
        [Test]
        public void BuildShaAssetName_Test() {
            var name = GithubReleaseBinAPI.BuildShaAssetName("abc123def456");
            Assert.That(name, Is.EqualTo("unsigned-bin-abc123def456.zip"));
        }

        /// <summary>A branch's latest bin asset is named <c>unsigned-bin-&lt;branch&gt;-latest.zip</c>.</summary>
        [Test]
        public void BuildBranchLatestAssetName_Test() {
            var name = GithubReleaseBinAPI.BuildBranchLatestAssetName("develop");
            Assert.That(name, Is.EqualTo("unsigned-bin-develop-latest.zip"));
        }

        /// <summary>A version tag's bin asset is named <c>bin-&lt;tag&gt;.zip</c> with the tag kept verbatim.</summary>
        [Test]
        public void BuildVersionTagBinAssetName_Test() {
            var name = GithubReleaseBinAPI.BuildVersionTagBinAssetName("v6.5.3.26176+2017");
            Assert.That(name, Is.EqualTo("bin-v6.5.3.26176+2017.zip"));
        }

        /// <summary>With a version tag, the URL uses that tag's release and encodes <c>+</c> as <c>%2B</c> in both the tag and the asset name.</summary>
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
