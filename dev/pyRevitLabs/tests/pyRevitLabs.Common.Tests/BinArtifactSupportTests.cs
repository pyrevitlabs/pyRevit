using System;
using System.IO;

using NUnit.Framework;
using pyRevitLabs.Common;

namespace pyRevitLabs.Common.Tests {
    [TestFixture]
    [FixtureLifeCycle(LifeCycle.InstancePerTestCase)]
    [Category("HostFree")]
    [Category("Integration")]
    public class BinArtifactSupportTests {
        private string _tempRoot = null!;

        [SetUp]
        public void SetUp() {
            _tempRoot = Path.Combine(
                Path.GetTempPath(),
                string.Format("pyrevit-bin-support-{0}", Guid.NewGuid().ToString("N")));
            Directory.CreateDirectory(_tempRoot);
        }

        [TearDown]
        public void TearDown() {
            if (Directory.Exists(_tempRoot))
                Directory.Delete(_tempRoot, recursive: true);
        }

        [Test]
        public void IsSupportedCiBinBranch_DevelopAndMaster_Test() {
            Assert.That(BinArtifactSupport.IsSupportedCiBinBranch("develop"), Is.True);
            Assert.That(BinArtifactSupport.IsSupportedCiBinBranch("master"), Is.True);
            Assert.That(BinArtifactSupport.IsSupportedCiBinBranch("Develop"), Is.True);
        }

        [Test]
        public void IsSupportedCiBinBranch_OtherBranches_Test() {
            Assert.That(BinArtifactSupport.IsSupportedCiBinBranch("feature/foo"), Is.False);
            Assert.That(BinArtifactSupport.IsSupportedCiBinBranch("v6.5.3.26176+2017"), Is.False);
            Assert.That(BinArtifactSupport.IsSupportedCiBinBranch(null), Is.False);
            Assert.That(BinArtifactSupport.IsSupportedCiBinBranch(string.Empty), Is.False);
        }

        [Test]
        public void IsVersionTagRef_PublishedReleaseTags_Test() {
            Assert.That(BinArtifactSupport.IsVersionTagRef("v6.5.3.26176+2017"), Is.True);
            Assert.That(BinArtifactSupport.IsVersionTagRef("V6.5.3.26176+2017"), Is.True);
            Assert.That(BinArtifactSupport.IsVersionTagRef(" v4.8.16 "), Is.True);
        }

        [Test]
        public void IsVersionTagRef_NonVersionRefs_Test() {
            Assert.That(BinArtifactSupport.IsVersionTagRef("develop"), Is.False);
            Assert.That(BinArtifactSupport.IsVersionTagRef("master"), Is.False);
            Assert.That(BinArtifactSupport.IsVersionTagRef("feature/foo"), Is.False);
            Assert.That(BinArtifactSupport.IsVersionTagRef("version"), Is.False);
            Assert.That(BinArtifactSupport.IsVersionTagRef("v"), Is.False);
            Assert.That(BinArtifactSupport.IsVersionTagRef(null), Is.False);
            Assert.That(BinArtifactSupport.IsVersionTagRef(string.Empty), Is.False);
        }

        [Test]
        public void GetReleaseDownloadRepos_ForkIncludesUpstream_Test() {
            var repos = BinArtifactSupport.GetReleaseDownloadRepos("myorg/pyRevit");
            Assert.That(repos.Count, Is.EqualTo(2));
            Assert.That(repos[0], Is.EqualTo("myorg/pyRevit"));
            Assert.That(repos[1], Is.EqualTo(PyRevitLabsConsts.OriginalRepoId));
        }

        [Test]
        public void GetReleaseDownloadRepos_UpstreamOnly_Test() {
            var repos = BinArtifactSupport.GetReleaseDownloadRepos(PyRevitLabsConsts.OriginalRepoId);
            Assert.That(repos.Count, Is.EqualTo(1));
            Assert.That(repos[0], Is.EqualTo(PyRevitLabsConsts.OriginalRepoId));
        }

