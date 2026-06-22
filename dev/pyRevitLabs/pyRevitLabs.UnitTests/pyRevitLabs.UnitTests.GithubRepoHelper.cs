using Microsoft.VisualStudio.TestTools.UnitTesting;
using pyRevitLabs.Common;

namespace pyRevitLabs.UnitTests.Common {
    [TestClass]
    public class GithubRepoHelperTests {
        [TestMethod]
        public void ParseRepoId_HttpsGitUrl_Test() {
            var repoId = GithubRepoHelper.ParseRepoId("https://github.com/pyrevitlabs/pyRevit.git");
            Assert.AreEqual("pyrevitlabs/pyRevit", repoId);
        }

        [TestMethod]
        public void ParseRepoId_SshGitUrl_Test() {
            var repoId = GithubRepoHelper.ParseRepoId("git@github.com:pyrevitlabs/pyRevit.git");
            Assert.AreEqual("pyrevitlabs/pyRevit", repoId);
        }

        [TestMethod]
        public void ParseRepoId_NullUsesDefault_Test() {
            var repoId = GithubRepoHelper.ParseRepoId(null);
            Assert.AreEqual(PyRevitLabsConsts.OriginalRepoId, repoId);
        }

        [TestMethod]
        public void ParseRepoId_ForkUrl_Test() {
            var repoId = GithubRepoHelper.ParseRepoId("https://github.com/myorg/pyRevit.git");
            Assert.AreEqual("myorg/pyRevit", repoId);
        }

        [TestMethod]
        public void ParseRepoId_UnrecognizedUrlUsesDefault_Test() {
            var repoId = GithubRepoHelper.ParseRepoId("not-a-valid-github-url");
            Assert.AreEqual(PyRevitLabsConsts.OriginalRepoId, repoId);
        }
    }
}
