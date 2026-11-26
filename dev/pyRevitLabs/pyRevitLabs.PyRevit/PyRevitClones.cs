using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Linq;

using pyRevitLabs.Common;
using pyRevitLabs.Common.Extensions;
using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Ini;
using pyRevitLabs.Configurations.Sections;
using pyRevitLabs.NLog;

namespace pyRevitLabs.PyRevit {
    public class pyRevitInvalidPyRevitCloneException : pyRevitInvalidGitCloneException {
        public pyRevitInvalidPyRevitCloneException() { }

        public pyRevitInvalidPyRevitCloneException(string invalidClonePath) : base(invalidClonePath) { }

        public override string Message {
            get {
                return string.Format("Path \"{0}\" is not a valid git pyRevit clone.", Path);
            }
        }
    }

    public static class PyRevitClones {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();
        private static readonly ConcurrentDictionary<string, string> reportedRejectedClones =
            new ConcurrentDictionary<string, string>(StringComparer.OrdinalIgnoreCase);

        /// <summary>
        /// Test seam that replaces the CI binaries install of a git clone: when set it runs instead of the
        /// download with the clone path, repository url, install mode and branch, so it throws to simulate
        /// missing binaries and returns to simulate success. Process-wide state: only non-parallel tests may
        /// set it, and they must reset it. Always null in production.
        /// </summary>
        internal static Action<string, string, BinArtifactInstallMode, string> BinariesInstallHook;

        // managing clones ===========================================================================================
        // clones are git clones. pyRevit module likes to know about available clones to
        // perform operations on (switching engines, clones, uninstalling, ...)

        // register a clone in a configs
        // @handled @logs
        public static void RegisterClone(string cloneName, string repoPath, bool forceUpdate = false) {
            var normalPath = repoPath.NormalizeAsPath();
            logger.Debug("Registering clone \"{0}\"", normalPath);

            WarnIfBinEnginesMissing(normalPath);

            var clone = new PyRevitClone(repoPath, name: cloneName);

            var registeredClones = GetRegisteredClones();

            if (forceUpdate) {
                registeredClones.RemoveAll(
                    registeredClone => registeredClone.Matches(cloneName) || registeredClone.Equals(clone));
            }
            else if (registeredClones.Contains(clone)) {
                throw new PyRevitException(
                    string.Format("Clone with repo path \"{0}\" already exists.", clone.ClonePath)
                    );
            }

            registeredClones.Add(clone);
            SaveRegisteredClones(registeredClones);
        }

        // renames a clone in a configs
        // @handled @logs
        public static void RenameClone(string cloneName, string newName) {
            logger.Debug("Renaming clone \"{0}\" to \"{1}\"", cloneName, newName);
            var renamed = false;
            var renamedClones = new List<PyRevitClone>();
            foreach (var clone in GetRegisteredClones()) {
                if (clone.Name == cloneName) {
                    clone.Rename(newName);
                    logger.Debug("Renamed clone \"{0}\" to \"{1}\"", cloneName, clone.Name);
                    renamed = true;
                }
                renamedClones.Add(clone);
            }
            if (renamed) {
                SaveRegisteredClones(renamedClones);
            }
        }

        // unregister a clone from configs
        // @handled @logs
        public static void UnregisterClone(PyRevitClone clone) {
            logger.Debug("Unregistering clone \"{0}\"", clone);

            // remove the clone path from list
            var clones = GetRegisteredClones();
            if (clones.Remove(clone)) {
                SaveRegisteredClones(clones);
            }
        }

        // unregister all clone from configs
        // @handled @logs
        public static void UnregisterAllClones() {
            logger.Debug("Unregistering all clones...");

            foreach (var clone in GetRegisteredClones())
                UnregisterClone(clone);
        }

        /// <summary>
        /// The nearest valid clone <paramref name="path"/> lies in, so a clone nested inside another
        /// registered clone is not mistaken for it. The registration of that clone is returned when there
        /// is one, to keep its name; a path that is inside no valid clone falls back to the registered
        /// clone containing it, or null.
        /// </summary>
        public static PyRevitClone FindContaining(string path) {
            var registeredClones = GetRegisteredClones(pruneStoredList: false);
            PyRevitClone nearest;
            try {
                nearest = new PyRevitClone(Path.GetDirectoryName(path));
            }
            catch (PyRevitException) {
                return registeredClones.FirstOrDefault(clone => path.IsPathWithin(clone.ClonePath));
            }
            var registered = registeredClones.FirstOrDefault(clone => clone.Equals(nearest));
            if (registered != null)
                return registered;
            try {
                return new PyRevitClone(nearest.ClonePath, name: new DirectoryInfo(nearest.ClonePath).Name);
            }
            catch (PyRevitException) {
                return new PyRevitClone(nearest.ClonePath);
            }
        }

        // return list of registered clones
        // @handled @logs
        public static List<PyRevitClone> GetRegisteredClones() {
            return GetRegisteredClones(pruneStoredList: true);
        }