        [Test]
        public void ResolveBinSourceRoot_DirectBinWrapper_Test() {
            var extractRoot = Path.Combine(_tempRoot, "extract-direct");
            var binDir = Path.Combine(extractRoot, "bin");
            Directory.CreateDirectory(binDir);
            File.WriteAllText(Path.Combine(binDir, "marker.txt"), "ok");

            var resolved = BinArtifactSupport.ResolveBinSourceRoot(extractRoot);
            Assert.That(resolved, Is.EqualTo(binDir));
        }

        [Test]
        public void ResolveBinSourceRoot_FlatRoot_Test() {
            var extractRoot = Path.Combine(_tempRoot, "extract-flat");
            Directory.CreateDirectory(extractRoot);
            Directory.CreateDirectory(Path.Combine(extractRoot, "netfx"));
            File.WriteAllText(Path.Combine(extractRoot, "marker.txt"), "ok");

            var resolved = BinArtifactSupport.ResolveBinSourceRoot(extractRoot);
            Assert.That(resolved, Is.EqualTo(extractRoot));
        }

        [Test]
        public void ResolveBinSourceRoot_SingleNestedDir_Test() {
            var extractRoot = Path.Combine(_tempRoot, "extract-nested");
            var nested = Path.Combine(extractRoot, "payload");
            var nestedBin = Path.Combine(nested, "bin");
            Directory.CreateDirectory(nestedBin);
            File.WriteAllText(Path.Combine(nestedBin, "marker.txt"), "ok");

            var resolved = BinArtifactSupport.ResolveBinSourceRoot(extractRoot);
            Assert.That(resolved, Is.EqualTo(nestedBin));
        }

        [Test]
        public void BuildNuGetPackageVersion_Test() {
            var version = GithubNuGetBinAPI.BuildPackageVersion("abcdef1234567890abcdef1234567890abcdef12");
            Assert.That(version, Is.EqualTo("1.0.0-ci-abcdef1"));
        }

        [Test]
        public void SwapBinDirectory_ReplacesExistingBin_Test() {
            var clonePath = Path.Combine(_tempRoot, "clone-success");
            var existingBin = Path.Combine(clonePath, "bin");
            var newSource = Path.Combine(_tempRoot, "new-bin-source");

            Directory.CreateDirectory(existingBin);
            Directory.CreateDirectory(newSource);
            File.WriteAllText(Path.Combine(existingBin, "old.txt"), "old");
            File.WriteAllText(Path.Combine(newSource, "new.txt"), "new");

            BinArtifactSupport.SwapBinDirectory(clonePath, newSource);

            Assert.That(File.Exists(Path.Combine(existingBin, "old.txt")), Is.False);
            Assert.That(File.Exists(Path.Combine(existingBin, "new.txt")), Is.True);
            Assert.That(Directory.Exists(Path.Combine(clonePath, "bin.bak")), Is.False);
            Assert.That(Directory.Exists(Path.Combine(clonePath, "bin.new")), Is.False);
        }

        [Test]
        public void SwapBinDirectory_RestoresBackupOnFailure_Test() {
            var clonePath = Path.Combine(_tempRoot, "clone-failure");
            var existingBin = Path.Combine(clonePath, "bin");
            var lockedFile = Path.Combine(existingBin, "locked.txt");
            var badSource = Path.Combine(_tempRoot, "missing-source");

            Directory.CreateDirectory(existingBin);
            File.WriteAllText(lockedFile, "keep-me");

            try {
                BinArtifactSupport.SwapBinDirectory(clonePath, badSource);
                Assert.Fail("Expected swap to fail for missing source.");
            }
            catch (PyRevitException) {
                Assert.That(File.Exists(lockedFile), Is.True);
                Assert.That(Directory.Exists(existingBin), Is.True);
            }
        }
    }
}
