using NUnit.Framework;
using pyRevitLabs.Common;

namespace pyRevitLabs.Common.Tests {
    /// <summary>Covers the binaries install for a git clone without network access.</summary>
    [TestFixture]
    [FixtureLifeCycle(LifeCycle.InstancePerTestCase)]
    [Category("HostFree")]
    [Category("Unit")]
    public class BinArtifactInstallerTests {
        /// <summary>A clone without an origin remote fails before any download is attempted (#4042).</summary>
        [Test]
        [Category("Integration")]
        [Category("Regression")]
        public void InstallForRepoClone_WhenTheCloneHasNoOrigin_Throws() {
            var repoPath = Path.Combine(Path.GetTempPath(), "binInstallNoOrigin_" + Guid.NewGuid().ToString("N"));
            LibGit2Sharp.Repository.Init(repoPath);
            try {
                var ex = Assert.Throws<PyRevitException>(
                    () => BinArtifactInstaller.InstallForRepoClone(repoPath, null, BinArtifactInstallMode.Clone));

                Assert.That(ex!.Message, Does.Contain("no origin remote"));
            }
            finally {
                Directory.Delete(repoPath, true);
            }
        }
    }
}