        /// <summary>
        /// Returns the registered clones that pass verification.
        /// </summary>
        /// <param name="pruneStoredList">
        /// When false, registrations that fail verification are skipped but stay in the config, so a
        /// clone on an unavailable drive is not unregistered by a caller that only needs to read.
        /// </param>
        public static List<PyRevitClone> GetRegisteredClones(bool pruneStoredList) {
            // safely get clone list
            var cfg = PyRevitConfigs.GetConfigFile();
            var clonesDict = MergeMachineRegisteredClones(cfg, cfg.Environment.Clones);

            var validatedClones = new List<PyRevitClone>();
            if (clonesDict is null) {
                return validatedClones;
            }
            var listChanged = false;
            var duplicates = new List<PyRevitClone>();
            var registrationKeys = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            // verify all registered clones, protect against tampering
            foreach (var cloneKeyValue in clonesDict) {
                var clonePath = cloneKeyValue.Value.NormalizeAsPath();
                var registrationKey = cloneKeyValue.Key + "|" + clonePath;
                registrationKeys.Add(registrationKey);
                if (!CommonUtils.VerifyPath(clonePath)) {
                    listChanged = true;
                    continue;
                }
                if (clonePath != cloneKeyValue.Value) {
                    listChanged = true;
                }
                try {
                    var clone = CreateVerifiedClone(clonePath, cloneKeyValue.Key);
                    reportedRejectedClones.TryRemove(registrationKey, out _);
                    var existing = validatedClones.Find(c => c.Equals(clone));
                    if (existing is null) {
                        logger.Debug("Verified clone \"{0}={1}\"", clone.Name, clone.ClonePath);
                        validatedClones.Add(clone);
                    }
                    else {
                        logger.Debug("Clone \"{0}\" duplicates clone \"{1}\" at \"{2}\"",
                                     clone.Name, existing.Name, clone.ClonePath);
                        duplicates.Add(clone);
                    }
                }
                catch (Exception ex) {
                    var alreadyReported = reportedRejectedClones.TryGetValue(registrationKey, out var lastReason)
                                          && lastReason == ex.Message;
                    reportedRejectedClones[registrationKey] = ex.Message;
                    if (!alreadyReported)
                        logger.Warn("Registered clone \"{0}\" at \"{1}\" failed validation and is skipped | {2}",
                                    cloneKeyValue.Key, clonePath, ex.Message);
                }
            }
            foreach (var staleKey in reportedRejectedClones.Keys.Where(k => !registrationKeys.Contains(k)).ToList())
                reportedRejectedClones.TryRemove(staleKey, out _);
            if (listChanged && pruneStoredList) {
                foreach (var duplicate in duplicates)
                    logger.Info("Registered clone \"{0}\" points to the same path as clone \"{1}\" and is dropped from the clones list",
                                duplicate.Name, validatedClones.Find(c => c.Equals(duplicate)).Name);
                // rewrite the verified clones list back to config file
                try {
                    SaveRegisteredClones(validatedClones);
                }
                catch (Exception saveEx) {
                    // pruning is cache hygiene; a read must not fail because
                    // the active config can not be written (e.g. admin-locked)
                    logger.Debug("Could not prune registered clones list | {0}", saveEx.Message);
                }
            }
            return validatedClones;
        }

        private static PyRevitClone CreateVerifiedClone(string clonePath, string name) {
            try {
                return new PyRevitClone(clonePath, name: name);
            }
            catch (PyRevitException) {
                PyRevitClone.VerifyCloneValidity(clonePath);
                throw;
            }
        }

        // overlay the machine-wide clone registry of an all-users install on top of
        // the per-user config so seeded copies can not go stale when an admin
        // re-registers or moves clones
        private static Dictionary<string, string> MergeMachineRegisteredClones(
            IConfigurationService activeConfig,
            Dictionary<string, string> clonesDict) {
            if (!PyRevitInstallScope.IsAllUsersInstall())
                return clonesDict;

            var machineConfigPath = PyRevitConsts.AdminConfigFilePath;
            if (!CommonUtils.VerifyFile(machineConfigPath))
                return clonesDict;

            // active config already is the machine config; nothing to merge
            var activeConfigPath = activeConfig.Configuration.ConfigurationPath;
            if (activeConfigPath != null
                    && machineConfigPath.NormalizeAsPath().Equals(
                        activeConfigPath.NormalizeAsPath(),
                        StringComparison.OrdinalIgnoreCase))
                return clonesDict;

            Dictionary<string, string> machineClones = null;
            try {
                var machineConfig = IniConfiguration.Create(machineConfigPath, readOnly: true);
                if (machineConfig.HasSectionKey(
                        PyRevitConsts.EnvConfigsSectionName,
                        PyRevitConsts.EnvConfigsInstalledClonesKey))
                    machineClones = machineConfig.GetValue<Dictionary<string, string>>(
                        PyRevitConsts.EnvConfigsSectionName,
                        PyRevitConsts.EnvConfigsInstalledClonesKey);
            }
            catch (Exception readEx) {
                logger.Debug("Could not read machine-wide clone registry | {0}", readEx.Message);
            }

            if (machineClones is null || machineClones.Count == 0)
                return clonesDict;

            var merged = clonesDict != null
                ? new Dictionary<string, string>(clonesDict, StringComparer.OrdinalIgnoreCase)
                : new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            foreach (var machineClone in machineClones) {
                // machine entries fill gaps and replace per-user entries that no
                // longer point to a valid location; a valid per-user override wins
                string userClonePath;
                if (!merged.TryGetValue(machineClone.Key, out userClonePath)
                        || !CommonUtils.VerifyPath(userClonePath.NormalizeAsPath()))
                    merged[machineClone.Key] = machineClone.Value;
            }
            return merged;
        }

        // return requested registered clone
        // @handled @logs
        public static PyRevitClone GetRegisteredClone(string cloneNameOrRepoPath) {
            foreach (var clone in GetRegisteredClones())
                if (clone.Matches(cloneNameOrRepoPath))
                    return clone;

            throw new PyRevitException(string.Format("Can not find clone \"{0}\"", cloneNameOrRepoPath));
        }

        public static void CreateImageFromClone(PyRevitClone clone, IEnumerable<string> paths, string destPath) {
            // create paths
            var imagePath = CommonUtils.EnsureFileExtension(destPath, GithubAPI.ArchiveFileExtension);
            var targetDir = Path.Combine(Path.GetDirectoryName(imagePath), Path.GetFileNameWithoutExtension(imagePath));
            CommonUtils.EnsurePath(targetDir);

            // copy paths from clone to temp directory
            foreach (var cloneItem in paths) {
                var srcItem = Path.Combine(clone.ClonePath, cloneItem);
                var destItem = Path.Combine(targetDir, cloneItem);
                if (File.Exists(srcItem)) {
                    // then copy and overwrite
                    File.Copy(srcItem, destItem, overwrite: true);
                }
                // otherwise it must be a directory
                else {
                    // remove existing first
                    if (CommonUtils.VerifyPath(destItem))
                        CommonUtils.DeleteDirectory(destItem);

                    // copy new
                    CommonUtils.CopyDirectory(srcItem, destItem);
                }
            }

            // now create the image
            ZipFile.CreateFromDirectory(
                targetDir,
                imagePath,
                compressionLevel: CompressionLevel.Optimal,
                includeBaseDirectory: true
                );

            // delete temp path
            CommonUtils.DeleteDirectory(targetDir);
        }

