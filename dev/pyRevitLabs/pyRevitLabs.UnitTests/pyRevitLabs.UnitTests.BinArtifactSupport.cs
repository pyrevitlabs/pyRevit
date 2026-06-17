using System;
using System.IO;

using Microsoft.VisualStudio.TestTools.UnitTesting;
using pyRevitLabs.Common;

namespace pyRevitLabs.UnitTests.Common {
    [TestClass]
    public class BinArtifactSupportTests {
        private string _tempRoot;

        [TestInitialize]
        public void SetUp() {
            _tempRoot = Path.Combine(
                Path.GetTempPath(),
                string.Format("pyrevit-bin-support-{0}", Guid.NewGuid().ToString("N")));
            Directory.CreateDirectory(_tempRoot);
        }

        [TestCleanup]
        public void TearDown() {
            if (Directory.Exists(_tempRoot))
                CommonUtils.DeleteDirectory(_tempRoot, verbose: false);
        }

        [TestMethod]
        public void IsSupportedCiBinBranch_DevelopAndMaster_Test() {
            Assert.IsTrue(BinArtifactSupport.IsSupportedCiBinBranch("develop"));
            Assert.IsTrue(BinArtifactSupport.IsSupportedCiBinBranch("master"));
            Assert.IsTrue(BinArtifactSupport.IsSupportedCiBinBranch("Develop"));
        }

        [TestMethod]
        public void IsSupportedCiBinBranch_OtherBranches_Test() {
            Assert.IsFalse(BinArtifactSupport.IsSupportedCiBinBranch("feature/foo"));
            Assert.IsFalse(BinArtifactSupport.IsSupportedCiBinBranch(null));
            Assert.IsFalse(BinArtifactSupport.IsSupportedCiBinBranch(string.Empty));
        }

        [TestMethod]
        public void GetReleaseDownloadRepos_ForkIncludesUpstream_Test() {
            var repos = BinArtifactSupport.GetReleaseDownloadRepos("myorg/pyRevit");
            Assert.AreEqual(2, repos.Count);
            Assert.AreEqual("myorg/pyRevit", repos[0]);
            Assert.AreEqual(PyRevitLabsConsts.OriginalRepoId, repos[1]);
        }

        [TestMethod]
        public void GetReleaseDownloadRepos_UpstreamOnly_Test() {
            var repos = BinArtifactSupport.GetReleaseDownloadRepos(PyRevitLabsConsts.OriginalRepoId);
            Assert.AreEqual(1, repos.Count);
            Assert.AreEqual(PyRevitLabsConsts.OriginalRepoId, repos[0]);
        }

        [TestMethod]
        public void ResolveBinSourceRoot_DirectBinWrapper_Test() {
            var extractRoot = Path.Combine(_tempRoot, "extract-direct");
            var binDir = Path.Combine(extractRoot, "bin");
            Directory.CreateDirectory(binDir);
            File.WriteAllText(Path.Combine(binDir, "marker.txt"), "ok");

            var resolved = BinArtifactSupport.ResolveBinSourceRoot(extractRoot);
            Assert.AreEqual(binDir, resolved);
        }

        [TestMethod]
        public void ResolveBinSourceRoot_FlatRoot_Test() {
            var extractRoot = Path.Combine(_tempRoot, "extract-flat");
            Directory.CreateDirectory(extractRoot);
            Directory.CreateDirectory(Path.Combine(extractRoot, "netfx"));
            File.WriteAllText(Path.Combine(extractRoot, "marker.txt"), "ok");

            var resolved = BinArtifactSupport.ResolveBinSourceRoot(extractRoot);
            Assert.AreEqual(extractRoot, resolved);
        }

        [TestMethod]
        public void ResolveBinSourceRoot_SingleNestedDir_Test() {
            var extractRoot = Path.Combine(_tempRoot, "extract-nested");
            var nested = Path.Combine(extractRoot, "payload");
            var nestedBin = Path.Combine(nested, "bin");
            Directory.CreateDirectory(nestedBin);
            File.WriteAllText(Path.Combine(nestedBin, "marker.txt"), "ok");

            var resolved = BinArtifactSupport.ResolveBinSourceRoot(extractRoot);
            Assert.AreEqual(nestedBin, resolved);
        }

        [TestMethod]
        public void BuildNuGetPackageVersion_Test() {
            var version = GithubNuGetBinAPI.BuildPackageVersion("abcdef1234567890abcdef1234567890abcdef12");
            Assert.AreEqual("1.0.0-ci-abcdef1", version);
        }

        [TestMethod]
        public void SwapBinDirectory_ReplacesExistingBin_Test() {
            var clonePath = Path.Combine(_tempRoot, "clone-success");
            var existingBin = Path.Combine(clonePath, "bin");
            var newSource = Path.Combine(_tempRoot, "new-bin-source");

            Directory.CreateDirectory(existingBin);
            Directory.CreateDirectory(newSource);
            File.WriteAllText(Path.Combine(existingBin, "old.txt"), "old");
            File.WriteAllText(Path.Combine(newSource, "new.txt"), "new");

            BinArtifactSupport.SwapBinDirectory(clonePath, newSource);

            Assert.IsFalse(File.Exists(Path.Combine(existingBin, "old.txt")));
            Assert.IsTrue(File.Exists(Path.Combine(existingBin, "new.txt")));
            Assert.IsFalse(Directory.Exists(Path.Combine(clonePath, "bin.bak")));
            Assert.IsFalse(Directory.Exists(Path.Combine(clonePath, "bin.new")));
        }

        [TestMethod]
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
                Assert.IsTrue(File.Exists(lockedFile));
                Assert.IsTrue(Directory.Exists(existingBin));
            }
        }
    }
}
