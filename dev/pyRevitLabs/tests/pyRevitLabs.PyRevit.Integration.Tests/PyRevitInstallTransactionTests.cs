using System;
using System.IO;
using System.IO.Compression;
using LibGit2Sharp;
using NUnit.Framework;
using pyRevitLabs.Common;
using pyRevitLabs.Common.Extensions;
using pyRevitLabs.Configurations.Ini;
using pyRevitLabs.PyRevit;

namespace pyRevitLabs.PyRevit.Integration.Tests {
    /// <summary>
    /// Regression tests for #4042: clone updates and extension installs must not lose data on failure.
    /// </summary>
    [TestFixture]
    [FixtureLifeCycle(LifeCycle.InstancePerTestCase)]
    [NonParallelizable]
    [Category("HostFree")]
    [Category("Integration")]
    [Category("Regression")]
    public class PyRevitInstallTransactionTests {
        private const string CloneName = "TransactionTestClone";

        private string _tempRoot;
        private string _previousPyRevitPathOverride;
        private string _previousProgramDataPathOverride;

        /// <summary>Redirects pyRevit data folders to a temporary root.</summary>
        [SetUp]
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

        /// <summary>Restores environment overrides and the install scope, then deletes the temporary root.</summary>
        [TearDown]
        public void Cleanup() {
            try {
                PyRevitConfigService.Reload();
            }
            finally {
                PyRevitInstallScope.ClearCachedInstallScope();
                PyRevitInstallScope.SetRuntimeInstallRoot(null);
                Environment.SetEnvironmentVariable(
                    PyRevitLabsConsts.PyRevitPathOverrideEnvVar,
                    _previousPyRevitPathOverride);
                Environment.SetEnvironmentVariable(
                    PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar,
                    _previousProgramDataPathOverride);
                FixtureDirectory.Delete(_tempRoot);
            }
        }

        /// <summary>An update whose image is missing throws, leaves the deployed clone and its registration intact, and removes its backup.</summary>
        [Test]
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
            Assert.Throws<PyRevitException>(
                () => PyRevitClones.Update(clone, credentials: null, skipBin: true));

            Assert.That(File.Exists(sentinel), Is.True, "failed update must leave the deployed clone untouched");
            Assert.That(
                PyRevitClones.GetRegisteredClone(CloneName).ClonePath.NormalizeAsPath(),
                Is.EqualTo(clonePath.NormalizeAsPath()));
            Assert.That(
                Directory.GetDirectories(_tempRoot, "cloneDest.update-backup-*"),
                Is.Empty,
                "failed update must not leave its backup behind");
        }

        /// <summary>Restoring over a locked, partially deployed clone does not throw and keeps the backup.</summary>
        [Test]
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