        // managing clones ===========================================================================================
        // check at least one pyRevit clone is available
        public static bool IsAtLeastOneClones() {
            return GetRegisteredClones().Count > 0;
        }

        /// <summary>
        /// Installs pyRevit by cloning a git repository, installing its CI binaries and registering the clone.
        /// </summary>
        /// <param name="cloneName">The name to register the clone under.</param>
        /// <param name="deploymentName">Deployments are not supported for git clones; any value throws.</param>
        /// <param name="branchName">The branch to clone, or the default branch when null.</param>
        /// <param name="repoUrl">The git source, or the official repository when null.</param>
        /// <param name="destPath">The parent folder; the clone lives in a subfolder named after <paramref name="cloneName"/>.</param>
        /// <param name="credentials">Credentials for a private source.</param>
        /// <param name="installBinaries">Whether to install CI binaries after cloning.</param>
        /// <exception cref="pyRevitBinArtifactNotFoundException">
        /// The clone succeeded but no CI binaries exist for it yet. The folder is kept unregistered and,
        /// when it qualifies for a resume as described in the remarks, running the same command again resumes it.
        /// </exception>
        /// <exception cref="PyRevitException">
        /// The destination folder exists and cannot be resumed; the message names the reason and how to
        /// recover.
        /// </exception>
        /// <remarks>
        /// An existing destination subfolder is resumed instead of cloned again only when it is an
        /// unregistered git clone of the same origin, checked out at the requested branch (a detached HEAD from
        /// a tag or commit checkout is never resumed), whose checkout is complete, whose branch tracks an
        /// existing remote branch and has no local commits missing from it, and the clone name is not
        /// registered at another path as a clone that still opens. A fresh clone, unlike a resume, replaces a
        /// registration of the same name.
        /// A resumed folder is never deleted or reset. Binaries are installed into it only when its
        /// <c>bin</c>, <c>bin.bak</c> and <c>bin.new</c> folders hold no file at any depth, since the install
        /// replaces <c>bin</c> and deletes the other two; otherwise the folder is only registered. When installing or
        /// registering fails, a resumed folder is kept as is; a freshly cloned folder is deleted unless only
        /// the binaries are missing.
        /// Archive (<c>--image</c>) installs never resume; see <see cref="DeployFromImage"/>.
        /// </remarks>
        // @handled @logs
        public static void DeployFromRepo(string cloneName,
                                          string deploymentName = null,
                                          string branchName = null,
                                          string repoUrl = null,
                                          string destPath = null,
                                          GitInstallerCredentials credentials = null,
                                          bool installBinaries = true) {
            if (deploymentName != null) {
                // TODO: Add core checkout option. Figure out how to checkout certain folders in libgit2sharp
                throw new NotImplementedException("Deployment with git clones not implemented yet.");
            }

            if (destPath != null)
                destPath = CommonUtils.ExpandEnvironmentPath(destPath);

            string repoSourcePath = repoUrl ?? PyRevitLabsConsts.OriginalRepoGitPath;
            if (!repoSourcePath.IsValidHttpUrl())
                repoSourcePath = CommonUtils.ExpandEnvironmentPath(repoSourcePath);
            string repoBranch = branchName != null ? branchName : PyRevitLabsConsts.TargetBranch;
            logger.Debug("Repo source determined as \"{0}\" branch \"{1}\"", repoSourcePath.RedactUrlCredentials(), repoBranch);

            // determine destination path if not provided
            if (destPath is null)
                destPath = Path.Combine(PyRevitLabsConsts.PyRevitPath, PyRevitConsts.DefaultCloneInstallName);
            logger.Debug("Destination path determined as \"{0}\"", destPath);
            // make sure destPath exists
            CommonUtils.EnsurePath(destPath);

            destPath = ResolveRepoDestination(destPath, cloneName, repoSourcePath, repoBranch, out var isResumedClone);

            // Drop stale registrations before cloning so a retried install can register cleanly.
            PruneStaleCloneRegistrations();

            // start the clone process
            if (isResumedClone)
                logger.Info("Resuming kept clone \"{0}\"", destPath);
            string clonedPath;
            if (isResumedClone)
                clonedPath = destPath.NormalizeAsPath();
            else {
                using (var repo = GitInstaller.Clone(repoSourcePath, repoBranch, destPath, credentials))
                    clonedPath = repo?.Info.WorkingDirectory.NormalizeAsPath();
            }

            // Check installation
            if (clonedPath != null) {
                try {
                    PyRevitClone.VerifyCloneValidity(clonedPath);
                    if (installBinaries && isResumedClone && HasLocalBinContent(clonedPath))
                        logger.Info("Kept clone already has files under bin; keeping them and installing nothing.");
                    else if (installBinaries)
                        InstallBinariesForRepoClone(
                            clonedPath,
                            repoSourcePath,
                            BinArtifactInstallMode.Clone,
                            repoBranch);
                    logger.Debug("Clone successful \"{0}\"", clonedPath);
                    RegisterClone(cloneName, clonedPath, forceUpdate: true);
                }
                catch (Exception ex) {
                    if (ex is pyRevitBinArtifactNotFoundException || isResumedClone) {
                        ReportKeptFolder(ex, clonedPath, repoSourcePath, repoBranch, cloneName);
                        throw;
                    }
                    logger.Debug(string.Format("Exception occured after clone complete. Deleting clone \"{0}\" | {1}",
                                               clonedPath, ex.Message));
                    UnregisterCloneAtPath(clonedPath);
                    try {
                        CommonUtils.DeleteDirectory(clonedPath);
                    }
                    catch (Exception delEx) {
                        logger.Error(string.Format("Error post-install cleanup on \"{0}\" | {1}",
                                                   clonedPath, delEx.Message));
                    }

                    // cleanup completed, now baloon up the exception
                    throw;
                }
            }
            else
                throw new PyRevitException(string.Format("Error installing pyRevit. Null repo error on \"{0}\"",
                                                         repoUrl));
        }

