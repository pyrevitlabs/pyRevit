using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Text.RegularExpressions;
using System.Security.Principal;
using System.Text;

using pyRevitLabs.Common;
using pyRevitLabs.Common.Extensions;

using MadMilkman.Ini;
using pyRevitLabs.Json.Linq;
using NLog;

namespace pyRevitLabs.TargetApps.Revit {
    // main pyrevit functionality class
    public static class PyRevit {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        // STANDARD PATHS ============================================================================================
        // pyRevit %appdata% path
        // @reviewed
        public static string pyRevitAppDataPath =>
            Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                                          PyRevitConsts.AppdataDirName);

        // pyRevit %programdata% path
        // @reviewed
        public static string pyRevitProgramDataPath =>
            Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData),
                                          PyRevitConsts.AppdataDirName);

        // pyRevit default extensions path
        // @reviewed
        public static string pyRevitDefaultExtensionsPath =>
            Path.Combine(pyRevitAppDataPath, PyRevitConsts.ExtensionsDefaultDirName);

        // pyRevit config file path
        // @reviewed
        public static string pyRevitConfigFilePath {
            get {
                var cfgFile = FindConfigFileInDirectory(pyRevitAppDataPath);
                return cfgFile != null ? cfgFile : Path.Combine(pyRevitAppDataPath, PyRevitConsts.DefaultConfigsFileName);
            }
        }

        // pyRevit config file path
        // @reviewed
        public static string pyRevitSeedConfigFilePath {
            get {
                var cfgFile = FindConfigFileInDirectory(pyRevitProgramDataPath);
                return cfgFile != null ? cfgFile : Path.Combine(pyRevitProgramDataPath,
                                                        PyRevitConsts.DefaultConfigsFileName);
            }
        }

        // pyrevit cache folder 
        // @reviewed
        public static string GetCacheDirectory(int revitYear) {
            return Path.Combine(pyRevitAppDataPath, revitYear.ToString());
        }

        // pyrevit logs folder 
        // @reviewed
        public static string GetLogsDirectory() {
            return Path.Combine(pyRevitAppDataPath, PyRevitConsts.AppdataLogsDirName);
        }

        // managing clones ===========================================================================================
        // check at least one pyRevit clone is available
        public static bool IsAtLeastOneClones() {
            return GetRegisteredClones().Count > 0;
        }

        // install pyRevit by cloning from git repo
        // @handled @logs
        public static void DeployFromRepo(string cloneName,
                                          string deploymentName = null,
                                          string branchName = null,
                                          string repoUrl = null,
                                          string destPath = null) {
            string repoSourcePath = repoUrl ?? PyRevitConsts.OriginalRepoPath;
            string repoBranch = branchName != null ? branchName : PyRevitConsts.OriginalRepoDefaultBranch;
            logger.Debug("Repo source determined as \"{0}:{1}\"", repoSourcePath, repoBranch);

            // determine destination path if not provided
            if (destPath == null)
                destPath = Path.Combine(pyRevitAppDataPath, PyRevitConsts.DefaultCloneInstallName);
            logger.Debug("Destination path determined as \"{0}\"", destPath);
            // make sure destPath exists
            CommonUtils.EnsurePath(destPath);

            // check existing destination path
            if (CommonUtils.VerifyPath(destPath)) {
                logger.Debug("Destination path already exists {0}", destPath);
                destPath = Path.Combine(destPath, cloneName);
                logger.Debug("Using subpath {0}", destPath);
                if (CommonUtils.VerifyPath(destPath))
                    throw new pyRevitException(string.Format("Destination path already exists \"{0}\"", destPath));
            }

            // start the clone process
            LibGit2Sharp.Repository repo = null;
            if (deploymentName != null) {
                // TODO: Add core checkout option. Figure out how to checkout certain folders in libgit2sharp
                throw new NotImplementedException("Deployment with git clones not implemented yet.");
            }
            else {
                repo = GitInstaller.Clone(repoSourcePath, repoBranch, destPath);
            }

            // Check installation
            if (repo != null) {
                // make sure to delete the repo if error occured after cloning
                var clonedPath = repo.Info.WorkingDirectory;
                try {
                    PyRevitClone.VerifyCloneValidity(clonedPath);
                    logger.Debug("Clone successful \"{0}\"", clonedPath);
                    RegisterClone(cloneName, clonedPath);
                }
                catch (Exception ex) {
                    logger.Debug(string.Format("Exception occured after clone complete. Deleting clone \"{0}\" | {1}",
                                               clonedPath, ex.Message));
                    try {
                        CommonUtils.DeleteDirectory(clonedPath);
                    }
                    catch (Exception delEx) {
                        logger.Error(string.Format("Error post-install cleanup on \"{0}\" | {1}",
                                                   clonedPath, delEx.Message));
                    }

                    // cleanup completed, now baloon up the exception
                    throw ex;
                }
            }
            else
                throw new pyRevitException(string.Format("Error installing pyRevit. Null repo error on \"{0}\"",
                                                         repoUrl));
        }

        public static void DeployFromImage(string cloneName,
                                           string deploymentName = null,
                                           string branchName = null,
                                           string imagePath = null,
                                           string destPath = null) {
            string repoBranch = branchName != null ? branchName : PyRevitConsts.OriginalRepoDefaultBranch;
            string imageSource = imagePath != null ? imagePath : PyRevitConsts.GetBranchArchiveUrl(repoBranch);
            string imageFilePath = null;

            // verify image is zip
            if (!imageSource.ToLower().EndsWith(PyRevitConsts.ImageFileExtension))
                throw new pyRevitException("Clone source must be a ZIP image.");

            logger.Debug("Image file is \"{0}\"", imageSource);

            // determine destination path if not provided
            if (destPath == null)
                destPath = Path.Combine(pyRevitAppDataPath, PyRevitConsts.DefaultCopyInstallName);

            // check existing destination path
            if (CommonUtils.VerifyPath(destPath)) {
                logger.Debug("Destination path already exists {0}", destPath);
                destPath = Path.Combine(destPath, cloneName);
                logger.Debug("Using subpath {0}", destPath);
                if (CommonUtils.VerifyPath(destPath))
                    throw new pyRevitException(string.Format("Destination path already exists \"{0}\"", destPath));
            }

            logger.Debug("Destination path determined as \"{0}\"", destPath);

            // process source
            // decide to download if source is a url
            if (imageSource.IsValidHttpUrl()) {
                try {
                    var pkgDest = Path.Combine(Environment.GetEnvironmentVariable("TEMP"),
                                               Path.GetFileName(imageSource));
                    logger.Debug("Downloading package \"{0}\" to \"{1}\"", imageSource, pkgDest);
                    imageFilePath =
                        CommonUtils.DownloadFile(imageSource, pkgDest);
                    logger.Debug("Downloaded to \"{0}\"", imageFilePath);
                }
                catch (Exception ex) {
                    throw new pyRevitException(
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
                throw new pyRevitException(string.Format("Unknow source \"{0}\"", imageSource));
            }

            // now extract the file
            if (imageFilePath != null) {
                var stagedImage = Path.Combine(
                    Environment.GetEnvironmentVariable("TEMP"),
                    Path.GetFileNameWithoutExtension(imageFilePath)
                    );

                // delete existing
                if (CommonUtils.VerifyPath(stagedImage)) {
                    logger.Debug("Deleting existing temp staging path \"{0}\"", stagedImage);
                    CommonUtils.DeleteDirectory(stagedImage);
                }

                // unpack image
                try {
                    logger.Debug("Staging package to \"{0}\"", stagedImage);
                    ZipFile.ExtractToDirectory(imageFilePath, stagedImage);
                }
                catch (Exception ex) {
                    throw new pyRevitException(
                        string.Format("Error unpacking \"{0}\" | {1}", imageFilePath, ex.Message)
                        );
                }

                // make a pyrevit clone and handle deployment
                try {
                    var clone = new PyRevitClone(stagedImage);

                    // deployment: copy the needed directories
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
                    CommonUtils.DeleteDirectory(stagedImage);

                    // record image deployment settings
                    try {
                        RecordDeploymentArgs(cloneName, deploymentName, branchName, imagePath, destPath);
                    }
                    catch (Exception ex) {
                        logger.Debug(string.Format("Exception occured after clone from image complete. " +
                                                   "Deleting clone \"{0}\" | {1}", destPath, ex.Message));
                        try {
                            CommonUtils.DeleteDirectory(destPath);
                        }
                        catch (Exception delEx) {
                            logger.Error(string.Format("Error post-install cleanup on \"{0}\" | {1}",
                                                       destPath, delEx.Message));
                        }

                        // cleanup completed, now baloon up the exception
                        throw ex;
                    }

                    // register the clone
                    VerifyAndRegisterClone(cloneName, destPath);
                }
                catch (pyRevitException ex) {
                    logger.Error("Can not find a valid clone inside extracted package. | {0}", ex.Message);
                }
            }
            else
                throw new pyRevitException(
                    string.Format("Unknown error occured getting package from \"{0}\"", imageSource)
                    );
        }

        // test clone validity and register
        // @handled @logs
        private static void VerifyAndRegisterClone(string cloneName, string clonePath) {
            try {
                PyRevitClone.VerifyCloneValidity(clonePath);
                logger.Debug("Clone successful \"{0}\"", clonePath);
                RegisterClone(cloneName, clonePath);
            }
            catch (Exception ex) {
                logger.Debug(string.Format("Exception occured after clone complete. Deleting clone \"{0}\" | {1}",
                                           clonePath, ex.Message));
                try {
                    CommonUtils.DeleteDirectory(clonePath);
                }
                catch (Exception delEx) {
                    logger.Error(string.Format("Error post-install cleanup on \"{0}\" | {1}",
                                               clonePath, delEx.Message));
                }

                // cleanup completed, now baloon up the exception
                throw ex;
            }
        }

        // private helper to deploy destination location by name
        // @handled
        private static void Deploy(string fromPath, string deploymentName, string destPath) {
            if (!PyRevitClone.VerifyHasDeployments(fromPath))
                throw new pyRevitException("There are no deployments configured.");

            foreach (var dep in PyRevitClone.GetConfiguredDeployments(fromPath)) {
                // compare lowercase deployment names
                if (dep.Name.ToLower() == deploymentName.ToLower()) {
                    logger.Debug("Found deployment \"{0}\"", deploymentName);
                    Deploy(fromPath, dep, destPath);
                    return;
                }
            }

            // means no deployment were found with given name
            throw new pyRevitException(string.Format("Can not find deployment \"{0}\" in \"{1}\"",
                                                        deploymentName, fromPath));
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
                throw new pyRevitException(string.Format("Error writing deployment arguments to \"{0}\" | {1}",
                                                         cloneMemoryFilePath, ex.Message));
            }
        }

        private static void ReDeployClone(PyRevitClone clone) {
            // grab clone arguments from inside of clone
            var cloneName = clone.Name;
            var clonePath = clone.ClonePath;
            var cloneDeployArgs = clone.DeploymentArgs;
            // delete existing clone
            Delete(clone);

            // re-deploy
            DeployFromImage(
                cloneName: cloneName,
                deploymentName: cloneDeployArgs.DeploymentName,
                branchName: cloneDeployArgs.BranchName,
                imagePath: cloneDeployArgs.Url,
                destPath: clonePath
                );
        }

        // uninstall primary or specified clone, has option for clearing configs
        // @handled @logs
        public static void Delete(PyRevitClone clone, bool clearConfigs = false) {
            logger.Debug("Unregistering clone \"{0}\"", clone);
            UnregisterClone(clone);

            logger.Debug("Removing directory \"{0}\"", clone.ClonePath);
            CommonUtils.DeleteDirectory(clone.ClonePath);

            if (clearConfigs)
                DeleteConfigs();
        }

        // uninstall all registered clones
        // @handled @logs
        public static void DeleteAllClones(bool clearConfigs = false) {
            foreach (var clone in GetRegisteredClones())
                Delete(clone, clearConfigs: false);

            if (clearConfigs)
                DeleteConfigs();
        }

        // force update given or all registered clones
        // @handled @logs
        public static void Update(PyRevitClone clone) {
            // current user config
            logger.Debug("Updating pyRevit clone \"{0}\"", clone.Name);
            if (clone.IsRepoDeploy) {
                var res = GitInstaller.ForcedUpdate(clone.ClonePath);
                if (res <= UpdateStatus.Conflicts)
                    throw new pyRevitException(string.Format("Error updating clone \"{0}\"", clone.Name));
            }
            else {
                // re-deploying is how the no-git clones get updated
                ReDeployClone(clone);
            }
        }

        // force update given or all registered clones
        // @handled @logs
        public static void UpdateAllClones() {
            logger.Debug("Updating all pyRevit clones");
            foreach (var clone in GetRegisteredClones())
                Update(clone);
        }

        // managing attachments ======================================================================================
        // attach primary or given clone to revit version
        // @handled @logs
        public static void Attach(int revitYear,
                                  PyRevitClone clone,
                                  int engineVer,
                                  bool allUsers = false,
                                  bool force = false) {
            // make the addin manifest file
            var engine = clone.GetEngine(engineVer);

            if (engine.Runtime) {
                logger.Debug(string.Format("Attaching Clone \"{0}\" @ \"{1}\" to Revit {2}",
                                            clone.Name, clone.ClonePath, revitYear));
                Addons.CreateManifestFile(revitYear,
                                          PyRevitConsts.AddinFileName,
                                          PyRevitConsts.AddinName,
                                          engine.AssemblyPath,
                                          PyRevitConsts.AddinId,
                                          PyRevitConsts.AddinClassName,
                                          PyRevitConsts.VendorId,
                                          allusers: allUsers);
            }
            else
                throw new pyRevitException(string.Format("Engine {0} can not be used as runtime.", engineVer));
        }

        // attach clone to all installed revit versions
        // @handled @logs
        public static void AttachToAll(PyRevitClone clone, int engineVer = 000, bool allUsers = false) {
            foreach (var revit in RevitProduct.ListInstalledProducts())
                Attach(revit.ProductYear, clone, engineVer: engineVer, allUsers: allUsers);
        }

        // detach from revit version
        // @handled @logs
        public static void Detach(int revitYear) {
            logger.Debug("Detaching from Revit {0}", revitYear);
            Addons.RemoveManifestFile(revitYear, PyRevitConsts.AddinName);
        }

        // detach pyrevit attachment
        // @handled @logs
        public static void Detach(PyRevitAttachment attachment) {
            logger.Debug("Detaching from Revit {0}", attachment.Product.ProductYear);
            Detach(attachment.Product.ProductYear);
        }

        // detach from all attached revits
        // @handled @logs
        public static void DetachAll() {
            foreach (var attachment in GetAttachments()) {
                Detach(attachment);
            }
        }

        // get all attached revit versions
        // @handled @logs
        public static List<PyRevitAttachment> GetAttachments() {
            var attachments = new List<PyRevitAttachment>();

            foreach (var revit in RevitProduct.ListInstalledProducts()) {
                logger.Debug("Checking attachment to Revit \"{0}\"", revit.Version);
                var userManifest = Addons.GetAttachedManifest(revit.ProductYear, allUsers: false);
                var allUsersManifest = Addons.GetAttachedManifest(revit.ProductYear, allUsers: true);

                PyRevitAttachment attachment = null;
                if (allUsersManifest != null) {
                    logger.Debug("pyRevit (All Users) is attached to Revit \"{0}\"", revit.Version);
                    attachment = new PyRevitAttachment(allUsersManifest, revit, PyRevitAttachmentType.AllUsers);

                }
                else if (userManifest != null) {
                    logger.Debug("pyRevit (Current User) is attached to Revit \"{0}\"", revit.Version);
                    attachment = new PyRevitAttachment(userManifest, revit, PyRevitAttachmentType.CurrentUser);
                }

                // verify attachment has found
                if (attachment != null) {
                    // try to find clone in registered clones
                    foreach (var clone in GetRegisteredClones()) {
                        if (attachment.Clone != null && attachment.Clone.ClonePath.Contains(clone.ClonePath)) {
                            attachment.SetClone(clone);
                            break;
                        }
                    }

                    attachments.Add(attachment);
                }
                else
                    logger.Debug("No attachment found for Revit \"{0}\"", revit.Version);
            }

            return attachments;
        }

        // get attachment for a revit version
        // @handled @logs
        public static PyRevitAttachment GetAttached(int revitYear) {
            foreach (var attachment in GetAttachments())
                if (attachment.Product.ProductYear == revitYear)
                    return attachment;
            return null;
        }

        // managing clones ===========================================================================================
        // clones are git clones. pyRevit module likes to know about available clones to
        // perform operations on (switching engines, clones, uninstalling, ...)

        // register a clone in a configs
        // @handled @logs
        public static void RegisterClone(string cloneName, string repoPath, bool forceUpdate = false) {
            var normalPath = repoPath.NormalizeAsPath();
            logger.Debug("Registering clone \"{0}\"", normalPath);

            var clone = new PyRevitClone(repoPath, name: cloneName);

            var registeredClones = GetRegisteredClones();

            if (forceUpdate && registeredClones.Contains(clone))
                registeredClones.Remove(clone);

            if (!registeredClones.Contains(clone)) {
                registeredClones.Add(clone);
                SaveRegisteredClones(registeredClones);
            }
            else
                throw new pyRevitException(
                    string.Format("Clone with repo path \"{0}\" already exists.", clone.ClonePath)
                    );
        }

        // renames a clone in a configs
        // @handled @logs
        public static void RenameClone(string cloneName, string newName) {
            logger.Debug("Renaming clone \"{0}\" to \"{1}\"", cloneName, newName);
            var renamedClones = new List<PyRevitClone>();
            foreach (var clone in GetRegisteredClones()) {
                if (clone.Name == cloneName) {
                    clone.Rename(newName);
                    logger.Debug("Renamed clone \"{0}\" to \"{1}\"", cloneName, clone.Name);
                }

                renamedClones.Add(clone);
            }

            SaveRegisteredClones(renamedClones);
        }

        // unregister a clone from configs
        // @handled @logs
        public static void UnregisterClone(PyRevitClone clone) {
            logger.Debug("Unregistering clone \"{0}\"", clone);

            // remove the clone path from list
            var clones = GetRegisteredClones();
            clones.Remove(clone);
            SaveRegisteredClones(clones);
        }

        // unregister all clone from configs
        // @handled @logs
        public static void UnregisterAllClones() {
            logger.Debug("Unregistering all clones...");

            foreach (var clone in GetRegisteredClones())
                UnregisterClone(clone);
        }

        // return list of registered clones
        // @handled @logs
        public static List<PyRevitClone> GetRegisteredClones() {
            var validatedClones = new List<PyRevitClone>();

            // safely get clone list
            var clonesList = GetKeyValueAsDict(PyRevitConsts.EnvConfigsSectionName,
                                               PyRevitConsts.EnvConfigsInstalledClonesKey,
                                               defaultValue: new List<string>(),
                                               throwNotSetException: false);

            // verify all registered clones, protect against tampering
            foreach (var cloneKeyValue in clonesList) {
                var clonePath = cloneKeyValue.Value.NormalizeAsPath();
                if(CommonUtils.VerifyPath(clonePath)) {
                    try {
                        var clone = new PyRevitClone(clonePath, name: cloneKeyValue.Key);
                        if (clone.IsValid && !validatedClones.Contains(clone)) {
                            logger.Debug("Verified clone \"{0}={1}\"", clone.Name, clone.ClonePath);
                            validatedClones.Add(clone);
                        }
                    }
                    catch {
                        logger.Debug("Error occured when processing registered clone \"{0}\" at \"{1}\"", cloneKeyValue.Key, clonePath);
                    }
                }
            }

            // rewrite the verified clones list back to config file
            SaveRegisteredClones(validatedClones);

            return validatedClones;
        }

        // return requested registered clone
        // @handled @logs
        public static PyRevitClone GetRegisteredClone(string cloneNameOrRepoPath) {
            foreach (var clone in GetRegisteredClones())
                if (clone.Matches(cloneNameOrRepoPath))
                    return clone;

            throw new pyRevitException(string.Format("Can not find clone \"{0}\"", cloneNameOrRepoPath));
        }

        public static void CreateImageFromClone(PyRevitClone clone, IEnumerable<string> paths, string destPath) {
            // create paths
            var imagePath = CommonUtils.EnsureFileExtension(destPath, PyRevitConsts.ImageFileExtension);
            var targetDir = Path.Combine(Path.GetDirectoryName(imagePath), Path.GetFileNameWithoutExtension(imagePath));
            CommonUtils.EnsurePath(targetDir);

            // copy paths from clone to temp directory
            foreach(var cloneItem in paths) {
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
                compressionLevel:CompressionLevel.Optimal,
                includeBaseDirectory: true
                );

            // delete temp path
            CommonUtils.DeleteDirectory(targetDir);
        }

        // runtime ===================================================================================================
        // clear cache
        // @handled @logs
        public static void ClearCache(int revitYear) {
            // make sure all revit instances are closed
            if (CommonUtils.VerifyPath(pyRevitAppDataPath)) {
                RevitController.KillRunningRevits(revitYear);
                CommonUtils.DeleteDirectory(GetCacheDirectory(revitYear));
            }
            // it's just clearing caches. Let's not be paranoid and throw an exception is directory does not exist
            // if it's not there, the clear cache request is technically already satisfied
            //else
            //    throw new pyRevitResourceMissingException(pyRevitAppDataPath);
        }

        // clear all caches
        // @handled @logs
        public static void ClearAllCaches() {
            var cacheDirFinder = new Regex(@"\d\d\d\d");
            if (CommonUtils.VerifyPath(pyRevitAppDataPath)) {
                foreach (string subDir in Directory.GetDirectories(pyRevitAppDataPath)) {
                    var dirName = Path.GetFileName(subDir);
                    if (cacheDirFinder.IsMatch(dirName))
                        ClearCache(int.Parse(dirName));
                }
            }
            else
                throw new pyRevitResourceMissingException(pyRevitAppDataPath);
        }

        // managing extensions =======================================================================================
        private static bool CompareExtensionNames(string extName, string searchTerm) {
            var extMatcher = new Regex(searchTerm,
                                       RegexOptions.IgnoreCase | RegexOptions.IgnorePatternWhitespace);
            return extMatcher.IsMatch(extName);
        }

        // list registered extensions based on search pattern if provided, if not list all
        // @handled @logs
        public static List<PyRevitExtensionDefinition> LookupRegisteredExtensions(string searchPattern = null) {
            var matchedExtensions = new List<PyRevitExtensionDefinition>();

            // attemp to find the extension in default ext file
            try {
                matchedExtensions =
                    LookupExtensionInDefinitionFile(GetDefaultExtensionLookupSource(),
                                                    searchPattern);
            }
            catch (Exception ex) {
                logger.Error(
                    string.Format(
                        "Error looking up extension with pattern \"{0}\" in default extension source."
                        + " | {1}", searchPattern, ex.Message)
                        );
            }

            // if not found in downloaded file or downlod failed, try the additional sources
            if (matchedExtensions.Count == 0)
                foreach (var extLookupSrc in GetRegisteredExtensionLookupSources()) {
                    try {
                        // attemp to find the extension in ext lookup source
                        matchedExtensions = LookupExtensionInDefinitionFile(extLookupSrc, searchPattern);
                        if (matchedExtensions.Count > 0)
                            return matchedExtensions;
                    }
                    catch (Exception ex) {
                        logger.Error(
                            string.Format(
                                "Error looking up extension with pattern \"{0}\" in extension lookup source \"{1}\""
                                + " | {2}", searchPattern, extLookupSrc, ex.Message)
                                );
                    }
                }

            // return empty results since nothing has been found and no exception has occured
            return matchedExtensions;
        }

        // return a list of installed extensions found under registered search paths
        // @handled @logs
        public static List<PyRevitExtension> GetInstalledExtensions(string searchPath = null) {
            List<string> searchPaths;
            if (searchPath == null)
                searchPaths = GetRegisteredExtensionSearchPaths();
            else
                searchPaths = new List<string>() { searchPath };

            var installedExtensions = new List<PyRevitExtension>();
            foreach (var path in searchPaths)
                installedExtensions.AddRange(PyRevitExtension.FindExtensions(path));

            return installedExtensions;
        }

        // find extension installed under registered search paths
        // @handled @logs
        public static PyRevitExtension GetInstalledExtension(string extensionName) {
            logger.Debug("Looking up installed extension \"{0}\"...", extensionName);
            foreach (var ext in GetInstalledExtensions())
                if (CompareExtensionNames(ext.Name, extensionName)) {
                    logger.Debug(string.Format("\"{0}\" Matched installed extension \"{1}\"",
                                               extensionName, ext.Name));
                    return ext;
                }

            throw new pyRevitException(string.Format("Installed extension \"{0}\" not found.", extensionName));
        }

        // lookup registered extension by name
        // @handled @logs
        public static PyRevitExtensionDefinition FindRegisteredExtension(string extensionName) {
            logger.Debug("Looking up registered extension \"{0}\"...", extensionName);
            var matchingExts = LookupRegisteredExtensions(extensionName);
            if (matchingExts.Count == 0) {
                throw new pyRevitException(string.Format("Can not find extension \"{0}\"", extensionName));
            }
            else if (matchingExts.Count == 1) {
                logger.Debug("Extension found \"{0}\"...", matchingExts[0].Name);
                return matchingExts[0];
            }
            else if (matchingExts.Count > 1)
                Errors.LatestError = ErrorCodes.MoreThanOneItemMatched;

            return null;
        }

        // installs extension from repo url
        // @handled @logs
        public static void InstallExtension(string extensionName, PyRevitExtensionTypes extensionType,
                                            string repoPath, string destPath = null, string branchName = null) {
            // make sure extension is not installed already
            try {
                var existExt = GetInstalledExtension(extensionName);
                if (existExt != null)
                    throw new pyRevitException(string.Format("Extension \"{0}\" is already installed under \"{1}\"",
                                                             existExt.Name, existExt.InstallPath));
            }
            catch {
                // extension is not installed so everything is fine
            }

            // determine repo folder name
            // Name.extension for UI Extensions
            // Name.lib for Library Extensions
            string extDestDirName = PyRevitExtension.MakeConfigName(extensionName, extensionType);

            // determine destination
            destPath = destPath ?? pyRevitDefaultExtensionsPath;
            string finalExtRepoPath = Path.Combine(destPath, extDestDirName).NormalizeAsPath();

            // determine branch name
            branchName = branchName ?? PyRevitConsts.ExtensionRepoDefaultBranch;

            logger.Debug("Extension branch name determined as \"{0}\"", branchName);
            logger.Debug("Installing extension into \"{0}\"", finalExtRepoPath);

            // start the clone process
            var repo = GitInstaller.Clone(repoPath, branchName, finalExtRepoPath);

            // Check installation
            if (repo != null) {
                // make sure to delete the repo if error occured after cloning
                var clonedPath = repo.Info.WorkingDirectory;
                if (GitInstaller.IsValidRepo(clonedPath)) {
                    logger.Debug("Clone successful \"{0}\"", clonedPath);
                    RegisterExtensionSearchPath(destPath.NormalizeAsPath());
                }
                else {
                    logger.Debug("Invalid repo after cloning. Deleting clone \"{0}\"", repoPath);
                    try {
                        CommonUtils.DeleteDirectory(repoPath);
                    }
                    catch (Exception delEx) {
                        logger.Error(string.Format("Error post-install cleanup on \"{0}\" | {1}",
                                                   repoPath, delEx.Message));
                    }
                }
            }
            else
                throw new pyRevitException(string.Format("Error installing extension. Null repo error on \"{0}\"",
                                                         repoPath));

        }

        // installs extension
        // @handled @logs
        public static void InstallExtension(PyRevitExtensionDefinition extDef,
                                            string destPath = null, string branchName = null) {
            logger.Debug("Installing extension \"{0}\"", extDef.Name);
            InstallExtension(extDef.Name, extDef.Type, extDef.Url, destPath, branchName);
        }

        // uninstalls an extension by repo
        // @handled @logs
        public static void RemoveExtension(string repoPath, bool removeSearchPath = false) {
            if (repoPath != null) {
                logger.Debug("Uninstalling extension at \"{0}\"", repoPath);
                CommonUtils.DeleteDirectory(repoPath);
                // remove search path if requested
                if (removeSearchPath)
                    UnregisterExtensionSearchPath(Path.GetDirectoryName(Path.GetDirectoryName(repoPath)));
            }
            else
                throw new pyRevitResourceMissingException(repoPath);
        }

        // uninstalls an extension
        // @handled @logs
        public static void UninstallExtension(PyRevitExtension ext, bool removeSearchPath = false) {
            RemoveExtension(ext.InstallPath, removeSearchPath: removeSearchPath);
        }

        // uninstalls an extension by name
        // @handled @logs
        public static void UninstallExtension(string extensionName, bool removeSearchPath = false) {
            logger.Debug("Uninstalling extension \"{0}\"", extensionName);
            var ext = GetInstalledExtension(extensionName);
            RemoveExtension(ext.InstallPath, removeSearchPath: removeSearchPath);
        }

        // force update extension
        // @handled @logs
        public static void UpdateExtension(PyRevitExtension ext) {
            logger.Debug("Updating extension \"{0}\"", ext.Name);
            logger.Debug("Updating extension repo at \"{0}\"", ext.InstallPath);
            var res = GitInstaller.ForcedUpdate(ext.InstallPath);
            if (res <= UpdateStatus.Conflicts)
                throw new pyRevitException(
                    string.Format("Error updating extension \"{0}\" installed at \"{1}\"", ext.Name, ext.InstallPath)
                    );
        }

        public static void UpdateExtension(string extName) {
            var ext = GetInstalledExtension(extName);
            UpdateExtension(ext);
        }

        // force update all extensions
        // @handled @logs
        public static void UpdateAllInstalledExtensions() {
            logger.Debug("Updating all installed extensions.");
            // update all installed extensions
            foreach (var ext in GetInstalledExtensions())
                UpdateExtension(ext);
        }

        // enable extension in config
        // @handled @logs
        private static void ToggleExtension(string extName, bool state) {
            var ext = GetInstalledExtension(extName);
            logger.Debug("{0} extension \"{1}\"", state ? "Enabling" : "Disabling", ext.Name);
            SetKeyValue(ext.ConfigName, PyRevitConsts.ExtensionJsonDisabledKey, !state);
        }

        // disable extension in config
        // @handled @logs
        public static void EnableExtension(string extName) {
            ToggleExtension(extName, true);
        }

        // disable extension in config
        // @handled @logs
        public static void DisableExtension(string extName) {
            ToggleExtension(extName, false);
        }

        // get list of registered extension search paths
        // @handled @logs
        public static List<string> GetRegisteredExtensionSearchPaths() {
            var validatedPaths = new List<string>();
            var searchPaths = GetKeyValueAsList(PyRevitConsts.ConfigsCoreSection,
                                                PyRevitConsts.ConfigsUserExtensionsKey);
            // make sure paths exist
            foreach (var path in searchPaths) {
                var normPath = path.NormalizeAsPath();
                if (CommonUtils.VerifyPath(path) && !validatedPaths.Contains(normPath)) {
                    logger.Debug("Verified extension search path \"{0}\"", normPath);
                    validatedPaths.Add(normPath);
                }
            }

            // rewrite verified list
            SetKeyValue(PyRevitConsts.ConfigsCoreSection,
                        PyRevitConsts.ConfigsUserExtensionsKey,
                        validatedPaths);

            return validatedPaths;
        }

        // add extension search path
        // @handled @logs
        public static void RegisterExtensionSearchPath(string searchPath) {
            if (CommonUtils.VerifyPath(searchPath)) {
                logger.Debug("Adding extension search path \"{0}\"", searchPath);
                var searchPaths = GetRegisteredExtensionSearchPaths();
                searchPaths.Add(searchPath.NormalizeAsPath());
                SetKeyValue(PyRevitConsts.ConfigsCoreSection,
                            PyRevitConsts.ConfigsUserExtensionsKey,
                            searchPaths);
            }
            else
                throw new pyRevitResourceMissingException(searchPath);
        }

        // remove extension search path
        // @handled @logs
        public static void UnregisterExtensionSearchPath(string searchPath) {
            var normPath = searchPath.NormalizeAsPath();
            logger.Debug("Removing extension search path \"{0}\"", normPath);
            var searchPaths = GetRegisteredExtensionSearchPaths();
            searchPaths.Remove(normPath);
            SetKeyValue(PyRevitConsts.ConfigsCoreSection,
                        PyRevitConsts.ConfigsUserExtensionsKey,
                        searchPaths);
        }

        // managing extension sources ================================================================================
        // get default extension lookup source
        // @handled @logs
        public static string GetDefaultExtensionLookupSource() {
            return PyRevitConsts.ExtensionsDefinitionFileUri;
        }

        // get extension lookup sources
        // @handled @logs
        public static List<string> GetRegisteredExtensionLookupSources() {
            var sources = GetKeyValueAsList(PyRevitConsts.EnvConfigsSectionName,
                                            PyRevitConsts.EnvConfigsExtensionLookupSourcesKey,
                                            throwNotSetException: false);
            var normSources = new List<string>();
            foreach (var src in sources) {
                var normSrc = src.NormalizeAsPath();
                logger.Debug("Extension lookup source \"{0}\"", normSrc);
                normSources.Add(normSrc);
            }
            return normSources;
        }

        // register new extension lookup source
        // @handled @logs
        public static void RegisterExtensionLookupSource(string extLookupSource) {
            var normSource = extLookupSource.NormalizeAsPath();
            var sources = GetRegisteredExtensionLookupSources();
            if (!sources.Contains(normSource)) {
                logger.Debug("Registering extension lookup source \"{0}\"", normSource);
                sources.Add(normSource);
                SaveExtensionLookupSources(sources);
            }
            else
                logger.Debug("Extension lookup source already exists. Skipping registration.");
        }

        // unregister extension lookup source
        // @handled @logs
        public static void UnregisterExtensionLookupSource(string extLookupSource) {
            var normSource = extLookupSource.NormalizeAsPath();
            var sources = GetRegisteredExtensionLookupSources();
            if (sources.Contains(normSource)) {
                logger.Debug("Unregistering extension lookup source \"{0}\"", normSource);
                sources.Remove(normSource);
                SaveExtensionLookupSources(sources);
            }
            else
                logger.Debug("Extension lookup source does not exist. Skipping unregistration.");
        }

        // unregister all extension lookup sources
        // @handled @logs
        public static void UnregisterAllExtensionLookupSources() {
            foreach (var src in GetRegisteredExtensionLookupSources())
                UnregisterExtensionLookupSource(src);
        }

        // managing configs ==========================================================================================
        // pyrevit config getter/setter
        // usage logging config
        // @handled @logs
        public static string FindConfigFileInDirectory(string sourcePath) {
            var configMatcher = new Regex(PyRevitConsts.ConfigsFileRegexPattern, RegexOptions.IgnoreCase);
            if (CommonUtils.VerifyPath(sourcePath))
                foreach (string subFile in Directory.GetFiles(sourcePath))
                    if (configMatcher.IsMatch(Path.GetFileName(subFile)))
                        return subFile;
            return null;
        }

        public static bool GetUsageReporting() {
            return bool.Parse(GetKeyValue(PyRevitConsts.ConfigsUsageLoggingSection,
                                          PyRevitConsts.ConfigsUsageLoggingStatusKey));
        }

        public static string GetUsageLogFilePath() {
            return GetKeyValue(PyRevitConsts.ConfigsUsageLoggingSection,
                               PyRevitConsts.ConfigsUsageLogFilePathKey);
        }

        public static string GetUsageLogServerUrl() {
            return GetKeyValue(PyRevitConsts.ConfigsUsageLoggingSection,
                               PyRevitConsts.ConfigsUsageLogServerUrlKey);
        }

        public static void EnableUsageReporting(string logFilePath = null, string logServerUrl = null) {
            logger.Debug(string.Format("Enabling usage logging... path: \"{0}\" server: {1}",
                                       logFilePath, logServerUrl));
            SetKeyValue(PyRevitConsts.ConfigsUsageLoggingSection,
                        PyRevitConsts.ConfigsUsageLoggingStatusKey,
                        true);

            if (logFilePath != null)
                if (CommonUtils.VerifyPath(logFilePath))
                    SetKeyValue(PyRevitConsts.ConfigsUsageLoggingSection,
                                PyRevitConsts.ConfigsUsageLogFilePathKey,
                                logFilePath);
                else
                    logger.Debug("Invalid log path \"{0}\"", logFilePath);

            if (logServerUrl != null)
                SetKeyValue(PyRevitConsts.ConfigsUsageLoggingSection,
                            PyRevitConsts.ConfigsUsageLogServerUrlKey,
                            logServerUrl);
        }

        public static void DisableUsageReporting() {
            logger.Debug("Disabling usage reporting...");
            SetKeyValue(PyRevitConsts.ConfigsUsageLoggingSection,
                        PyRevitConsts.ConfigsUsageLoggingStatusKey,
                        false);
        }

        // update checking config
        // @handled @logs
        public static bool GetCheckUpdates() {
            return bool.Parse(GetKeyValue(PyRevitConsts.ConfigsCoreSection,
                                             PyRevitConsts.ConfigsCheckUpdatesKey));
        }

        public static void SetCheckUpdates(bool state) {
            SetKeyValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsCheckUpdatesKey, state);
        }

        // auto update config
        // @handled @logs
        public static bool GetAutoUpdate() {
            return bool.Parse(GetKeyValue(PyRevitConsts.ConfigsCoreSection,
                                          PyRevitConsts.ConfigsAutoUpdateKey));
        }

        public static void SetAutoUpdate(bool state) {
            SetKeyValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsAutoUpdateKey, state);
        }

        // rocket mode config
        // @handled @logs
        public static bool GetRocketMode() {
            return bool.Parse(GetKeyValue(PyRevitConsts.ConfigsCoreSection,
                                          PyRevitConsts.ConfigsRocketModeKey));
        }

        public static void SetRocketMode(bool state) {
            SetKeyValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsRocketModeKey, state);
        }

        // logging level config
        // @handled @logs
        public static PyRevitLogLevels GetLoggingLevel() {
            bool verbose = bool.Parse(GetKeyValue(PyRevitConsts.ConfigsCoreSection,
                                                  PyRevitConsts.ConfigsVerboseKey));
            bool debug = bool.Parse(GetKeyValue(PyRevitConsts.ConfigsCoreSection,
                                                PyRevitConsts.ConfigsDebugKey));

            if (verbose && !debug)
                return PyRevitLogLevels.Verbose;
            else if (debug)
                return PyRevitLogLevels.Debug;

            return PyRevitLogLevels.None;
        }

        public static void SetLoggingLevel(PyRevitLogLevels level) {
            if (level == PyRevitLogLevels.None) {
                SetKeyValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsVerboseKey, false);
                SetKeyValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsDebugKey, false);
            }

            if (level == PyRevitLogLevels.Verbose) {
                SetKeyValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsVerboseKey, true);
                SetKeyValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsDebugKey, false);
            }

            if (level == PyRevitLogLevels.Debug) {
                SetKeyValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsVerboseKey, true);
                SetKeyValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsDebugKey, true);
            }
        }

        // file logging config
        // @handled @logs
        public static bool GetFileLogging() {
            return bool.Parse(GetKeyValue(PyRevitConsts.ConfigsCoreSection,
                                          PyRevitConsts.ConfigsFileLoggingKey));
        }

        public static void SetFileLogging(bool state) {
            SetKeyValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsFileLoggingKey, state);
        }

        // load beta config
        // @handled @logs
        public static bool GetLoadBetaTools() {
            return bool.Parse(GetKeyValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsLoadBetaKey));
        }

        public static void SetLoadBetaTools(bool state) {
            SetKeyValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsLoadBetaKey, state);
        }

        // output style sheet config
        // @handled @logs
        public static string GetOutputStyleSheet() {
            return GetKeyValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsOutputStyleSheet);
        }

        public static void SetOutputStyleSheet(string outputCSSFilePath) {
            if (File.Exists(outputCSSFilePath))
                SetKeyValue(PyRevitConsts.ConfigsCoreSection,
                            PyRevitConsts.ConfigsOutputStyleSheet,
                            outputCSSFilePath);
        }

        // user access to tools
        // @handled @logs
        public static bool GetUserCanUpdate() {
            return bool.Parse(GetKeyValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsUserCanUpdateKey));
        }

        public static bool GetUserCanExtend() {
            return bool.Parse(GetKeyValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsUserCanExtendKey));
        }

        public static bool GetUserCanConfig() {
            return bool.Parse(GetKeyValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsUserCanConfigKey));
        }

        public static void SetUserCanUpdate(bool state) {
            SetKeyValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsUserCanUpdateKey, state);
        }

        public static void SetUserCanExtend(bool state) {
            SetKeyValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsUserCanExtendKey, state);
        }

        public static void SetUserCanConfig(bool state) {
            SetKeyValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsUserCanConfigKey, state);
        }

        // deletes config file
        // @handled @logs
        public static void DeleteConfigs() {
            if (File.Exists(pyRevitConfigFilePath))
                try {
                    File.Delete(pyRevitConfigFilePath);
                }
                catch (Exception ex) {
                    throw new pyRevitException(string.Format("Failed deleting config file \"{0}\" | {1}",
                                                              pyRevitConfigFilePath, ex.Message));
                }
        }

        // generic configuration public access  ======================================================================
        // @handled @logs
        public static string GetConfig(string sectionName, string keyName) {
            return GetKeyValue(sectionName, keyName);
        }

        // @handled @logs
        public static void SetConfig(string sectionName, string keyName, bool boolValue) {
            SetKeyValue(sectionName, keyName, boolValue);
        }

        // @handled @logs
        public static void SetConfig(string sectionName, string keyName, int intValue) {
            SetKeyValue(sectionName, keyName, intValue);
        }

        // @handled @logs
        public static void SetConfig(string sectionName, string keyName, string stringValue) {
            SetKeyValue(sectionName, keyName, stringValue);
        }

        // @handled @logs
        public static void SetConfig(string sectionName, string keyName, IEnumerable<string> stringListValue) {
            SetKeyValue(sectionName, keyName, stringListValue);
        }

        // copy config file into all users directory as seed config file
        // create user config file based on a template
        // @handled @logs
        public static void SeedConfig(bool makeCurrentUserAsOwner = false, string setupFromTemplate = null) {
            // if setupFromTemplate is not specified: copy current config into Allusers folder
            // if setupFromTemplate is specified: copy setupFromTemplate as the main config
            string sourceFile = setupFromTemplate != null ? setupFromTemplate : pyRevitConfigFilePath;
            string targetFile = setupFromTemplate != null ? pyRevitConfigFilePath : pyRevitSeedConfigFilePath;

            logger.Debug("Seeding config file \"{0}\" to \"{1}\"", sourceFile, targetFile);

            try {
                if (File.Exists(sourceFile)) {
                    CommonUtils.EnsureFile(targetFile);
                    File.Copy(sourceFile, targetFile, true);

                    if (makeCurrentUserAsOwner) {
                        var fs = File.GetAccessControl(targetFile);
                        var currentUser = WindowsIdentity.GetCurrent();
                        try {
                            CommonUtils.SetFileSecurity(targetFile, currentUser.Name);
                        }
                        catch (InvalidOperationException ex) {
                            logger.Error(
                                string.Format(
                                    "You cannot assign ownership to user \"{0}\"." +
                                    "Either you don't have TakeOwnership permissions, " +
                                    "or it is not your user account. | {1}", currentUser.Name, ex.Message
                                    )
                            );
                        }
                    }
                }
            }
            catch (Exception ex) {
                throw new pyRevitException(string.Format("Failed seeding config file. | {0}", ex.Message));
            }
        }

        // configurations private access methods  ====================================================================
        private static void InitConfigFile() {
            // get allusers seed config file
            var adminFile = FindConfigFileInDirectory(pyRevitProgramDataPath);
            if (adminFile != null)
                SeedConfig(false, setupFromTemplate: adminFile);
            else
                CommonUtils.EnsureFile(pyRevitConfigFilePath);
        }

        private static IniFile GetConfigFile() {
            // INI formatting
            var cfgOps = new IniOptions();
            cfgOps.KeySpaceAroundDelimiter = true;
            cfgOps.Encoding = CommonUtils.GetUTF8NoBOMEncoding();
            IniFile cfgFile = new IniFile(cfgOps);

            // default to current user config
            string configFile = pyRevitConfigFilePath;
            // make sure the file exists and if not create an empty one
            if (!CommonUtils.VerifyFile(configFile))
                InitConfigFile();

            // load the config file
            cfgFile.Load(configFile);
            return cfgFile;
        }

        // save config file to standard location
        // @handled @logs
        private static void SaveConfigFile(IniFile cfgFile) {
            logger.Debug("Saving config file \"{0}\"", pyRevitConfigFilePath);
            try {
                cfgFile.Save(pyRevitConfigFilePath);
            }
            catch (Exception ex) {
                throw new pyRevitException(string.Format("Failed to save config to \"{0}\". | {1}",
                                                         pyRevitConfigFilePath, ex.Message));
            }
        }

        // get config key value
        // @handled @logs
        private static string GetKeyValue(string sectionName,
                                          string keyName,
                                          string defaultValue = null,
                                          bool throwNotSetException = true) {
            var c = GetConfigFile();
            logger.Debug(string.Format("Try getting config \"{0}:{1}\" ?? {2}",
                                       sectionName, keyName, defaultValue ?? "NULL"));
            if (c.Sections.Contains(sectionName) && c.Sections[sectionName].Keys.Contains(keyName))
                return c.Sections[sectionName].Keys[keyName].Value as string;
            else {
                if (defaultValue == null && throwNotSetException)
                    throw new pyRevitConfigValueNotSet(sectionName, keyName);
                else {
                    logger.Debug(string.Format("Config is not set. Returning default value \"{0}\"",
                                               defaultValue ?? "NULL"));
                    return defaultValue;
                }
            }
        }

        // get config key value and make a string list out of it
        // @handled @logs
        private static List<string> GetKeyValueAsList(string sectionName,
                                                      string keyName,
                                                      bool throwNotSetException = true) {
            logger.Debug("Try getting config as list \"{0}:{1}\"", sectionName, keyName);
            var stringValue = GetKeyValue(sectionName, keyName, "[]", throwNotSetException: throwNotSetException);

            return stringValue.ConvertFromTomlListString();
        }

        // get config key value and make a string dictionary out of it
        // @handled @logs
        private static Dictionary<string, string> GetKeyValueAsDict(string sectionName,
                                                                    string keyName,
                                                                    IEnumerable<string> defaultValue = null,
                                                                    bool throwNotSetException = true) {
            logger.Debug("Try getting config as dict \"{0}:{1}\"", sectionName, keyName);
            var stringValue = GetKeyValue(sectionName,
                                          keyName, defaultValue: "{}",
                                          throwNotSetException: throwNotSetException);
            return stringValue.ConvertFromTomlDictString();
        }

        // updates config key value, creates the config if not set yet
        // @handled @logs
        private static void UpdateKeyValue(string sectionName, string keyName, string stringValue) {
            if (stringValue != null) {
                var c = GetConfigFile();

                if (!c.Sections.Contains(sectionName)) {
                    logger.Debug("Adding config section \"{0}\"", sectionName);
                    c.Sections.Add(sectionName);
                }

                if (!c.Sections[sectionName].Keys.Contains(keyName)) {
                    logger.Debug("Adding config key \"{0}:{1}\"", sectionName, keyName);
                    c.Sections[sectionName].Keys.Add(keyName);
                }

                logger.Debug("Updating config \"{0}:{1} = {2}\"", sectionName, keyName, stringValue);
                c.Sections[sectionName].Keys[keyName].Value = stringValue;

                SaveConfigFile(c);
            }
            else
                logger.Debug("Can not set null value for \"{0}:{1}\"", sectionName, keyName);
        }

        // sets config key value as bool
        // @handled @logs
        private static void SetKeyValue(string sectionName, string keyName, bool boolValue) {
            UpdateKeyValue(sectionName, keyName, boolValue.ConvertToTomlBoolString());
        }

        // sets config key value as int
        // @handled @logs
        private static void SetKeyValue(string sectionName, string keyName, int intValue) {
            UpdateKeyValue(sectionName, keyName, intValue.ConvertToTomlIntString());
        }

        // sets config key value as string
        // @handled @logs
        private static void SetKeyValue(string sectionName, string keyName, string stringValue) {
            UpdateKeyValue(sectionName, keyName, stringValue.ConvertToTomlString());
        }

        // sets config key value as string list
        // @handled @logs
        private static void SetKeyValue(string sectionName, string keyName, IEnumerable<string> listString) {
            UpdateKeyValue(sectionName, keyName, listString.ConvertToTomlListString());
        }

        // sets config key value as string dictionary
        // @handled @logs
        private static void SetKeyValue(string sectionName, string keyName, IDictionary<string, string> dictString) {
            UpdateKeyValue(sectionName, keyName, dictString.ConvertToTomlDictString());
        }

        // updates the config value for registered clones
        // @handled @logs
        private static void SaveRegisteredClones(IEnumerable<PyRevitClone> clonesList) {
            var newValueDic = new Dictionary<string, string>();
            foreach (var clone in clonesList)
                newValueDic[clone.Name] = clone.ClonePath;

            SetKeyValue(PyRevitConsts.EnvConfigsSectionName,
                        PyRevitConsts.EnvConfigsInstalledClonesKey,
                        newValueDic);
        }

        // updates the config value for extensions lookup sources
        // @handled @logs
        private static void SaveExtensionLookupSources(IEnumerable<string> sourcesList) {
            SetKeyValue(PyRevitConsts.EnvConfigsSectionName,
                        PyRevitConsts.EnvConfigsExtensionLookupSourcesKey,
                        sourcesList);
        }

        // other private helprs  =====================================================================================
        // find extension with search patten in extension lookup resource (file or url to a remote file)
        // @handled @logs
        private static List<PyRevitExtensionDefinition> LookupExtensionInDefinitionFile(
                string fileOrUri,
                string searchPattern = null) {

            var pyrevtExts = new List<PyRevitExtensionDefinition>();
            string filePath = null;

            // determine if path is file or uri
            logger.Debug("Determining file or remote source \"{0}\"", fileOrUri);
            Uri uriResult;
            var validPath = Uri.TryCreate(fileOrUri, UriKind.Absolute, out uriResult);
            if (validPath) {
                if (uriResult.IsFile) {
                    filePath = fileOrUri;
                    logger.Debug("Source is a file \"{0}\"", filePath);
                }
                else if (uriResult.HostNameType == UriHostNameType.Dns
                            || uriResult.HostNameType == UriHostNameType.IPv4
                            || uriResult.HostNameType == UriHostNameType.IPv6) {

                    logger.Debug("Source is a remote resource \"{0}\"", fileOrUri);
                    logger.Debug("Downloading remote resource \"{0}\"...", fileOrUri);
                    // download the resource into TEMP
                    try {
                        filePath =
                            CommonUtils.DownloadFile(fileOrUri,
                                                     Path.Combine(Environment.GetEnvironmentVariable("TEMP"),
                                                                  PyRevitConsts.EnvConfigsExtensionDBFileName)
                            );
                    }
                    catch (Exception ex) {
                        throw new pyRevitException(
                            string.Format("Error downloading extension metadata file. | {0}", ex.Message)
                            );
                    }
                }
            }
            else
                throw new pyRevitException(
                    string.Format("Source is not a valid file or remote resource \"{0}\"", fileOrUri)
                    );

            // process file now
            if (filePath != null) {
                if (Path.GetExtension(filePath).ToLower() == ".json") {
                    logger.Debug("Parsing extension metadata file...");

                    dynamic extensionsObj;
                    if (filePath != null) {
                        try {
                            extensionsObj = JObject.Parse(File.ReadAllText(filePath));
                        }
                        catch (Exception ex) {
                            throw new pyRevitException(string.Format("Error parsing extension metadata. | {0}", ex.Message));
                        }

                        // make extension list
                        foreach (JObject extObj in extensionsObj.extensions) {
                            var extDef = new PyRevitExtensionDefinition(extObj);

                            logger.Debug("Registered extension \"{0}\"", extDef.Name);
                            if (searchPattern != null) {
                                if (CompareExtensionNames(extDef.Name, searchPattern)) {
                                    logger.Debug(string.Format("\"{0}\" Matched registered extension \"{1}\"",
                                                               searchPattern, extDef.Name));
                                    pyrevtExts.Add(extDef);
                                }
                            }
                            else
                                pyrevtExts.Add(extDef);
                        }
                    }
                }
                else
                    throw new pyRevitException(
                        string.Format("Definition file is not a valid json file \"{0}\"", filePath)
                        );
            }

            return pyrevtExts;
        }
    }
}
