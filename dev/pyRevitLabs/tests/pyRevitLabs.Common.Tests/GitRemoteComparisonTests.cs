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
        [TestCase("", "https://github.com/pyrevitlabs/pyRevit")]
        [TestCase(null, null)]
        public void AreSameRemote_DifferentSources_ReturnsFalse(string? first, string? second) {
            Assert.That(GitInstaller.AreSameRemote(first, second), Is.False);
        }
    }
}