        /// <summary>
        /// Installs pyRevit from a ZIP archive and registers it. An existing destination subfolder is never
        /// resumed: the call fails instead.
        /// </summary>
        public static void DeployFromImage(string cloneName,
                                           string deploymentName = null,
                                           string branchName = null,
                                           string imagePath = null,
                                           string destPath = null,
                                           bool installBinaries = true,
                                           BinArtifactInstallMode binInstallMode = BinArtifactInstallMode.Clone) {
            if (destPath != null)
                destPath = CommonUtils.ExpandEnvironmentPath(destPath);
            if (imagePath != null)
                imagePath = CommonUtils.ExpandEnvironmentPath(imagePath);

            string repoBranch = branchName != null ? branchName : PyRevitLabsConsts.TargetBranch;
            string imageSource = imagePath != null ? imagePath : GithubAPI.GetBranchArchiveUrl(PyRevitLabsConsts.OriginalRepoId, repoBranch);
            string imageFilePath = null;

            // verify image is zip
            if (!imageSource.ToLower().EndsWith(GithubAPI.ArchiveFileExtension))
                throw new PyRevitException("Clone source must be a ZIP image.");

            logger.Debug("Image file is \"{0}\"", imageSource);

            // determine destination path if not provided
            if (destPath is null)
                destPath = Path.Combine(PyRevitLabsConsts.PyRevitPath, PyRevitConsts.DefaultCopyInstallName);

            // check existing destination path
            if (CommonUtils.VerifyPath(destPath)) {
                destPath = destPath.NormalizeAsPath();
                logger.Debug("Destination path already exists {0}", destPath);
                destPath = Path.Combine(destPath, cloneName);
                logger.Debug("Using subpath {0}", destPath);
                if (CommonUtils.VerifyPath(destPath))
                    throw CreateExistingDestinationError(
                        destPath,
                        RegistrationDecisionAt(destPath)
                        ?? ResumeDecision.NotResumable("image deployments are not resumable", ResumeAdvice.KeepWork));
            }

            logger.Debug("Destination path determined as \"{0}\"", destPath);

            // Drop stale registrations before deploying so a retried install can register cleanly.
            PruneStaleCloneRegistrations();

            // process source
            // decide to download if source is a url
            if (imageSource.IsValidHttpUrl()) {
                try {
                    var pkgDest = Path.Combine(CommonUtils.GetUserTempDirectory(), Path.GetFileName(imageSource));
                    logger.Info("Downloading package \"{0}\"", imageSource);
                    logger.Debug("Downloading package \"{0}\" to \"{1}\"", imageSource, pkgDest);
                    imageFilePath =
                        CommonUtils.DownloadFile(imageSource, pkgDest);
                    logger.Debug("Downloaded to \"{0}\"", imageFilePath);
                }
                catch (Exception ex) {
                    throw new PyRevitException(
                        string.Format("Error downloading repo image file \"{0}\" | {1}", imageSource, ex.Message)
                        );
                }
            }
            // otherwise check if the source is a file and exists
            else if (CommonUtils.VerifyFile(imageSource)) {
                imageFilePath = imageSource;
            }
            // otherwise the source format is unknown
            else {
                throw new PyRevitException(string.Format("Unknown source \"{0}\"", imageSource));
            }

            // now extract the file
            if (imageFilePath == null) {
                throw new PyRevitException(
                    string.Format("Unknown error occured getting package from \"{0}\"", imageSource)
                    );
            }
            var stagedImage = Path.Combine(
                CommonUtils.GetUserTempDirectory(),
                Path.GetFileNameWithoutExtension(imageFilePath)
                );

            // delete existing
            if (CommonUtils.VerifyPath(stagedImage)) {
                logger.Debug("Deleting existing temp staging path \"{0}\"", stagedImage);
                CommonUtils.DeleteDirectory(stagedImage);
            }

            // unpack image
            logger.Info("Preparing package for deployment...");

            try {
                logger.Debug("Staging package to \"{0}\"", stagedImage);
                ZipFile.ExtractToDirectory(imageFilePath, stagedImage);
                if (Directory.GetFiles(stagedImage).Length == 0) {
                    var subDirs = Directory.GetDirectories(stagedImage);
                    if (subDirs.Length > 1) {
                        logger.Debug("Found multiple subdirectories in extracted archive: {0}", string.Join(", ", subDirs));
                    }
                    if (subDirs.Length == 1) {
                        logger.Debug("Found single subdirectory, using it as clone root: \"{0}\"", subDirs[0]);
                        stagedImage = subDirs[0];
                    }
                }
            }
            catch (Exception ex) {
                throw new PyRevitException(
                    string.Format("Error unpacking \"{0}\" | {1}", imageFilePath, ex.Message)
                    );
            }

            // make a pyrevit clone and handle deployment
            try {
                var clone = new PyRevitClone(stagedImage);

                // deployment: copy the needed directories
                logger.Info("Deploying to \"{0}\"", destPath);

                if (deploymentName != null) {
                    // deploy the requested deployment
                    // throws exceptions if deployment does not exist or on copy error
                    Deploy(clone.ClonePath, deploymentName, destPath);
                }
                else {
                    logger.Debug("Deploying complete clone from image...");
                    CommonUtils.CopyDirectory(clone.ClonePath, destPath);
                }

                // cleanup temp files
                logger.Debug("Cleaning up temp files after clone from image...");
                try {
                    CommonUtils.DeleteDirectory(stagedImage);
                }
                catch (Exception delEx) {
                    logger.Error(string.Format("Error cleaning up temp staging files \"{0}\" | {1}",
                                               destPath, delEx.Message));
                }

                // record image deployment settings
                try {
                    RecordDeploymentArgs(cloneName, deploymentName, branchName, imageSource, destPath);
                }
                catch (Exception ex) {
                    logger.Debug(string.Format("Exception occured after clone from image complete. " +
                                               "Deleting clone \"{0}\" | {1}", destPath, ex.Message));
                    UnregisterCloneAtPath(destPath);
                    try {
                        CommonUtils.DeleteDirectory(destPath);
                    }
                    catch (Exception delEx) {
                        logger.Error(string.Format("Error post-install cleanup on \"{0}\" | {1}",
                                                   destPath, delEx.Message));
                    }

                    // cleanup completed, now baloon up the exception
                    throw;
                }

                // register the clone
                if (installBinaries) {
                    InstallBinariesForImageClone(
                        destPath,
                        GithubRepoHelper.ParseRepoId(imageSource),
                        repoBranch,
                        binInstallMode);
                }
                VerifyAndRegisterClone(cloneName, destPath);

                logger.Info("Package deployed and registered.");
            }
            catch (pyRevitBinArtifactNotFoundException ex) {
                logger.Warn(
                    "Image clone deployed but CI binaries could not be installed at \"{0}\" | {1} | {2}",
                    destPath,
                    ex.Message,
                    RecoveryMessage(destPath));
                throw;
            }
            catch (PyRevitException ex) {
                var errMsg = ex.Message;
                if (errMsg != null && errMsg.IndexOf('%') >= 0)
                    errMsg += " Path may contain unexpanded environment variables; ensure TEMP and --dest resolve to absolute paths.";
                throw new PyRevitException(
                    string.Format("Can not find a valid clone inside extracted package. | {0}", errMsg),
                    ex);
            }
        }

