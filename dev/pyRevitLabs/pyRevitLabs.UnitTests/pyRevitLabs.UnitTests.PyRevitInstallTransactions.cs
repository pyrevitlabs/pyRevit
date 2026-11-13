using System;
using System.IO;
using System.IO.Compression;

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
        public void DeleteInvalidClone_RemovesTheClonedPathAndLeavesTheSourceAlone() {
            var sourcePath = Path.Combine(_tempRoot, "source-repo");
            var clonedPath = Path.Combine(_tempRoot, "cloned-repo");
            Directory.CreateDirectory(sourcePath);
            Directory.CreateDirectory(clonedPath);
            File.WriteAllText(Path.Combine(sourcePath, "keep.txt"), "source");

            PyRevitExtensions.DeleteInvalidClone(clonedPath);

            Assert.IsFalse(Directory.Exists(clonedPath));
            Assert.IsTrue(File.Exists(Path.Combine(sourcePath, "keep.txt")));
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
