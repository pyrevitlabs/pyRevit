using NUnit.Framework;
using pyRevitLabs.Common;

namespace pyRevitLabs.Common.Tests {
    /// <summary>Covers reading the owner/repository id from clone URLs, falling back to the upstream repository when a URL is missing or unrecognized.</summary>
    [TestFixture]
    [FixtureLifeCycle(LifeCycle.InstancePerTestCase)]
    [Category("HostFree")]
    [Category("Unit")]
    public class GithubRepoHelperTests {
        /// <summary>An HTTPS clone URL yields the owner/repository id without the <c>.git</c> suffix.</summary>
        [Test]
        public void ParseRepoId_HttpsGitUrl_Test() {
            var repoId = GithubRepoHelper.ParseRepoId("https://github.com/pyrevitlabs/pyRevit.git");
            Assert.That(repoId, Is.EqualTo("pyrevitlabs/pyRevit"));
        }

        /// <summary>An SSH clone URL yields the owner/repository id without the <c>.git</c> suffix.</summary>
        [Test]
        public void ParseRepoId_SshGitUrl_Test() {
            var repoId = GithubRepoHelper.ParseRepoId("git@github.com:pyrevitlabs/pyRevit.git");
            Assert.That(repoId, Is.EqualTo("pyrevitlabs/pyRevit"));
        }

        /// <summary>A null URL falls back to the upstream repository id.</summary>
        [Test]
        public void ParseRepoId_NullUsesDefault_Test() {
            var repoId = GithubRepoHelper.ParseRepoId(null);
            Assert.That(repoId, Is.EqualTo(PyRevitLabsConsts.OriginalRepoId));
        }

        /// <summary>A fork's clone URL yields the fork's own owner/repository id.</summary>
        [Test]
        public void ParseRepoId_ForkUrl_Test() {
            var repoId = GithubRepoHelper.ParseRepoId("https://github.com/myorg/pyRevit.git");
            Assert.That(repoId, Is.EqualTo("myorg/pyRevit"));
        }

        /// <summary>A URL that is not a GitHub clone URL falls back to the upstream repository id.</summary>
        [Test]
        public void ParseRepoId_UnrecognizedUrlUsesDefault_Test() {
            var repoId = GithubRepoHelper.ParseRepoId("not-a-valid-github-url");
            Assert.That(repoId, Is.EqualTo(PyRevitLabsConsts.OriginalRepoId));
        }
    }
}