        // test clone validity and register
        // @handled @logs
        private static void VerifyAndRegisterClone(string cloneName, string clonePath) {
            try {
                PyRevitClone.VerifyCloneValidity(clonePath);
                logger.Debug("Clone successful \"{0}\"", clonePath);
                RegisterClone(cloneName, clonePath, forceUpdate: true);
            }
            catch (Exception ex) {
                logger.Debug(string.Format("Exception occured after clone complete. Deleting clone \"{0}\" | {1}",
                                           clonePath, ex.Message));
                UnregisterCloneAtPath(clonePath);
                try {
                    CommonUtils.DeleteDirectory(clonePath);
                }
                catch (Exception delEx) {
                    logger.Error(string.Format("Error post-install cleanup on \"{0}\" | {1}",
                                               clonePath, delEx.Message));
                }

                // cleanup completed, now baloon up the exception
                throw;
            }
        }

        // private helper to deploy destination location by name
        // @handled
        private static void Deploy(string fromPath, string deploymentName, string destPath) {
            if (!PyRevitClone.VerifyHasDeployments(fromPath))
                throw new PyRevitException("There are no deployments configured.");

            var validDeployments = PyRevitClone.GetConfiguredDeployments(fromPath);
            foreach (var dep in validDeployments) {
                // compare lowercase deployment names
                if (dep.Name.ToLower() == deploymentName.ToLower()) {
                    logger.Debug("Found deployment \"{0}\"", deploymentName);
                    Deploy(fromPath, dep, destPath);
                    return;
                }
            }
            var validDeploymentNames = string.Join(", ", validDeployments.Select(d => d.Name.ToLower()));
            // means no deployment were found with given name
            throw new PyRevitException(
                string.Format(
                    "Can not find deployment \"{0}\" in \"{1}\". Valid deployments: {2}",
                    deploymentName, fromPath, validDeploymentNames));
        }

        // private helper to deploy destination location by deployment
        // @handled
        private static void Deploy(string imagePath, PyRevitDeployment deployment, string destPath) {
            logger.Debug("Deploying from \"{0}\"", deployment.Name);
            foreach (var depPath in deployment.Paths) {
                var depSrcPath = Path.Combine(imagePath, depPath);
                var depDestPath = Path.Combine(destPath, depPath);

                // if source is a file
                if (File.Exists(depSrcPath)) {
                    // then copy and overwrite
                    File.Copy(depSrcPath, depDestPath, overwrite: true);
                }
                // otherwise it must be a directory
                else {
                    // remove existing first
                    if (CommonUtils.VerifyPath(depDestPath))
                        CommonUtils.DeleteDirectory(depDestPath);

                    // copy new
                    CommonUtils.CopyDirectory(depSrcPath, depDestPath);
                }
            }
        }

        // record source image and deploy configs at clone path for later updates
        private static void RecordDeploymentArgs(string cloneName,
                                                 string deploymentName,
                                                 string branchName,
                                                 string imagePath,
                                                 string clonePath) {
            var cloneMemoryFilePath = Path.Combine(clonePath, PyRevitConsts.DeployFromImageConfigsFilename);
            logger.Debug(string.Format("Recording deploy parameters for image clone \"{0}\" to \"{1}\"",
                                       cloneName, cloneMemoryFilePath));

            try {
                var f = File.CreateText(cloneMemoryFilePath);
                f.WriteLine(imagePath);
                f.WriteLine(branchName);
                f.WriteLine(deploymentName);
                f.Close();
            }
            catch (Exception ex) {
                throw new PyRevitException(string.Format("Error writing deployment arguments to \"{0}\" | {1}",
                                                         cloneMemoryFilePath, ex.Message));
            }
        }

        private static void ReDeployClone(PyRevitClone clone, GitInstallerCredentials credentials, bool skipBin = false) {
            // grab clone arguments from inside of clone
            var cloneName = clone.Name;
            var clonePath = clone.ClonePath;
            var cloneDeployArgs = clone.DeploymentArgs;
            logger.Debug("Clone Name=\"{0}\", Path=\"{1}\" Args=> {2}", cloneName, clonePath, cloneDeployArgs);

            ReplaceClone(cloneName, clonePath, () => DeployFromImage(
                cloneName: cloneName,
                deploymentName: cloneDeployArgs.DeploymentName,
                branchName: cloneDeployArgs.BranchName,
                imagePath: cloneDeployArgs.Url,
                destPath: clonePath,
                installBinaries: !skipBin,
                binInstallMode: BinArtifactInstallMode.Update
                ));
        }

