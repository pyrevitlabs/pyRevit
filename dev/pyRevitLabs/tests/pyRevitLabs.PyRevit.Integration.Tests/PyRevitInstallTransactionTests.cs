using System;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Security.AccessControl;
using System.Security.Principal;
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
                PyRevitClones.BinariesInstallHook = null;
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

        /// <summary>Retrying a clone that stopped on missing binaries resumes the kept folder, registers it and deletes nothing.</summary>
        [Test]
        public void DeployFromRepo_WhenRetriedAfterMissingBinaries_ResumesTheKeptClone() {
            var keptClone = CreateKeptClone(out var source, out var dest);
            var marker = Path.Combine(keptClone, "marker.txt");
            File.WriteAllText(marker, "keep me");
            var hookCalls = 0;
            string hookPath = null;
            string hookUrl = null;
            var hookMode = BinArtifactInstallMode.Update;
            string hookBranch = null;
            PyRevitClones.BinariesInstallHook = (path, url, mode, branch) => {
                hookCalls++;
                hookPath = path;
                hookUrl = url;
                hookMode = mode;
                hookBranch = branch;
            };
            PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: dest);

            Assert.That(hookCalls, Is.EqualTo(1));
            Assert.That(hookPath.NormalizeAsPath(), Is.EqualTo(keptClone.NormalizeAsPath()));
            Assert.That(hookUrl, Is.EqualTo(source));
            Assert.That(hookMode, Is.EqualTo(BinArtifactInstallMode.Clone));
            Assert.That(hookBranch, Is.EqualTo(PyRevitLabsConsts.TargetBranch));
            Assert.That(File.Exists(marker), Is.True, "resume must not delete anything in the kept folder");
            Assert.That(Repository.IsValid(keptClone), Is.True);
            Assert.That(
                PyRevitClones.GetRegisteredClone(CloneName).ClonePath.NormalizeAsPath(),
                Is.EqualTo(keptClone.NormalizeAsPath()));
        }

        /// <summary>A kept folder that already has built binaries is registered without installing binaries over its build.</summary>
        [Test]
        public void DeployFromRepo_WhenTheKeptFolderHasBuiltBinaries_RegistersItWithoutInstallingBinaries() {
            var keptClone = CreateKeptClone(out var source, out var dest);
            var localBuild = Path.Combine(keptClone, "bin", "netfx", "engines", "local-build.txt");
            Directory.CreateDirectory(Path.GetDirectoryName(localBuild));
            File.WriteAllText(localBuild, "built locally");
            PyRevitClones.BinariesInstallHook = (path, url, mode, branch) => throw new InvalidOperationException("binaries must not be installed");

            PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: dest);

            Assert.That(File.Exists(localBuild), Is.True);
            Assert.That(
                PyRevitClones.GetRegisteredClone(CloneName).ClonePath.NormalizeAsPath(),
                Is.EqualTo(keptClone.NormalizeAsPath()));
        }

        /// <summary>The install runs only when bin, bin.bak and bin.new are all empty or missing, since it replaces bin and deletes the other two; anything else is kept and the folder is only registered.</summary>
        [TestCase("bin.bak", "old.dll", false)]
        [TestCase("bin.new", "user-staging.dll", false)]
        [TestCase("bin.new", null, true)]
        [TestCase("bin.bak", null, true)]
        [TestCase("bin", null, true)]
        [TestCase("bin/netfx/engines", null, true)]
        [TestCase("bin/netfx", "pyrevit.exe", false)]
        public void DeployFromRepo_WhenTheKeptFolderHasLocalBinContent_InstallsOnlyWhenThereIsNone(
            string folder,
            string file,
            bool installExpected) {
            var keptClone = CreateKeptClone(out var source, out var dest);
            var folderPath = Path.Combine(keptClone, folder);
            Directory.CreateDirectory(folderPath);
            var filePath = file == null ? null : Path.Combine(folderPath, file);
            if (filePath != null)
                File.WriteAllText(filePath, "local");
            var hookCalls = 0;
            PyRevitClones.BinariesInstallHook = (path, url, mode, branch) => hookCalls++;

            PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: dest);

            Assert.That(hookCalls, Is.EqualTo(installExpected ? 1 : 0));
            if (!installExpected)
                Assert.That(File.Exists(filePath), Is.True);
            Assert.That(PyRevitClones.GetRegisteredClone(CloneName), Is.Not.Null);
        }

        /// <summary>A kept branch that tracks another local branch has no remote upstream and is refused.</summary>
        [Test]
        public void DeployFromRepo_WhenTheKeptBranchTracksALocalBranch_Refuses() {
            var keptClone = CreateKeptClone(out var source, out var dest);
            using (var repo = new Repository(keptClone)) {
                var localBranch = repo.CreateBranch("local-upstream", repo.Head.Tip);
                repo.Branches.Update(repo.Head, branch => branch.TrackedBranch = localBranch.CanonicalName);
            }
            PyRevitClones.BinariesInstallHook = (path, url, mode, branch) => throw new InvalidOperationException("binaries must not be installed");

            var ex = Assert.Throws<PyRevitException>(
                () => PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: dest));

            Assert.That(ex.Message, Does.Contain("does not track an existing remote branch"));
            Assert.That(GitInstaller.HasTrackingBranch(keptClone), Is.False);
        }

        /// <summary>A kept git folder that is not a valid pyRevit clone is refused up front and the hint does not offer a resume.</summary>
        [Test]
        public void DeployFromRepo_WhenTheKeptFolderIsNotAValidPyRevitClone_RefusesAndDoesNotOfferAResume() {
            var keptClone = CreateKeptClone(out var source, out var dest);
            Directory.Delete(Path.Combine(keptClone, "pyrevitlib", "pyrevit"), recursive: true);
            using (var repo = new Repository(keptClone))
                Commands.Stage(repo, "*");
            PyRevitClones.BinariesInstallHook = (path, url, mode, branch) => throw new InvalidOperationException("binaries must not be installed");

            var ex = Assert.Throws<PyRevitException>(
                () => PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: dest));

            Assert.That(ex.Message, Does.Contain("not a valid pyRevit clone"));
            Assert.That(
                PyRevitClones.DescribeKeptFolderRecovery(keptClone, source, PyRevitLabsConsts.TargetBranch, CloneName),
                Does.Not.Contain("resumes"));
        }

        /// <summary>A kept clone nested in another valid clone is judged on its own folder, so an invalid inner clone is not accepted through its parent.</summary>
        [Test]
        public void DeployFromRepo_WhenTheInvalidKeptCloneIsInsideAValidClone_RefusesAndDoesNotOfferAResume() {
            var outerSource = CreateSourceRepo("outerSource");
            var outerDest = Path.Combine(_tempRoot, "outerDest");
            PyRevitClones.DeployFromRepo("OuterClone", repoUrl: outerSource, destPath: outerDest, installBinaries: false);
            var nestedDest = Path.Combine(outerDest, "OuterClone", "nested");
            var keptClone = CreateKeptClone(out var source, out var dest, nestedDest);
            Directory.Delete(Path.Combine(keptClone, "pyrevitlib", "pyrevit"), recursive: true);
            using (var repo = new Repository(keptClone))
                Commands.Stage(repo, "*");
            PyRevitClones.BinariesInstallHook = (path, url, mode, branch) => throw new InvalidOperationException("binaries must not be installed");

            var ex = Assert.Throws<PyRevitException>(
                () => PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: dest));

            Assert.That(ex.Message, Does.Contain("not a valid pyRevit clone"));
            Assert.That(
                PyRevitClones.DescribeKeptFolderRecovery(keptClone, source, PyRevitLabsConsts.TargetBranch, CloneName),
                Does.Not.Contain("resumes"));
        }

        /// <summary>A name registered at an inner clone that now opens only through its valid parent still blocks the resume, so the registration is not moved.</summary>
        [Test]
        public void DeployFromRepo_WhenTheNameIsRegisteredAtAnInnerCloneOpenedThroughItsParent_RefusesAndKeepsIt() {
            var source = CreateSourceRepo();
            var keptDest = Path.Combine(_tempRoot, "keptDest");
            PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: keptDest, installBinaries: false);
            PyRevitClones.UnregisterClone(PyRevitClones.GetRegisteredClone(CloneName));
            var outerDest = Path.Combine(_tempRoot, "outerDest");
            PyRevitClones.DeployFromRepo("OuterClone", repoUrl: source, destPath: outerDest, installBinaries: false);
            var innerDest = Path.Combine(outerDest, "OuterClone", "nested");
            PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: innerDest, installBinaries: false);
            PyRevitClones.UnregisterClone(PyRevitClones.GetRegisteredClone("OuterClone"));
            Directory.Delete(Path.Combine(innerDest, CloneName, "pyrevitlib", "pyrevit"), recursive: true);

            var ex = Assert.Throws<PyRevitException>(
                () => PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: keptDest, installBinaries: false));

            Assert.That(ex.Message, Does.Contain("already registered at"));
            var kept = Path.Combine(keptDest, CloneName).NormalizeAsPath();
            Assert.That(
                PyRevitClones.GetRegisteredClones(pruneStoredList: false)
                    .Any(clone => clone.ClonePath.IsSamePathAs(kept)),
                Is.False);
        }

        /// <summary>A name stored at an inner clone is still seen while its valid parent stays registered, although the registry omits the duplicate path.</summary>
        [Test]
        public void DeployFromRepo_WhenTheParentCloneStaysRegisteredAndTheInnerNameIsHidden_RefusesAndKeepsIt() {
            var source = CreateSourceRepo();
            var keptDest = Path.Combine(_tempRoot, "keptDest");
            PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: keptDest, installBinaries: false);
            PyRevitClones.UnregisterClone(PyRevitClones.GetRegisteredClone(CloneName));
            var outerDest = Path.Combine(_tempRoot, "outerDest");
            PyRevitClones.DeployFromRepo("OuterClone", repoUrl: source, destPath: outerDest, installBinaries: false);
            var innerDest = Path.Combine(outerDest, "OuterClone", "nested");
            PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: innerDest, installBinaries: false);
            Directory.Delete(Path.Combine(innerDest, CloneName, "pyrevitlib", "pyrevit"), recursive: true);

            var ex = Assert.Throws<PyRevitException>(
                () => PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: keptDest, installBinaries: false));

            Assert.That(ex.Message, Does.Contain("already registered at"));
            Assert.That(ex.Message, Does.Contain("not listed"));
            Assert.That(ex.Message, Does.Contain("--force"));
            Assert.That(ex.Message, Does.Not.Contain("clones forget"));
            Assert.That(PyRevitClones.GetRegisteredClone("OuterClone"), Is.Not.Null);

            var kept = Path.Combine(keptDest, CloneName);
            PyRevitClones.RegisterClone(CloneName, kept, forceUpdate: true);
            Assert.That(
                PyRevitClones.GetRegisteredClone(CloneName).ClonePath.NormalizeAsPath(),
                Is.EqualTo(kept.NormalizeAsPath()));
            Assert.That(PyRevitClones.GetRegisteredClone("OuterClone"), Is.Not.Null);
        }

        /// <summary>The same-name check reads the saved registrations before the cleanup of a missing unrelated clone can drop a hidden name.</summary>
        [Test]
        public void DeployFromRepo_WhenAnUnrelatedCloneFolderIsMissing_StillSeesTheHiddenSavedName() {
            var source = CreateSourceRepo();
            var keptDest = Path.Combine(_tempRoot, "keptDest");
            PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: keptDest, installBinaries: false);
            PyRevitClones.UnregisterClone(PyRevitClones.GetRegisteredClone(CloneName));
            var unrelatedDest = Path.Combine(_tempRoot, "unrelatedDest");
            PyRevitClones.DeployFromRepo("UnrelatedClone", repoUrl: source, destPath: unrelatedDest, installBinaries: false);
            var outerDest = Path.Combine(_tempRoot, "outerDest");
            PyRevitClones.DeployFromRepo("OuterClone", repoUrl: source, destPath: outerDest, installBinaries: false);
            var innerDest = Path.Combine(outerDest, "OuterClone", "nested");
            PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: innerDest, installBinaries: false);
            Directory.Delete(Path.Combine(innerDest, CloneName, "pyrevitlib", "pyrevit"), recursive: true);
            FixtureDirectory.Delete(Path.Combine(unrelatedDest, "UnrelatedClone"));

            var ex = Assert.Throws<PyRevitException>(
                () => PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: keptDest, installBinaries: false));

            Assert.That(ex.Message, Does.Contain("already registered at"));
        }

        /// <summary>Recovery commands in the messages quote a clone name that contains spaces, so they can be copied into a shell.</summary>
        [Test]
        public void DeployFromRepo_WhenTheCloneNameHasSpaces_TheRecoveryCommandsQuoteIt() {
            const string spacedName = "My Dev Clone";
            var source = CreateSourceRepo();
            var keptDest = Path.Combine(_tempRoot, "keptDest");
            var otherDest = Path.Combine(_tempRoot, "otherDest");
            PyRevitClones.DeployFromRepo(spacedName, repoUrl: source, destPath: keptDest, installBinaries: false);
            var registered = Assert.Throws<PyRevitException>(
                () => PyRevitClones.DeployFromRepo(spacedName, repoUrl: source, destPath: keptDest, installBinaries: false));
            Assert.That(registered.Message, Does.Contain("clones update \"My Dev Clone\""));

            PyRevitClones.UnregisterClone(PyRevitClones.GetRegisteredClone(spacedName));
            PyRevitClones.DeployFromRepo(spacedName, repoUrl: source, destPath: otherDest, installBinaries: false);
            var listed = Assert.Throws<PyRevitException>(
                () => PyRevitClones.DeployFromRepo(spacedName, repoUrl: source, destPath: keptDest, installBinaries: false));
            Assert.That(listed.Message, Does.Contain("clones forget \"My Dev Clone\""));
        }

        /// <summary>The replace command for an unlisted blocking name quotes both the name and the folder.</summary>
        [Test]
        public void DeployFromRepo_WhenAnUnlistedNameHasSpaces_TheReplaceCommandQuotesNameAndFolder() {
            const string spacedName = "My Dev Clone";
            var source = CreateSourceRepo();
            var keptDest = Path.Combine(_tempRoot, "keptDest");
            PyRevitClones.DeployFromRepo(spacedName, repoUrl: source, destPath: keptDest, installBinaries: false);
            PyRevitClones.UnregisterClone(PyRevitClones.GetRegisteredClone(spacedName));
            var outerDest = Path.Combine(_tempRoot, "outerDest");
            PyRevitClones.DeployFromRepo("OuterClone", repoUrl: source, destPath: outerDest, installBinaries: false);
            var innerDest = Path.Combine(outerDest, "OuterClone", "nested");
            PyRevitClones.DeployFromRepo(spacedName, repoUrl: source, destPath: innerDest, installBinaries: false);
            Directory.Delete(Path.Combine(innerDest, spacedName, "pyrevitlib", "pyrevit"), recursive: true);

            var ex = Assert.Throws<PyRevitException>(
                () => PyRevitClones.DeployFromRepo(spacedName, repoUrl: source, destPath: keptDest, installBinaries: false));

            Assert.That(ex.Message, Does.Contain("clones add \"My Dev Clone\" \""));
        }

        /// <summary>A resume with --skip-bin registers the folder without scanning bin, even when a build folder cannot be listed.</summary>
        [Test]
        public void DeployFromRepo_WhenResumingWithSkipBin_RegistersWithoutInstalling() {
            var keptClone = CreateKeptClone(out var source, out var dest);
            var build = Path.Combine(keptClone, "bin", "netfx", "pyrevit.exe");
            Directory.CreateDirectory(Path.GetDirectoryName(build));
            File.WriteAllText(build, "local");
            PyRevitClones.BinariesInstallHook = (path, url, mode, branch) => throw new InvalidOperationException("binaries must not be installed");
            var binInfo = new DirectoryInfo(Path.Combine(keptClone, "bin"));
            var denyListing = new FileSystemAccessRule(
                WindowsIdentity.GetCurrent().User,
                FileSystemRights.ListDirectory,
                AccessControlType.Deny);
            var security = binInfo.GetAccessControl();
            security.AddAccessRule(denyListing);
            binInfo.SetAccessControl(security);

            try {
                PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: dest, installBinaries: false);
            }
            finally {
                security = binInfo.GetAccessControl();
                security.RemoveAccessRule(denyListing);
                binInfo.SetAccessControl(security);
            }

            Assert.That(File.Exists(build), Is.True);
            Assert.That(PyRevitClones.GetRegisteredClone(CloneName), Is.Not.Null);
        }

        /// <summary>A kept folder whose remote branch ref is gone is refused instead of throwing, and the tracking helpers treat it as untracked.</summary>
        [Test]
        public void DeployFromRepo_WhenTheTrackedRemoteRefIsGone_RefusesWithoutThrowingFromGit() {
            var keptClone = CreateKeptClone(out var source, out var dest);
            using (var repo = new Repository(keptClone))
                repo.Refs.Remove("refs/remotes/origin/master");
            PyRevitClones.BinariesInstallHook = (path, url, mode, branch) => throw new InvalidOperationException("binaries must not be installed");

            var ex = Assert.Throws<PyRevitException>(
                () => PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: dest));

            Assert.That(ex.Message, Does.Contain("does not track an existing remote branch"));
            Assert.That(GitInstaller.HasTrackingBranch(keptClone), Is.False);
            Assert.That(GitInstaller.IsLocalAheadOfTrackingBranch(keptClone), Is.False);
            Assert.That(GitInstaller.IsSyncedWithTrackingBranch(keptClone), Is.True);
        }

        /// <summary>A clone interrupted before its checkout finished is refused, while modified and untracked files do not count as incomplete.</summary>
        [Test]
        public void DeployFromRepo_WhenTheCheckoutIsIncomplete_RefusesAndTolerantOfLocalEdits() {
            var source = CreateSourceRepo();
            var dest = Path.Combine(_tempRoot, "repoDest");
            var keptClone = Path.Combine(dest, CloneName);
            Repository.Clone(source, keptClone, new CloneOptions { Checkout = false });
            PyRevitClones.BinariesInstallHook = (path, url, mode, branch) => { };

            var ex = Assert.Throws<PyRevitException>(
                () => PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: dest));

            Assert.That(ex.Message, Does.Contain("checkout is incomplete"));
            Assert.That(ex.Message, Does.Contain("Move the folder aside"));
            Assert.That(GitInstaller.HasCompleteWorkingTree(keptClone), Is.False);
            using (var repo = new Repository(keptClone))
                Commands.Checkout(repo, repo.Head, new CheckoutOptions { CheckoutModifiers = CheckoutModifiers.Force });
            File.AppendAllText(Path.Combine(keptClone, "pyRevitfile"), "edited");
            File.WriteAllText(Path.Combine(keptClone, "untracked.txt"), "untracked");

            PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: dest);

            Assert.That(PyRevitClones.GetRegisteredClone(CloneName), Is.Not.Null);
        }

        /// <summary>The recovery hint offers a resume only when the kept folder would be accepted.</summary>
        [Test]
        public void DescribeKeptFolderRecovery_OffersAResumeOnlyWhenTheFolderQualifies() {
            var keptClone = CreateKeptClone(out var source, out _);
            var branch = PyRevitLabsConsts.TargetBranch;

            Assert.That(
                PyRevitClones.DescribeKeptFolderRecovery(keptClone, source, branch, CloneName),
                Does.Contain("resumes"));

            var otherDest = Path.Combine(_tempRoot, "otherDest");
            PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: otherDest, installBinaries: false);

            var hint = PyRevitClones.DescribeKeptFolderRecovery(keptClone, source, branch, CloneName);
            Assert.That(hint, Does.Contain("cannot be resumed"));
            Assert.That(hint, Does.Not.Contain("resumes"));
            using (var repo = new Repository(keptClone))
                Commands.Checkout(repo, repo.Head.Tip);
            PyRevitClones.UnregisterClone(PyRevitClones.GetRegisteredClone(CloneName));
            Assert.That(
                PyRevitClones.DescribeKeptFolderRecovery(keptClone, source, branch, CloneName),
                Does.Contain("detached"));
        }

        /// <summary>A folder registered at this path that is no longer a valid clone gets advice that works: deleting it drops the stale registration.</summary>
        [Test]
        public void DeployFromRepo_WhenTheFolderIsRegisteredButNoLongerAClone_AdvisesDeletingItAndThatWorks() {
            var source = CreateSourceRepo();
            var dest = Path.Combine(_tempRoot, "repoDest");
            var folder = Path.Combine(dest, CloneName);
            PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: dest, installBinaries: false);
            Directory.Delete(Path.Combine(folder, "pyrevitlib", "pyrevit"), recursive: true);

            var ex = Assert.Throws<PyRevitException>(
                () => PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: dest, installBinaries: false));

            Assert.That(ex.Message, Does.Contain("no longer a valid clone"));
            Assert.That(ex.Message, Does.Contain("Move the folder aside"));
            Assert.That(ex.Message, Does.Not.Contain("clones forget"));
            Assert.That(ex.Message, Does.Not.Contain("not a registered clone"));
            FixtureDirectory.Delete(folder);
            PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: dest, installBinaries: false);
            Assert.That(PyRevitClones.GetRegisteredClone(CloneName), Is.Not.Null);
        }

        /// <summary>A resumed clone that fails for a reason other than missing binaries keeps its folder and registers nothing.</summary>
        [Test]
        public void DeployFromRepo_WhenTheResumeFailsForAnotherReason_KeepsTheFolderAndRegistersNothing() {
            var keptClone = CreateKeptClone(out var source, out var dest);
            var marker = Path.Combine(keptClone, "marker.txt");
            File.WriteAllText(marker, "keep me");
            PyRevitClones.BinariesInstallHook = (path, url, mode, branch) => throw new InvalidOperationException("boom");

            Assert.Throws<PyRevitException>(
                () => PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: dest));

            Assert.That(File.Exists(marker), Is.True);
            Assert.That(Repository.IsValid(keptClone), Is.True);
            Assert.That(PyRevitClones.GetRegisteredClones(pruneStoredList: false), Is.Empty);
        }

        /// <summary>A kept folder whose branch has no upstream is not resumed, since local commits could not be detected.</summary>
        [Test]
        public void DeployFromRepo_WhenTheKeptBranchHasNoUpstream_Refuses() {
            var keptClone = CreateKeptClone(out var source, out var dest);
            using (var repo = new Repository(keptClone)) {
                repo.Config.Unset("branch.master.remote");
                repo.Config.Unset("branch.master.merge");
            }
            PyRevitClones.BinariesInstallHook = (path, url, mode, branch) => throw new InvalidOperationException("binaries must not be installed");

            var ex = Assert.Throws<PyRevitException>(
                () => PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: dest));

            Assert.That(ex.Message, Does.Contain("does not track an existing remote branch"));
            Assert.That(PyRevitClones.GetRegisteredClones(pruneStoredList: false), Is.Empty);
        }

        /// <summary>A kept folder checked out at a commit instead of a branch is not resumed.</summary>
        [Test]
        public void DeployFromRepo_WhenTheKeptFolderHasADetachedHead_Refuses() {
            var keptClone = CreateKeptClone(out var source, out var dest);
            using (var repo = new Repository(keptClone))
                Commands.Checkout(repo, repo.Head.Tip);
            PyRevitClones.BinariesInstallHook = (path, url, mode, branch) => throw new InvalidOperationException("binaries must not be installed");

            var ex = Assert.Throws<PyRevitException>(
                () => PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: dest));

            Assert.That(ex.Message, Does.Contain("HEAD is detached"));
            Assert.That(ex.Message, Does.Not.Contain("(no branch)"));
            Assert.That(PyRevitClones.GetRegisteredClones(pruneStoredList: false), Is.Empty);
        }

        /// <summary>A kept folder with commits missing from its remote branch is not resumed, since the binaries would not match its code.</summary>
        [Test]
        public void DeployFromRepo_WhenTheKeptFolderHasLocalCommits_RefusesWithoutInstallingBinaries() {
            var source = CreateSourceRepo();
            var dest = Path.Combine(_tempRoot, "repoDest");
            var keptClone = Path.Combine(dest, CloneName);
            PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: dest, installBinaries: false);
            PyRevitClones.UnregisterClone(PyRevitClones.GetRegisteredClone(CloneName));
            using (var repo = new Repository(keptClone)) {
                File.WriteAllText(Path.Combine(keptClone, "local.txt"), "local work");
                Commands.Stage(repo, "local.txt");
                var author = new Signature("Test", "test@example.invalid", DateTimeOffset.UtcNow);
                repo.Commit("local", author, author);
            }
            PyRevitClones.BinariesInstallHook = (path, url, mode, branch) => throw new InvalidOperationException("binaries must not be installed");

            var ex = Assert.Throws<PyRevitException>(
                () => PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: dest));

            Assert.That(ex.Message, Does.Contain("local commits"));
            Assert.That(ex.Message, Does.Not.Contain(source));
            Assert.That(File.Exists(Path.Combine(keptClone, "local.txt")), Is.True);
            Assert.That(PyRevitClones.GetRegisteredClones(pruneStoredList: false), Is.Empty);
        }

        /// <summary>A same-name registration at a folder that is no longer a valid clone does not block the resume and is replaced, like a fresh clone replaces it.</summary>
        [Test]
        public void DeployFromRepo_WhenTheNameIsRegisteredAtAFolderThatIsNoLongerAClone_ResumesAndReplacesIt() {
            var source = CreateSourceRepo();
            var keptDest = Path.Combine(_tempRoot, "keptDest");
            var otherDest = Path.Combine(_tempRoot, "otherDest");
            PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: keptDest, installBinaries: false);
            PyRevitClones.UnregisterClone(PyRevitClones.GetRegisteredClone(CloneName));
            PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: otherDest, installBinaries: false);
            var otherClone = Path.Combine(otherDest, CloneName);
            Directory.Delete(Path.Combine(otherClone, "pyrevitlib", "pyrevit"), recursive: true);

            PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: keptDest, installBinaries: false);

            Assert.That(Directory.Exists(otherClone), Is.True);
            Assert.That(
                PyRevitClones.GetRegisteredClone(CloneName).ClonePath.NormalizeAsPath(),
                Is.EqualTo(Path.Combine(keptDest, CloneName).NormalizeAsPath()));
        }

        /// <summary>A kept folder whose origin differs from the requested source is not resumed and the error explains recovery.</summary>
        [Test]
        public void DeployFromRepo_WhenTheKeptFolderIsAnotherRemote_ThrowsWithRecoveryMessage() {
            var source = CreateSourceRepo();
            var otherSource = CreateSourceRepo("otherSource");
            var dest = Path.Combine(_tempRoot, "repoDest");
            PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: dest, installBinaries: false);
            PyRevitClones.UnregisterClone(PyRevitClones.GetRegisteredClone(CloneName));

            var ex = Assert.Throws<PyRevitException>(
                () => PyRevitClones.DeployFromRepo(CloneName, repoUrl: otherSource, destPath: dest, installBinaries: false));

            Assert.That(ex.Message, Does.Contain("not a registered clone"));
            Assert.That(ex.Message, Does.Contain(source));
            Assert.That(ex.Message, Does.Contain(otherSource));
            Assert.That(ex.Message, Does.Contain("Move the folder aside"));
            Assert.That(ex.Message, Does.Not.Contain("pyrevit clones update"));
            Assert.That(PyRevitClones.GetRegisteredClones(pruneStoredList: false), Is.Empty);
        }

        /// <summary>A leftover repo that has no origin remote gets the recovery message instead of a null reference error.</summary>
        [Test]
        public void DeployFromRepo_WhenTheKeptFolderHasNoOriginRemote_ThrowsWithRecoveryMessage() {
            var source = CreateSourceRepo();
            var dest = Path.Combine(_tempRoot, "repoDest");
            var leftover = Path.Combine(dest, CloneName);
            Directory.CreateDirectory(leftover);
            Repository.Init(leftover);
            using (var repository = new Repository(leftover))
                repository.Network.Remotes.Add("upstream", source);

            var ex = Assert.Throws<PyRevitException>(
                () => PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: dest, installBinaries: false));

            Assert.That(ex.Message, Does.Contain("not a registered clone"));
            Assert.That(ex.Message, Does.Contain("Move the folder aside"));
            Assert.That(ex.Message, Does.Not.Contain("pyrevit clones update"));
            Assert.That(Repository.IsValid(leftover), Is.True);
        }

        /// <summary>A kept clone checked out at another branch than the requested one is refused, not silently resumed.</summary>
        [Test]
        public void DeployFromRepo_WhenTheRequestedBranchDiffersFromTheKeptClone_Refuses() {
            var source = CreateSourceRepo();
            var dest = Path.Combine(_tempRoot, "repoDest");
            PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: dest, installBinaries: false);
            PyRevitClones.UnregisterClone(PyRevitClones.GetRegisteredClone(CloneName));

            var ex = Assert.Throws<PyRevitException>(
                () => PyRevitClones.DeployFromRepo(
                    CloneName,
                    branchName: "no-such-branch",
                    repoUrl: source,
                    destPath: dest,
                    installBinaries: false));

            Assert.That(ex.Message, Does.Contain("no-such-branch"));
            Assert.That(ex.Message, Does.Contain("pyrevit clones add"));
            Assert.That(PyRevitClones.GetRegisteredClones(pruneStoredList: false), Is.Empty);
        }

        /// <summary>A second clone into a folder that is already registered says so and points at update.</summary>
        [Test]
        public void DeployFromRepo_WhenTheFolderIsAlreadyRegistered_PointsAtUpdate() {
            var source = CreateSourceRepo();
            var dest = Path.Combine(_tempRoot, "repoDest");
            PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: dest, installBinaries: false);

            var ex = Assert.Throws<PyRevitException>(
                () => PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: dest, installBinaries: false));

            Assert.That(ex.Message, Does.Contain("already registered"));
            Assert.That(ex.Message, Does.Contain("pyrevit clones update \"" + CloneName + "\""));
            Assert.That(ex.Message, Does.Not.Contain("not a registered clone"));
        }

        /// <summary>When the resume fails again on missing binaries the kept folder, its files and its repo survive and nothing is registered.</summary>
        [Test]
        public void DeployFromRepo_WhenTheResumeFailsAgain_KeepsTheFolderAndRegistersNothing() {
            var keptClone = CreateKeptClone(out var source, out var dest);
            var marker = Path.Combine(keptClone, "marker.txt");
            File.WriteAllText(marker, "keep me");

            Assert.Throws<pyRevitBinArtifactNotFoundException>(
                () => PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: dest));

            Assert.That(File.Exists(marker), Is.True);
            Assert.That(Directory.Exists(Path.Combine(keptClone, ".git")), Is.True);
            Assert.That(Repository.IsValid(keptClone), Is.True);
            Assert.That(PyRevitClones.GetRegisteredClones(pruneStoredList: false), Is.Empty);
        }

        /// <summary>A kept clone switched to another branch is refused when no branch is requested, because the default branch would be installed.</summary>
        [Test]
        public void DeployFromRepo_WhenTheKeptCloneIsOnAnotherBranchThanTheDefault_Refuses() {
            var source = CreateSourceRepo();
            var dest = Path.Combine(_tempRoot, "repoDest");
            PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: dest, installBinaries: false);
            PyRevitClones.UnregisterClone(PyRevitClones.GetRegisteredClone(CloneName));
            using (var kept = new Repository(Path.Combine(dest, CloneName))) {
                var other = kept.CreateBranch("other-branch");
                Commands.Checkout(kept, other);
            }

            var ex = Assert.Throws<PyRevitException>(
                () => PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: dest, installBinaries: false));

            Assert.That(ex.Message, Does.Contain("other-branch"));
            Assert.That(ex.Message, Does.Contain(PyRevitLabsConsts.TargetBranch));
            Assert.That(PyRevitClones.GetRegisteredClones(pruneStoredList: false), Is.Empty);
        }

        /// <summary>A kept folder is not resumed when its clone name is registered at another path, so that registration is not re-pointed.</summary>
        [Test]
        public void DeployFromRepo_WhenTheCloneNameIsRegisteredElsewhere_RefusesAndKeepsTheRegistration() {
            var source = CreateSourceRepo();
            var keptDest = Path.Combine(_tempRoot, "keptDest");
            var otherDest = Path.Combine(_tempRoot, "otherDest");
            PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: keptDest, installBinaries: false);
            PyRevitClones.UnregisterClone(PyRevitClones.GetRegisteredClone(CloneName));
            PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: otherDest, installBinaries: false);

            var ex = Assert.Throws<PyRevitException>(
                () => PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: keptDest, installBinaries: false));

            Assert.That(ex.Message, Does.Contain("already registered at"));
            Assert.That(ex.Message, Does.Not.Contain("not a registered clone"));
            Assert.That(
                PyRevitClones.GetRegisteredClone(CloneName).ClonePath.NormalizeAsPath(),
                Is.EqualTo(Path.Combine(otherDest, CloneName).NormalizeAsPath()));

            PyRevitClones.UnregisterClone(PyRevitClones.GetRegisteredClone(CloneName));
            PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: keptDest, installBinaries: false);
            Assert.That(
                PyRevitClones.GetRegisteredClone(CloneName).ClonePath.NormalizeAsPath(),
                Is.EqualTo(Path.Combine(keptDest, CloneName).NormalizeAsPath()));
        }

        /// <summary>A deployment request is rejected as not implemented before anything is created, even for an existing folder.</summary>
        [Test]
        public void DeployFromRepo_WhenADeploymentNameIsGivenForAnExistingFolder_ThrowsNotImplemented() {
            var source = CreateSourceRepo();
            var dest = Path.Combine(_tempRoot, "repoDest");
            PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: dest, installBinaries: false);
            PyRevitClones.UnregisterClone(PyRevitClones.GetRegisteredClone(CloneName));

            Assert.Throws<NotImplementedException>(
                () => PyRevitClones.DeployFromRepo(CloneName, deploymentName: "core", repoUrl: source, destPath: dest));

            Assert.That(Repository.IsValid(Path.Combine(dest, CloneName)), Is.True);
        }

        /// <summary>A fresh clone that fails for a reason other than missing binaries is still deleted.</summary>
        [Test]
        public void DeployFromRepo_WhenAFreshCloneFailsForAnotherReason_DeletesTheClonedFolder() {
            var source = CreateSourceRepo();
            var dest = Path.Combine(_tempRoot, "repoDest");
            PyRevitClones.BinariesInstallHook = (path, url, mode, branch) => throw new InvalidOperationException("boom");

            Assert.Throws<PyRevitException>(
                () => PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: dest));

            Assert.That(Directory.Exists(Path.Combine(dest, CloneName)), Is.False);
            Assert.That(PyRevitClones.GetRegisteredClones(pruneStoredList: false), Is.Empty);
        }

        /// <summary>A destination containing braces does not turn the missing-binaries warning into a format error, for a fresh clone or a resume.</summary>
        [Test]
        public void DeployFromRepo_WhenTheDestinationHasBraces_StillReportsMissingBinaries() {
            var source = CreateSourceRepo();
            var dest = Path.Combine(_tempRoot, "dest{0}{x}");
            PyRevitClones.BinariesInstallHook = (path, url, mode, branch) => throw new pyRevitBinArtifactNotFoundException("no binaries");

            Assert.Throws<pyRevitBinArtifactNotFoundException>(
                () => PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: dest));
            Assert.Throws<pyRevitBinArtifactNotFoundException>(
                () => PyRevitClones.DeployFromRepo(CloneName, repoUrl: source, destPath: dest));
        }

        /// <summary>An image deploy into an existing folder is not resumed and the error says so and explains recovery.</summary>
        [Test]
        public void DeployFromImage_WhenTheDestinationExists_ThrowsWithRecoveryMessage() {
            var zipPath = Path.Combine(_tempRoot, "clone.zip");
            var dest = Path.Combine(_tempRoot, "imageDest");
            CreateMinimalCloneZip(zipPath);
            Directory.CreateDirectory(Path.Combine(dest, CloneName));

            var ex = Assert.Throws<PyRevitException>(
                () => PyRevitClones.DeployFromImage(CloneName, imagePath: zipPath, destPath: dest, installBinaries: false));

            Assert.That(ex.Message, Does.Contain("not a registered clone"));
            Assert.That(ex.Message, Does.Contain("not resumable"));
            Assert.That(ex.Message, Does.Contain("pyrevit clones add"));
        }

        private string CreateKeptClone(out string source, out string dest, string destRootPath = null) {
            var sourceRepo = CreateSourceRepo();
            var destRoot = destRootPath ?? Path.Combine(_tempRoot, "repoDest");
            source = sourceRepo;
            dest = destRoot;
            var keptClone = Path.Combine(destRoot, CloneName);
            PyRevitClones.BinariesInstallHook = (path, url, mode, branch) => throw new pyRevitBinArtifactNotFoundException("no binaries");
            Assert.Throws<pyRevitBinArtifactNotFoundException>(
                () => PyRevitClones.DeployFromRepo(CloneName, repoUrl: sourceRepo, destPath: destRoot));
            return keptClone;
        }

        private string CreateSourceRepo(string folderName = "source") {
            var source = Path.Combine(_tempRoot, folderName);
            Directory.CreateDirectory(Path.Combine(source, "pyrevitlib", "pyrevit"));
            File.WriteAllText(Path.Combine(source, "pyrevitlib", "pyrevit", "version"), "7.0.0");
            File.WriteAllText(Path.Combine(source, "pyRevitfile"), "[deployments]\r\ncore = ['pyrevitlib', 'pyRevitfile']\r\n");
            Repository.Init(source);
            using (var repository = new Repository(source)) {
                repository.Refs.UpdateTarget("HEAD", "refs/heads/master");
                Commands.Stage(repository, "*");
                var author = new Signature("Test", "test@example.invalid", DateTimeOffset.UtcNow);
                repository.Commit("fixture", author, author);
            }
            return source;
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
