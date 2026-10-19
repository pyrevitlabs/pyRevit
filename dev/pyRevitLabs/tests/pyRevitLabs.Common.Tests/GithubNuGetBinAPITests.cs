using Microsoft.VisualStudio.TestTools.UnitTesting;
using Assert = Microsoft.VisualStudio.TestTools.UnitTesting.Assert;
using CollectionAssert = Microsoft.VisualStudio.TestTools.UnitTesting.CollectionAssert;
using StringAssert = Microsoft.VisualStudio.TestTools.UnitTesting.StringAssert;
using pyRevitLabs.Common;

namespace pyRevitLabs.Common.Tests {
    [TestClass]
    [TestCategory("HostFree")]
    [TestCategory("Unit")]
    public class GithubNuGetBinAPITests {
        [TestMethod]
        public void BuildPackageVersion_Test() {
            var version = GithubNuGetBinAPI.BuildPackageVersion("abcdef1234567890abcdef1234567890abcdef12");
            Assert.AreEqual("1.0.0-ci-abcdef1", version);
        }

        [TestMethod]
        public void BuildPackageDownloadUrl_Test() {
            var url = GithubNuGetBinAPI.BuildPackageDownloadUrl(
                "pyrevitlabs/pyRevit",
                "1.0.0-ci-abcdef1");
            Assert.AreEqual(
                "https://nuget.pkg.github.com/pyrevitlabs/download/pyrevit.unsignedbin/1.0.0-ci-abcdef1/PyRevit.UnsignedBin.1.0.0-ci-abcdef1.nupkg",
                url);
        }
    }
}