        internal static void ReplaceClone(string cloneName, string clonePath, Action redeploy) {
            var backupPath = clonePath.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar)
                             + ".update-backup-" + Guid.NewGuid().ToString("N");

            Directory.Move(clonePath, backupPath);

            try {
                redeploy();
            }
            catch (pyRevitBinArtifactNotFoundException) {
                DeleteCloneBackup(backupPath);
                throw;
            }
            catch {
                RestoreClone(cloneName, clonePath, backupPath);
                throw;
            }

            DeleteCloneBackup(backupPath);
        }

        private static void DeleteCloneBackup(string backupPath) {
            try {
                CommonUtils.DeleteDirectory(backupPath);
            }
            catch (Exception delEx) {
                logger.Error(string.Format("Error removing previous clone backup \"{0}\" | {1}",
                                           backupPath, delEx.Message));
            }
        }

        internal static void RestoreClone(string cloneName, string clonePath, string backupPath) {
            logger.Warn("Update failed. Restoring previous clone at \"{0}\"", clonePath);
            try {
                if (CommonUtils.VerifyPath(clonePath)) {
                    UnregisterCloneAtPath(clonePath);
                    CommonUtils.DeleteDirectory(clonePath);
                }
                Directory.Move(backupPath, clonePath);
                RegisterClone(cloneName, clonePath, forceUpdate: true);
            }
            catch (Exception restoreEx) {
                logger.Error(string.Format("Could not restore clone \"{0}\" at \"{1}\". " +
                                           "The previous clone is kept at \"{2}\" | {3}",
                                           cloneName, clonePath, backupPath, restoreEx.Message));
            }
        }

        /// <summary>
        /// Unregisters the clone and deletes its directory. The user config file is left
        /// untouched: it is shared by every clone and holds no clone-specific settings
        /// beyond the registry entry removed here.
        /// </summary>
        // @handled @logs
        public static void Delete(PyRevitClone clone) {
            logger.Debug("Unregistering clone \"{0}\"", clone);
            UnregisterClone(clone);

            logger.Debug("Removing directory \"{0}\"", clone.ClonePath);
            CommonUtils.DeleteDirectory(clone.ClonePath);
        }

        /// <summary>
        /// Unregisters and deletes every registered clone.
        /// </summary>
        /// <param name="clearConfigs">
        /// Also deletes the whole user config file, including every setting unrelated to the
        /// clones.
        /// </param>
        // @handled @logs
        public static void DeleteAllClones(bool clearConfigs = false) {
            foreach (var clone in GetRegisteredClones())
                Delete(clone);

            if (clearConfigs)
                PyRevitConfigs.DeleteConfig();
        }

        // force update given or all registered clones
        // @handled @logs
        public static void Update(PyRevitClone clone, GitInstallerCredentials credentials, bool skipBin = false) {
            // current user config
            logger.Debug("Updating pyRevit clone \"{0}\"", clone.Name);
            if (clone.IsRepoDeploy) {
                var res = GitInstaller.ForcedUpdate(clone.ClonePath, credentials);
                if (res <= UpdateStatus.Conflicts)
                    throw new PyRevitException(string.Format("Error updating clone \"{0}\"", clone.Name));

                if (!skipBin)
                    InstallBinariesForRepoClone(
                        clone.ClonePath,
                        clone.Origin,
                        BinArtifactInstallMode.Update);
            }
            else {
                // re-deploying is how the no-git clones get updated
                ReDeployClone(clone, credentials, skipBin: skipBin);
            }
        }

        // force update given or all registered clones
        // @handled @logs
        public static void UpdateAllClones(GitInstallerCredentials credentials, bool skipBin = false) {
            logger.Debug("Updating all pyRevit clones");
            foreach (var clone in GetRegisteredClones())
                Update(clone, credentials, skipBin: skipBin);
        }

        private enum ResumeDecisionKind {
            Resume,
            NotResumable,
            RegisteredClone,
            RegisteredInvalidClone,
            NameRegisteredElsewhere,
            NameRegisteredHidden,
        }

        private enum ResumeAdvice {
            DeleteFolder,
            KeepWork,
        }

        private sealed class ResumeDecision {
            public static readonly ResumeDecision Resume =
                new ResumeDecision(ResumeDecisionKind.Resume, null, null, ResumeAdvice.KeepWork);

            private ResumeDecision(ResumeDecisionKind kind, string reason, string registeredName, ResumeAdvice advice) {
                Kind = kind;
                Reason = reason;
                RegisteredName = registeredName;
                Advice = advice;
            }

            public ResumeDecisionKind Kind { get; }
            public string Reason { get; }
            public string RegisteredName { get; }
            public ResumeAdvice Advice { get; }
            public bool CanResume => Kind == ResumeDecisionKind.Resume;

            public static ResumeDecision NotResumable(string reason, ResumeAdvice advice) {
                return new ResumeDecision(ResumeDecisionKind.NotResumable, reason, null, advice);
            }

            public static ResumeDecision Registered(ResumeDecisionKind kind, string registeredName) {
                return new ResumeDecision(kind, null, registeredName, ResumeAdvice.KeepWork);
            }

            public static ResumeDecision NameElsewhere(string name, string path, bool isListed) {
                return new ResumeDecision(
                    isListed ? ResumeDecisionKind.NameRegisteredElsewhere : ResumeDecisionKind.NameRegisteredHidden,
                    string.Format("a clone named \"{0}\" is already registered at \"{1}\"", name, path),
                    name,
                    ResumeAdvice.KeepWork);
            }
        }

        private static string RecoveryMessage(string path) {
            return string.Format(
                "To recover, register the folder with: pyrevit clones add <name> \"{0}\" " +
                "then pyrevit clones update <name>, delete the folder, or choose another --dest.",
                path);
        }

