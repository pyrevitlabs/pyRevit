using NUnit.Framework;
using pyRevitLabs.Common;

namespace pyRevitLabs.Common.Tests {
    [TestFixture]
    [FixtureLifeCycle(LifeCycle.InstancePerTestCase)]
    [Category("HostFree")]
    [Category("Unit")]
    public class GithubRepoHelperTests {
        [Test]
        public void ParseRepoId_HttpsGitUrl_Test() {
            var repoId = GithubRepoHelper.ParseRepoId("https://github.com/pyrevitlabs/pyRevit.git");
            Assert.That(repoId, Is.EqualTo("pyrevitlabs/pyRevit"));
        }

        [Test]
        public void ParseRepoId_SshGitUrl_Test() {
            var repoId = GithubRepoHelper.ParseRepoId("git@github.com:pyrevitlabs/pyRevit.git");
            Assert.That(repoId, Is.EqualTo("pyrevitlabs/pyRevit"));
        }

        [Test]
        public void ParseRepoId_NullUsesDefault_Test() {
            var repoId = GithubRepoHelper.ParseRepoId(null);
            Assert.That(repoId, Is.EqualTo(PyRevitLabsConsts.OriginalRepoId));
        }

        [Test]
        public void ParseRepoId_ForkUrl_Test() {
            var repoId = GithubRepoHelper.ParseRepoId("https://github.com/myorg/pyRevit.git");
            Assert.That(repoId, Is.EqualTo("myorg/pyRevit"));
        }

        [Test]
        public void ParseRepoId_UnrecognizedUrlUsesDefault_Test() {
            var repoId = GithubRepoHelper.ParseRepoId("not-a-valid-github-url");
            Assert.That(repoId, Is.EqualTo(PyRevitLabsConsts.OriginalRepoId));
        }
    }
}