            Assert.That(File.Exists(Path.Combine(backupPath, "previous.txt")), Is.True, "backup must survive a failed restore");
        }

        /// <summary>An update blocked by a locked file throws, keeps the clone and its registration, and leaves no backup.</summary>
        [Test]
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
                Assert.Throws<IOException>(
                    () => PyRevitClones.Update(clone, credentials: null, skipBin: true));
            }

            Assert.That(File.Exists(lockedFile), Is.True);
            Assert.That(PyRevitClones.GetRegisteredClone(CloneName), Is.Not.Null);
            Assert.That(Directory.GetDirectories(_tempRoot, "cloneDest.update-backup-*"), Is.Empty);
        }

        /// <summary>A successful update deploys a fresh copy, keeps the registration and removes the backup.</summary>
        [Test]
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

            Assert.That(File.Exists(sentinel), Is.False, "successful update must deploy a fresh copy");
            Assert.That(Directory.Exists(Path.Combine(clonePath, "pyrevitlib", "pyrevit")), Is.True);
            Assert.That(Directory.GetDirectories(_tempRoot, "cloneDest.update-backup-*"), Is.Empty);
            Assert.That(PyRevitClones.GetRegisteredClone(CloneName), Is.Not.Null);
        }

        /// <summary>Missing binaries for the branch keep the newly deployed clone instead of restoring the old one, and drop the backup.</summary>
        [Test]
        public void ReplaceClone_WhenBinariesAreMissingForTheBranch_KeepsTheDeployedCloneAndDropsTheBackup() {
            var clonePath = Path.Combine(_tempRoot, "binlessDest");
            Directory.CreateDirectory(clonePath);
            File.WriteAllText(Path.Combine(clonePath, "previous.txt"), "previous clone");

            Assert.Throws<pyRevitBinArtifactNotFoundException>(
                () => PyRevitClones.ReplaceClone(CloneName, clonePath, () => {
                    Directory.CreateDirectory(clonePath);
                    File.WriteAllText(Path.Combine(clonePath, "deployed.txt"), "new clone");
                    throw new pyRevitBinArtifactNotFoundException("no binaries");
                }));

            Assert.That(File.Exists(Path.Combine(clonePath, "deployed.txt")), Is.True);
            Assert.That(File.Exists(Path.Combine(clonePath, "previous.txt")), Is.False);
            Assert.That(Directory.GetDirectories(_tempRoot, "binlessDest.update-backup-*"), Is.Empty);
        }

        /// <summary>A failed redeploy removes the partial deploy, restores the previous clone and drops the backup.</summary>
        [Test]
        public void ReplaceClone_WhenTheRedeployFails_RestoresThePreviousClone() {
            var clonePath = Path.Combine(_tempRoot, "failedDest");
            Directory.CreateDirectory(clonePath);
            File.WriteAllText(Path.Combine(clonePath, "previous.txt"), "previous clone");

            Assert.Throws<PyRevitException>(
                () => PyRevitClones.ReplaceClone(CloneName, clonePath, () => {
                    Directory.CreateDirectory(clonePath);
                    File.WriteAllText(Path.Combine(clonePath, "partial.txt"), "partial");
                    throw new PyRevitException("deploy failed");
                }));

            Assert.That(File.Exists(Path.Combine(clonePath, "previous.txt")), Is.True);
            Assert.That(File.Exists(Path.Combine(clonePath, "partial.txt")), Is.False);
            Assert.That(Directory.GetDirectories(_tempRoot, "failedDest.update-backup-*"), Is.Empty);
        }

        /// <summary>Installing an extension whose folder already exists fails with an already-installed message.</summary>
        [Test]
        public void InstallExtension_WhenAlreadyInstalled_FailsWithAlreadyInstalledMessage() {
            var ex = InstallOverExistingExtension("Sample.extension", "Sample");

            Assert.That(ex.Message, Does.Contain("already installed"));
        }

        /// <summary>An installed extension whose name merely contains the requested name is not reported as already installed.</summary>
        [Test]
        public void InstallExtension_WhenOnlyALongerNameIsInstalled_DoesNotReportAlreadyInstalled() {
            var ex = InstallOverExistingExtension("MyTools.extension", "Tools");

            Assert.That(ex.Message, Does.Not.Contain("already installed"));
        }

        /// <summary>An extension name with regex metacharacters is matched literally and reported as already installed.</summary>
        [Test]
        public void InstallExtension_WhenNameHasRegexMetacharacters_StillDetectsTheInstalledExtension() {
            var ex = InstallOverExistingExtension("C++.extension", "C++");

            Assert.That(ex.Message, Does.Contain("already installed"));
        }

        /// <summary>The already-installed check ignores case.</summary>
        [Test]
        public void InstallExtension_WhenNameDiffersOnlyInCase_FailsWithAlreadyInstalledMessage() {
            var ex = InstallOverExistingExtension("Sample.extension", "SAMPLE");

            Assert.That(ex.Message, Does.Contain("already installed"));
        }

        /// <summary>A malformed extension.json in an unrelated extension does not block an install.</summary>
        [Test]
        public void InstallExtension_WhenAnUnrelatedExtensionHasMalformedMetadata_DoesNotReportAlreadyInstalled() {
            var ex = InstallOverExistingExtension("Broken.extension", "Sample", malformedMetadata: true);

            Assert.That(ex.Message, Does.Not.Contain("already installed"));
        }

        /// <summary>A malformed extension.json does not hide an installed extension of the same folder name.</summary>
        [Test]
        public void InstallExtension_WhenTheSameNamedExtensionHasMalformedMetadata_StillReportsAlreadyInstalled() {
            var ex = InstallOverExistingExtension("Sample.extension", "Sample", malformedMetadata: true);

            Assert.That(ex.Message, Does.Contain("already installed"));
        }

        /// <summary>Deleting an invalid clone removes the cloned folder, keeps the source, and throws naming the source.</summary>
        [Test]
        public void DeleteInvalidClone_RemovesTheClonedPathLeavesTheSourceAloneAndThrows() {
            var sourcePath = Path.Combine(_tempRoot, "source-repo");
            var clonedPath = Path.Combine(_tempRoot, "cloned-repo");
            Directory.CreateDirectory(sourcePath);
            Directory.CreateDirectory(clonedPath);
            File.WriteAllText(Path.Combine(sourcePath, "keep.txt"), "source");

            var ex = Assert.Throws<PyRevitException>(
                () => PyRevitExtensions.DeleteInvalidClone(clonedPath, sourcePath));

            Assert.That(ex.Message, Does.Contain(sourcePath));
            Assert.That(Directory.Exists(clonedPath), Is.False);
            Assert.That(File.Exists(Path.Combine(sourcePath, "keep.txt")), Is.True);
        }

        /// <summary>A successfully cloned extension holds no file locks, so it can be deleted right away.</summary>
        [Test]
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
            Assert.That(Directory.Exists(Path.Combine(clonedPath, ".git")), Is.True);
            CommonUtils.DeleteDirectory(clonedPath);
            Assert.That(Directory.Exists(clonedPath), Is.False);
        }

        private PyRevitException InstallOverExistingExtension(string installedFolder, string requestedName, bool malformedMetadata = false) {
            var searchPath = Path.Combine(_tempRoot, "extensions");
            var installedPath = Path.Combine(searchPath, installedFolder);
            Directory.CreateDirectory(installedPath);
            if (malformedMetadata)
                File.WriteAllText(Path.Combine(installedPath, "extension.json"), "{ not valid json");
            PyRevitExtensions.RegisterExtensionSearchPath(searchPath);

            return Assert.Throws<PyRevitException>(
                () => PyRevitExtensions.InstallExtension(
                    requestedName,
                    PyRevitExtensionTypes.UIExtension,
                    Path.Combine(_tempRoot, "missing-source-repo"),
                    destPath: Path.Combine(_tempRoot, "elsewhere")));
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