        private static string AdviceFor(string path, ResumeDecision decision) {
            switch (decision.Kind) {
                case ResumeDecisionKind.RegisteredClone:
                    return string.Format(
                        "To refresh it run: pyrevit clones update \"{0}\", or choose another --dest.",
                        decision.RegisteredName);
                case ResumeDecisionKind.RegisteredInvalidClone:
                    return "Move the folder aside, or delete it if it holds nothing you need, which drops its stale registration, or choose another --dest.";
                case ResumeDecisionKind.NameRegisteredElsewhere:
                    return string.Format(
                        "Choose another clone name or --dest, or run: pyrevit clones forget \"{0}\".",
                        decision.RegisteredName);
                case ResumeDecisionKind.NameRegisteredHidden:
                    return string.Format(
                        "That registration is not listed, so it cannot be forgotten by name. Choose another clone " +
                        "name or --dest, or replace it with: pyrevit clones add \"{0}\" \"{1}\" --force.",
                        decision.RegisteredName,
                        path);
            }
            if (decision.Advice == ResumeAdvice.DeleteFolder)
                return "Move the folder aside, or delete it if it holds nothing you need, or choose another --dest.";
            return string.Format(
                "If it holds work you want to keep, commit or stash it first, then register the folder with: " +
                "pyrevit clones add <name> \"{0}\" (this does not change the folder), or choose another --dest. " +
                "pyrevit clones update <name> discards uncommitted edits to tracked files and merges the remote " +
                "branch into local commits; add --skip-bin to keep its bin.",
                path);
        }

        private static PyRevitException CreateExistingDestinationError(string path, ResumeDecision decision) {
            string problem;
            switch (decision.Kind) {
                case ResumeDecisionKind.RegisteredClone:
                    problem = string.Format("is already registered as clone \"{0}\"", decision.RegisteredName);
                    break;
                case ResumeDecisionKind.RegisteredInvalidClone:
                    problem = string.Format(
                        "is registered as clone \"{0}\" but is no longer a valid clone",
                        decision.RegisteredName);
                    break;
                case ResumeDecisionKind.NameRegisteredElsewhere:
                case ResumeDecisionKind.NameRegisteredHidden:
                    problem = string.Format("cannot be resumed ({0})", decision.Reason);
                    break;
                default:
                    problem = string.Format("is not a registered clone ({0})", decision.Reason);
                    break;
            }
            return new PyRevitException(string.Format(
                "Destination path already exists \"{0}\" and {1}. {2}",
                path,
                problem,
                AdviceFor(path, decision)));
        }

        private static string ResolveRepoDestination(
            string destPath,
            string cloneName,
            string repoSourcePath,
            string repoBranch,
            out bool isResumed) {
            isResumed = false;
            logger.Debug("Destination path already exists {0}", destPath);
            var clonePath = Path.Combine(destPath, cloneName);
            logger.Debug("Using subpath {0}", clonePath);
            if (!CommonUtils.VerifyPath(clonePath))
                return clonePath;

            var decision = DecideResume(clonePath, repoSourcePath, repoBranch, cloneName);
            if (!decision.CanResume)
                throw CreateExistingDestinationError(clonePath, decision);
            isResumed = true;
            return clonePath;
        }

        private static bool CanOpenAsClone(string path, string name) {
            try {
                return CreateVerifiedClone(path, name).ClonePath.IsSamePathAs(path);
            }
            catch (Exception) {
                return false;
            }
        }

        private static bool OpensAsCloneAtAnyPath(string path, string name) {
            if (!CommonUtils.VerifyPath(path))
                return false;
            try {
                CreateVerifiedClone(path, name);
                return true;
            }
            catch (Exception) {
                return false;
            }
        }

        private static ResumeDecision RegistrationDecisionAt(string clonePath) {
            var entry = GetStoredCloneRegistrations()
                .FirstOrDefault(stored => stored.Value.NormalizeAsPath().IsSamePathAs(clonePath));
            if (entry.Key == null)
                return null;
            return ResumeDecision.Registered(
                CanOpenAsClone(entry.Value.NormalizeAsPath(), entry.Key)
                    ? ResumeDecisionKind.RegisteredClone
                    : ResumeDecisionKind.RegisteredInvalidClone,
                entry.Key);
        }

        private static ResumeDecision DecideResume(
            string clonePath,
            string repoSourcePath,
            string effectiveBranch,
            string cloneName) {
            var registeredAtPath = RegistrationDecisionAt(clonePath);
            if (registeredAtPath != null)
                return registeredAtPath;
            if (!GitInstaller.IsValidRepo(clonePath))
                return ResumeDecision.NotResumable("it is not a git repository", ResumeAdvice.DeleteFolder);
            var originUrl = GitInstaller.GetRemoteUrl(clonePath, PyRevitConsts.DefaultCloneRemoteName);
            if (originUrl == null)
                return ResumeDecision.NotResumable("it has no origin remote", ResumeAdvice.DeleteFolder);
            if (!GitInstaller.AreSameRemote(originUrl, repoSourcePath))
                return ResumeDecision.NotResumable(
                    string.Format(
                        "its origin remote \"{0}\" is not the requested source \"{1}\"",
                        originUrl.RedactUrlCredentials(),
                        repoSourcePath.RedactUrlCredentials()),
                    ResumeAdvice.DeleteFolder);
            if (!GitInstaller.HasCompleteWorkingTree(clonePath))
                return ResumeDecision.NotResumable(
                    "its checkout is incomplete, as after an interrupted clone",
                    ResumeAdvice.DeleteFolder);
            if (!CanOpenAsClone(clonePath, cloneName))
                return ResumeDecision.NotResumable(
                    "it is not a valid pyRevit clone, for example pyrevitlib/pyrevit is missing",
                    ResumeAdvice.DeleteFolder);
            if (GitInstaller.IsHeadDetached(clonePath))
                return ResumeDecision.NotResumable(
                    "its HEAD is detached, as after a tag or commit checkout, and those are never resumed",
                    ResumeAdvice.KeepWork);
            var keptBranch = GitInstaller.GetCheckedoutBranch(clonePath);
            if (keptBranch != effectiveBranch)
                return ResumeDecision.NotResumable(
                    string.Format(
                        "it is checked out at branch \"{0}\", not the requested \"{1}\"",
                        keptBranch,
                        effectiveBranch),
                    ResumeAdvice.KeepWork);
            if (!GitInstaller.HasTrackingBranch(clonePath))
                return ResumeDecision.NotResumable(
                    "its branch does not track an existing remote branch",
                    ResumeAdvice.KeepWork);
            if (GitInstaller.IsLocalAheadOfTrackingBranch(clonePath))
                return ResumeDecision.NotResumable(
                    "it has local commits that are not on its remote branch",
                    ResumeAdvice.KeepWork);
            var sameNamed = GetStoredCloneRegistrations().FirstOrDefault(
                entry => string.Equals(entry.Key, cloneName, StringComparison.OrdinalIgnoreCase)
                         && OpensAsCloneAtAnyPath(entry.Value.NormalizeAsPath(), entry.Key));
            if (sameNamed.Key != null)
                return ResumeDecision.NameElsewhere(
                    cloneName,
                    sameNamed.Value,
                    GetRegisteredClones(pruneStoredList: false)
                        .Any(clone => string.Equals(clone.Name, cloneName, StringComparison.OrdinalIgnoreCase)));
            return ResumeDecision.Resume;
        }

