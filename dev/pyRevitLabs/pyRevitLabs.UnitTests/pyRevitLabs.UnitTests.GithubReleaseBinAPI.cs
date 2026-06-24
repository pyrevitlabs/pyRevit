using Microsoft.VisualStudio.TestTools.UnitTesting;
using pyRevitLabs.Common;

namespace pyRevitLabs.UnitTests.Common {
    [TestClass]
    public class GithubReleaseBinAPITests {
        [TestMethod]
        public void BuildReleaseAssetUrl_ShaZip_Test() {
            var url = GithubReleaseBinAPI.BuildReleaseAssetUrl(
                "pyrevitlabs/pyRevit",
                "unsigned-bin-abc123.zip");
            Assert.AreEqual(
                "https://github.com/pyrevitlabs/pyRevit/releases/download/ci-binaries/unsigned-bin-abc123.zip",
                url);
        }

        [TestMethod]
        public void BuildShaAssetName_Test() {
            var name = GithubReleaseBinAPI.BuildShaAssetName("abc123def456");
            Assert.AreEqual("unsigned-bin-abc123def456.zip", name);
        }

        [TestMethod]
        public void BuildBranchLatestAssetName_Test() {
            var name = GithubReleaseBinAPI.BuildBranchLatestAssetName("develop");
            Assert.AreEqual("unsigned-bin-develop-latest.zip", name);
        }
    }
}
