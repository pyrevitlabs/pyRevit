using System;
using System.IO;
using System.IO.Compression;

using LibGit2Sharp;
using Microsoft.VisualStudio.TestTools.UnitTesting;

using pyRevitLabs.Common;
using pyRevitLabs.Common.Extensions;
using pyRevitLabs.Configurations.Ini;
using pyRevitLabs.PyRevit;

namespace pyRevitLabs.UnitTests {
    /// <summary>
    /// Regression tests for #4042: clone updates and extension installs must not lose data on failure.
    /// </summary>
    [TestClass]
    [TestCategory("HostFree")]
    [TestCategory("Integration")]
    public class PyRevitInstallTransactionTests {
        private const string CloneName = "TransactionTestClone";

        private string _tempRoot;
        private string _previousPyRevitPathOverride;
        private string _previousProgramDataPathOverride;

        [TestInitialize]
        public void Setup() {
            _tempRoot = Path.Combine(Path.GetTempPath(), "pyRevitInstallTx_" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(_tempRoot);
            _previousPyRevitPathOverride = Environment.GetEnvironmentVariable(PyRevitLabsConsts.PyRevitPathOverrideEnvVar);
            _previousProgramDataPathOverride = Environment.GetEnvironmentVariable(PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar);
            Environment.SetEnvironmentVariable(
                PyRevitLabsConsts.PyRevitPathOverrideEnvVar,
                Path.Combine(_tempRoot, "AppDataPyRevit"));
            Environment.SetEnvironmentVariable(
                PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar,
                Path.Combine(_tempRoot, "ProgramDataPyRevit"));
            PyRevitInstallScope.ClearCachedInstallScope();
            PyRevitInstallScope.SetRuntimeInstallRoot(null);
            PyRevitConfigService.Reload();
            Directory.CreateDirectory(PyRevitLabsConsts.PyRevitPath);
        }

        [TestCleanup]
        public void Cleanup() {
            PyRevitConfigService.Reload();
            PyRevitInstallScope.ClearCachedInstallScope();
            PyRevitInstallScope.SetRuntimeInstallRoot(null);
            Environment.SetEnvironmentVariable(
                PyRevitLabsConsts.PyRevitPathOverrideEnvVar,
                _previousPyRevitPathOverride);
            Environment.SetEnvironmentVariable(
                PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar,
                _previousProgramDataPathOverride);
            if (Directory.Exists(_tempRoot))
                CommonUtils.DeleteDirectory(_tempRoot);
        }

        [TestMethod]
        public void Update_WhenImageIsUnavailable_KeepsTheDeployedCloneAndItsRegistration() {
            var zipPath = Path.Combine(_tempRoot, "clone.zip");
            var clonePath = Path.Combine(_tempRoot, "cloneDest");
            CreateMinimalCloneZip(zipPath);
            PyRevitClones.DeployFromImage(
                cloneName: CloneName,
                imagePath: zipPath,
                destPath: clonePath,
                installBinaries: false);
            var sentinel = Path.Combine(clonePath, "sentinel.txt");
            File.WriteAllText(sentinel, "keep me");
            File.Delete(zipPath);

            var clone = PyRevitClones.GetRegisteredClone(CloneName);
            Assert.ThrowsException<PyRevitException>(
                () => PyRevitClones.Update(clone, credentials: null, skipBin: true));

            Assert.IsTrue(File.Exists(sentinel), "failed update must leave the deployed clone untouched");
            Assert.AreEqual(
                clonePath.NormalizeAsPath(),
                PyRevitClones.GetRegisteredClone(CloneName).ClonePath.NormalizeAsPath());
            CollectionAssert.AreEqual(
                new string[0],
                Directory.GetDirectories(_tempRoot, "cloneDest.update-backup-*"),
                "failed update must not leave its backup behind");
        }

        [TestMethod]
        public void RestoreClone_WhenTheFailedDeployCanNotBeRemoved_KeepsTheBackupAndDoesNotThrow() {
            var clonePath = Path.Combine(_tempRoot, "partialDest");
            var backupPath = Path.Combine(_tempRoot, "partialDest.update-backup-test");
            Directory.CreateDirectory(backupPath);
            File.WriteAllText(Path.Combine(backupPath, "previous.txt"), "previous clone");
            Directory.CreateDirectory(clonePath);
            var lockedFile = Path.Combine(clonePath, "locked.txt");

            using (new FileStream(lockedFile, FileMode.Create, FileAccess.ReadWrite, FileShare.None)) {
                PyRevitClones.RestoreClone(CloneName, clonePath, backupPath);
            }

            Assert.IsTrue(File.Exists(Path.Combine(backupPath, "previous.txt")), "backup must survive a failed restore");
        }

        [TestMethod]
        public void Update_WhenTheCloneFolderIsLocked_KeepsTheCloneAndItsRegistration() {
            var zipPath = Path.Combine(_tempRoot, "clone.zip");
            var clonePath = Path.Combine(_tempRoot, "cloneDest");
            CreateMinimalCloneZip(zipPath);
            PyRevitClones.DeployFromImage(
                cloneName: CloneName,
                imagePath: zipPath,
                destPath: clonePath,
                installBinaries: false);
            var lockedFile = Path.Combine(clonePath, "locked.txt");
            var clone = PyRevitClones.GetRegisteredClone(CloneName);

            using (new FileStream(lockedFile, FileMode.Create, FileAccess.ReadWrite, FileShare.None)) {
                Assert.ThrowsException<IOException>(
                    () => PyRevitClones.Update(clone, credentials: null, skipBin: true));
            }

            Assert.IsTrue(File.Exists(lockedFile));
            Assert.IsNotNull(PyRevitClones.GetRegisteredClone(CloneName));
            Assert.AreEqual(0, Directory.GetDirectories(_tempRoot, "cloneDest.update-backup-*").Length);
        }

        [TestMethod]
        public void Update_WhenImageIsAvailable_ReplacesTheCloneAndRemovesTheBackup() {
            var zipPath = Path.Combine(_tempRoot, "clone.zip");
            var clonePath = Path.Combine(_tempRoot, "cloneDest");
            CreateMinimalCloneZip(zipPath);
            PyRevitClones.DeployFromImage(
                cloneName: CloneName,
                imagePath: zipPath,
                destPath: clonePath,
                installBinaries: false);
            var sentinel = Path.Combine(clonePath, "sentinel.txt");
            File.WriteAllText(sentinel, "stale");

            var clone = PyRevitClones.GetRegisteredClone(CloneName);
            PyRevitClones.Update(clone, credentials: null, skipBin: true);

            Assert.IsFalse(File.Exists(sentinel), "successful update must deploy a fresh copy");
            Assert.IsTrue(Directory.Exists(Path.Combine(clonePath, "pyrevitlib", "pyrevit")));
            Assert.AreEqual(0, Directory.GetDirectories(_tempRoot, "cloneDest.update-backup-*").Length);
            Assert.IsNotNull(PyRevitClones.GetRegisteredClone(CloneName));
        }

        [TestMethod]
        public void ReplaceClone_WhenBinariesAreMissingForTheBranch_KeepsTheDeployedCloneAndDropsTheBackup() {
            var clonePath = Path.Combine(_tempRoot, "binlessDest");
            Directory.CreateDirectory(clonePath);
            File.WriteAllText(Path.Combine(clonePath, "previous.txt"), "previous clone");

            Assert.ThrowsException<pyRevitBinArtifactNotFoundException>(
                () => PyRevitClones.ReplaceClone(CloneName, clonePath, () => {
                    Directory.CreateDirectory(clonePath);
                    File.WriteAllText(Path.Combine(clonePath, "deployed.txt"), "new clone");
                    throw new pyRevitBinArtifactNotFoundException("no binaries");
                }));

            Assert.IsTrue(File.Exists(Path.Combine(clonePath, "deployed.txt")));
            Assert.IsFalse(File.Exists(Path.Combine(clonePath, "previous.txt")));
            Assert.AreEqual(0, Directory.GetDirectories(_tempRoot, "binlessDest.update-backup-*").Length);
        }

        [TestMethod]
        public void ReplaceClone_WhenTheRedeployFails_RestoresThePreviousClone() {
            var clonePath = Path.Combine(_tempRoot, "failedDest");
            Directory.CreateDirectory(clonePath);
            File.WriteAllText(Path.Combine(clonePath, "previous.txt"), "previous clone");

            Assert.ThrowsException<PyRevitException>(
                () => PyRevitClones.ReplaceClone(CloneName, clonePath, () => {
                    Directory.CreateDirectory(clonePath);
                    File.WriteAllText(Path.Combine(clonePath, "partial.txt"), "partial");
                    throw new PyRevitException("deploy failed");
                }));

            Assert.IsTrue(File.Exists(Path.Combine(clonePath, "previous.txt")));
            Assert.IsFalse(File.Exists(Path.Combine(clonePath, "partial.txt")));
            Assert.AreEqual(0, Directory.GetDirectories(_tempRoot, "failedDest.update-backup-*").Length);
        }

        [TestMethod]
        public void InstallExtension_WhenAlreadyInstalled_FailsWithAlreadyInstalledMessage() {
            var searchPath = Path.Combine(_tempRoot, "extensions");
            Directory.CreateDirectory(Path.Combine(searchPath, "Sample.extension"));
            PyRevitExtensions.RegisterExtensionSearchPath(searchPath);

            var ex = Assert.ThrowsException<PyRevitException>(
                () => PyRevitExtensions.InstallExtension(
                    "Sample",
                    PyRevitExtensionTypes.UIExtension,
                    Path.Combine(_tempRoot, "missing-source-repo"),
                    destPath: Path.Combine(_tempRoot, "elsewhere")));

            StringAssert.Contains(ex.Message, "already installed");
        }

        [TestMethod]
        public void InstallExtension_WhenOnlyALongerNameIsInstalled_DoesNotReportAlreadyInstalled() {
            var searchPath = Path.Combine(_tempRoot, "extensions");
            Directory.CreateDirectory(Path.Combine(searchPath, "MyTools.extension"));
            PyRevitExtensions.RegisterExtensionSearchPath(searchPath);

            var ex = Assert.ThrowsException<PyRevitException>(
                () => PyRevitExtensions.InstallExtension(
                    "Tools",
                    PyRevitExtensionTypes.UIExtension,
                    Path.Combine(_tempRoot, "missing-source-repo"),
                    destPath: Path.Combine(_tempRoot, "elsewhere")));

            Assert.IsFalse(ex.Message.Contains("already installed"), ex.Message);
        }

        [TestMethod]
        public void InstallExtension_WhenNameHasRegexMetacharacters_StillDetectsTheInstalledExtension() {
            var searchPath = Path.Combine(_tempRoot, "extensions");
            Directory.CreateDirectory(Path.Combine(searchPath, "C++.extension"));
            PyRevitExtensions.RegisterExtensionSearchPath(searchPath);

            var ex = Assert.ThrowsException<PyRevitException>(
                () => PyRevitExtensions.InstallExtension(
                    "C++",
                    PyRevitExtensionTypes.UIExtension,
                    Path.Combine(_tempRoot, "missing-source-repo"),
                    destPath: Path.Combine(_tempRoot, "elsewhere")));

            StringAssert.Contains(ex.Message, "already installed");
        }

        [TestMethod]
        public void InstallExtension_WhenNameDiffersOnlyInCase_FailsWithAlreadyInstalledMessage() {
            var searchPath = Path.Combine(_tempRoot, "extensions");
            Directory.CreateDirectory(Path.Combine(searchPath, "Sample.extension"));
            PyRevitExtensions.RegisterExtensionSearchPath(searchPath);

            var ex = Assert.ThrowsException<PyRevitException>(
                () => PyRevitExtensions.InstallExtension(
                    "SAMPLE",
                    PyRevitExtensionTypes.UIExtension,
                    Path.Combine(_tempRoot, "missing-source-repo"),
                    destPath: Path.Combine(_tempRoot, "elsewhere")));

            StringAssert.Contains(ex.Message, "already installed");
        }

        /// <summary>A malformed extension.json in an unrelated extension does not block an install.</summary>
        [TestMethod]
        public void InstallExtension_WhenAnUnrelatedExtensionHasMalformedMetadata_DoesNotReportAlreadyInstalled() {
            var searchPath = Path.Combine(_tempRoot, "extensions");
            var brokenPath = Path.Combine(searchPath, "Broken.extension");
            Directory.CreateDirectory(brokenPath);
            File.WriteAllText(Path.Combine(brokenPath, "extension.json"), "{ not valid json");
            PyRevitExtensions.RegisterExtensionSearchPath(searchPath);

            var ex = Assert.ThrowsException<PyRevitException>(
                () => PyRevitExtensions.InstallExtension(
                    "Sample",
                    PyRevitExtensionTypes.UIExtension,
                    Path.Combine(_tempRoot, "missing-source-repo"),
                    destPath: Path.Combine(_tempRoot, "elsewhere")));

            Assert.IsFalse(ex.Message.Contains("already installed"), ex.Message);
        }

        /// <summary>A malformed extension.json does not hide an installed extension of the same folder name.</summary>
        [TestMethod]
        public void InstallExtension_WhenTheSameNamedExtensionHasMalformedMetadata_StillReportsAlreadyInstalled() {
            var searchPath = Path.Combine(_tempRoot, "extensions");
            var brokenPath = Path.Combine(searchPath, "Sample.extension");
            Directory.CreateDirectory(brokenPath);
            File.WriteAllText(Path.Combine(brokenPath, "extension.json"), "{ not valid json");
            PyRevitExtensions.RegisterExtensionSearchPath(searchPath);

            var ex = Assert.ThrowsException<PyRevitException>(
                () => PyRevitExtensions.InstallExtension(
                    "Sample",
                    PyRevitExtensionTypes.UIExtension,
                    Path.Combine(_tempRoot, "missing-source-repo"),
                    destPath: Path.Combine(_tempRoot, "elsewhere")));

            StringAssert.Contains(ex.Message, "already installed");
        }

        [TestMethod]
        public void DeleteInvalidClone_RemovesTheClonedPathLeavesTheSourceAloneAndThrows() {
            var sourcePath = Path.Combine(_tempRoot, "source-repo");
            var clonedPath = Path.Combine(_tempRoot, "cloned-repo");
            Directory.CreateDirectory(sourcePath);
            Directory.CreateDirectory(clonedPath);
            File.WriteAllText(Path.Combine(sourcePath, "keep.txt"), "source");

            var ex = Assert.ThrowsException<PyRevitException>(
                () => PyRevitExtensions.DeleteInvalidClone(clonedPath, sourcePath));

            StringAssert.Contains(ex.Message, sourcePath);
            Assert.IsFalse(Directory.Exists(clonedPath));
            Assert.IsTrue(File.Exists(Path.Combine(sourcePath, "keep.txt")));
        }

        [TestMethod]
        public void InstallExtension_WhenCloneSucceeds_LeavesTheCloneFreeToDeleteRightAway() {
            var sourcePath = CreateLocalSourceRepo();
            var destPath = Path.Combine(_tempRoot, "extensions");
            Directory.CreateDirectory(destPath);

            PyRevitExtensions.InstallExtension(
                "LocalExt",
                PyRevitExtensionTypes.UIExtension,
                sourcePath,
                destPath: destPath);

            var clonedPath = Path.Combine(destPath, "LocalExt.extension");
            Assert.IsTrue(Directory.Exists(Path.Combine(clonedPath, ".git")));
            CommonUtils.DeleteDirectory(clonedPath);
            Assert.IsFalse(Directory.Exists(clonedPath));
        }

        private string CreateLocalSourceRepo() {
            var sourcePath = Path.Combine(_tempRoot, "local-source");
            Repository.Init(sourcePath);
            using (var repo = new Repository(sourcePath)) {
                repo.Refs.UpdateTarget("HEAD", "refs/heads/master");
                File.WriteAllText(Path.Combine(sourcePath, "readme.txt"), "extension");
                Commands.Stage(repo, "readme.txt");
                var author = new Signature("test", "test@example.com", DateTimeOffset.UtcNow);
                repo.Commit("init", author, author);
            }
            return sourcePath;
        }

        private static void CreateMinimalCloneZip(string zipPath) {
            var root = Path.Combine(Path.GetDirectoryName(zipPath), "zipcontent");
            if (Directory.Exists(root))
                Directory.Delete(root, recursive: true);
            Directory.CreateDirectory(Path.Combine(root, "bin"));
            Directory.CreateDirectory(Path.Combine(root, "pyrevitlib", "pyrevit"));
            Directory.CreateDirectory(Path.Combine(root, "site-packages"));
            File.WriteAllText(
                Path.Combine(root, "pyRevitfile"),
                "[deployments]\r\ncore = ['bin', 'pyrevitlib', 'site-packages', 'pyRevitfile']\r\n");
            if (File.Exists(zipPath))
                File.Delete(zipPath);
            ZipFile.CreateFromDirectory(root, zipPath);
            Directory.Delete(root, recursive: true);
        }
    }
}