        internal static string DescribeKeptFolderRecovery(
            string clonedPath,
            string repoSourcePath,
            string repoBranch,
            string cloneName) {
            ResumeDecision decision;
            try {
                decision = DecideResume(clonedPath, repoSourcePath, repoBranch, cloneName);
            }
            catch (Exception) {
                decision = ResumeDecision.NotResumable("its state could not be read", ResumeAdvice.DeleteFolder);
            }
            if (decision.CanResume)
                return "Running the same command again resumes.";
            return string.Format(
                "It cannot be resumed ({0}). {1}",
                decision.Reason ?? "it is already registered",
                AdviceFor(clonedPath, decision));
        }

        private static void ReportKeptFolder(
            Exception ex,
            string clonedPath,
            string repoSourcePath,
            string repoBranch,
            string cloneName) {
            var recovery = DescribeKeptFolderRecovery(clonedPath, repoSourcePath, repoBranch, cloneName);
            if (ex is pyRevitBinArtifactNotFoundException)
                logger.Warn(
                    "Git clone succeeded but CI binaries could not be installed at \"{0}\" | {1} | {2}",
                    clonedPath,
                    ex.Message,
                    recovery);
            else
                logger.Warn(
                    "Resuming the kept clone at \"{0}\" failed | {1} | {2}",
                    clonedPath,
                    ex.Message,
                    recovery);
        }

        private static Dictionary<string, string> GetStoredCloneRegistrations() {
            var cfg = PyRevitConfigs.GetConfigFile();
            return MergeMachineRegisteredClones(cfg, cfg.Environment.Clones)
                   ?? new Dictionary<string, string>();
        }

        private static void InstallBinariesForRepoClone(
            string clonePath,
            string repoUrl,
            BinArtifactInstallMode mode,
            string branchName = null) {
            try {
                if (BinariesInstallHook != null)
                    BinariesInstallHook(clonePath, repoUrl, mode, branchName);
                else
                    BinArtifactInstaller.InstallForRepoClone(clonePath, repoUrl, mode, branchName);
            }
            catch (pyRevitMissingGithubTokenException) {
                throw;
            }
            catch (pyRevitBinArtifactNotFoundException) {
                throw;
            }
            catch (Exception ex) {
                throw new PyRevitException(
                    string.Format("Error installing CI binaries for clone \"{0}\" | {1}", clonePath, ex.Message),
                    ex);
            }
        }

        private static void InstallBinariesForImageClone(
            string clonePath,
            string repoId,
            string branchName,
            BinArtifactInstallMode mode) {
            try {
                BinArtifactInstaller.InstallForImageClone(clonePath, repoId, branchName, mode);
            }
            catch (pyRevitMissingGithubTokenException) {
                throw;
            }
            catch (pyRevitBinArtifactNotFoundException) {
                throw;
            }
            catch (Exception ex) {
                throw new PyRevitException(
                    string.Format("Error installing CI binaries for clone \"{0}\" | {1}", clonePath, ex.Message),
                    ex);
            }
        }

        private static void PruneStaleCloneRegistrations() {
            GetRegisteredClones();
        }

        private static void UnregisterCloneAtPath(string clonePath) {
            if (string.IsNullOrWhiteSpace(clonePath))
                return;

            var normalizedPath = clonePath.NormalizeAsPath();
            foreach (var clone in GetRegisteredClones().ToList()) {
                if (clone.ClonePath.IsSamePathAs(normalizedPath))
                    UnregisterClone(clone);
            }
        }

        private static bool HasLocalBinContent(string clonePath) {
            var binPath = Path.Combine(clonePath, "bin");
            return HasFiles(binPath) || HasFiles(binPath + ".bak") || HasFiles(binPath + ".new");
        }

        private static bool HasFiles(string folderPath) {
            return Directory.Exists(folderPath)
                   && Directory.EnumerateFiles(folderPath, "*", SearchOption.AllDirectories).Any();
        }

        private static bool HasBuiltBinaries(string clonePath) {
            var netfxEngines = Path.Combine(clonePath, "bin", "netfx", "engines");
            var netcoreEngines = Path.Combine(clonePath, "bin", "netcore", "engines");
            return CommonUtils.VerifyPath(netfxEngines) || CommonUtils.VerifyPath(netcoreEngines);
        }

        private static void WarnIfBinEnginesMissing(string clonePath) {
            if (HasBuiltBinaries(clonePath))
                return;

            logger.Warn(
                "Clone at \"{0}\" does not contain built binaries under bin/*/engines. "
                + "Run \"dotnet run -- ci\" in the repository root, "
                + "or install with \"pyrevit clone\" to download pre-built binaries from CI.",
                clonePath);
        }

        // updates the config value for registered clones
        public static void SaveRegisteredClones(IEnumerable<PyRevitClone> clonesList) {
            var cfg = PyRevitConfigs.GetConfigFile();
            cfg.SaveSection(
                new EnvironmentSection() { Clones = clonesList.ToDictionary(item => item.Name, item => item.ClonePath) });
            PyRevitAttachments.ClearAttachmentCache();
        }
    }
}
