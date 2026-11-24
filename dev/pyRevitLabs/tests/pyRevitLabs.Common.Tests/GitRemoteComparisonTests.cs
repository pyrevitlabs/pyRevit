using NUnit.Framework;
using pyRevitLabs.Common;

namespace pyRevitLabs.Common.Tests {
    /// <summary>Covers comparing a stored git remote with a requested clone source.</summary>
    [TestFixture]
    [FixtureLifeCycle(LifeCycle.InstancePerTestCase)]
    [Category("HostFree")]
    [Category("Unit")]
    public class GitRemoteComparisonTests {
        /// <summary>Writing the same remote differently still compares equal.</summary>
        [TestCase("https://github.com/pyrevitlabs/pyRevit.git", "https://github.com/pyrevitlabs/pyRevit")]
        [TestCase("https://github.com/pyrevitlabs/pyRevit/", "https://github.com/pyrevitlabs/pyRevit.git")]
        [TestCase("https://GitHub.com/pyrevitlabs/pyRevit", "https://github.com/pyrevitlabs/pyRevit")]
        [TestCase("https://user:secret@github.com/pyrevitlabs/pyRevit.git", "https://github.com/pyrevitlabs/pyRevit")]
        [TestCase("git@github.com:pyrevitlabs/pyRevit.git", "https://github.com/pyrevitlabs/pyRevit")]
        [TestCase("git@github.com:pyrevitlabs/pyRevit.git", "github.com:pyrevitlabs/pyRevit")]
        [TestCase("https://github.com\\pyrevitlabs\\pyRevit", "https://github.com/pyrevitlabs/pyRevit")]
        [TestCase("C:\\dev\\source\\\\", "c:/dev/source")]
        [TestCase("C:\\dev\\Source", "c:\\DEV\\source")]
        [TestCase("C:\\dev\\a\\..\\source", "C:\\dev\\source")]
        [TestCase("\\\\server\\share\\repo", "//server/share/repo")]
        [TestCase("ssh://git@host/org/repo", "https://host/org/repo")]
        [TestCase("git@host:/repos/pyRevit.git", "git@host:/repos/pyRevit")]
        [TestCase("git@host:repos/pyRevit.git", "host:repos/pyRevit")]
        [TestCase("git@host:/repos/pyRevit.git", "https://host/repos/pyRevit")]
        [TestCase("git@host:/repos/pyRevit.git", "ssh://git@host/repos/pyRevit.git")]
        [TestCase("file:///C:/dev/source", "C:\\dev\\source")]
        public void AreSameRemote_EquivalentSources_ReturnsTrue(string? first, string? second) {
            Assert.That(GitInstaller.AreSameRemote(first, second), Is.True);
            Assert.That(GitInstaller.AreSameRemote(second, first), Is.True);
        }

        /// <summary>Different hosts, different path case, other paths and empty values never match.</summary>
        [TestCase("https://github.com/pyrevitlabs/pyRevit", "https://github.com/pyrevitlabs/pyrevit")]
        [TestCase("https://github.com/pyrevitlabs/pyRevit", "https://gitlab.com/pyrevitlabs/pyRevit")]
        [TestCase("git@github.com:pyrevitlabs/pyRevit.git", "git@gitlab.com:pyrevitlabs/pyRevit.git")]
        [TestCase("https://github.com/pyrevitlabs/pyRevit", "https://github.com/other/pyRevit")]
        [TestCase("C:\\dev\\source", "C:\\dev\\other")]
        [TestCase("C:\\dev\\source", "https://github.com/pyrevitlabs/pyRevit")]
        [TestCase("https://host:8443/org/repo", "https://host:9443/org/repo")]
        [TestCase("ssh://git@host1/org/repo", "ssh://git@host2/org/repo")]
        [TestCase("git@host:repos/pyRevit.git", "git@host:/repos/pyRevit.git")]
        [TestCase("host:/repos/pyRevit", "git@host:repos/pyRevit")]
        [TestCase("git@host:repos/pyRevit.git", "ssh://git@host/repos/pyRevit.git")]
        [TestCase("\\\\server\\share\\a", "\\\\server\\share\\b")]
        [TestCase("relative\\repo", "C:\\dev\\source")]
        [TestCase("file:///C:/dev/source", "file:///C:/dev/other")]
        [TestCase("", "https://github.com/pyrevitlabs/pyRevit")]
        [TestCase(null, null)]
        public void AreSameRemote_DifferentSources_ReturnsFalse(string? first, string? second) {
            Assert.That(GitInstaller.AreSameRemote(first, second), Is.False);
        }

        /// <summary>A missing remote and a folder that is not a repository both read as null.</summary>
        [Test]
        [Category("Integration")]
        public void GetRemoteUrl_WhenTheRemoteOrRepositoryIsMissing_ReturnsNull() {
            var root = Path.Combine(Path.GetTempPath(), "gitRemoteUrl_" + Guid.NewGuid().ToString("N"));
            var repoPath = Path.Combine(root, "repo");
            var plainFolder = Path.Combine(root, "plain");
            Directory.CreateDirectory(plainFolder);
            LibGit2Sharp.Repository.Init(repoPath);
            try {
                using (var repo = new LibGit2Sharp.Repository(repoPath))
                    repo.Network.Remotes.Add("upstream", "https://example.invalid/org/repo");

                Assert.That(GitInstaller.GetRemoteUrl(repoPath, "origin"), Is.Null);
                Assert.That(GitInstaller.GetRemoteUrl(repoPath, "upstream"), Is.EqualTo("https://example.invalid/org/repo"));
                Assert.That(GitInstaller.GetRemoteUrl(plainFolder, "origin"), Is.Null);
            }
            finally {
                Directory.Delete(root, true);
            }
        }
    }
}
