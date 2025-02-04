using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Linq;

using pyRevitLabs.Common;
using pyRevitLabs.Common.Extensions;
using pyRevitLabs.NLog;

namespace pyRevitLabs.PyRevit
{
    public class pyRevitInvalidPyRevitCloneException : pyRevitInvalidGitCloneException
    {
        public pyRevitInvalidPyRevitCloneException() { }

        public pyRevitInvalidPyRevitCloneException(string invalidClonePath) : base(invalidClonePath) { }

        public override string Message
        {
            get
            {
                return string.Format("Path \"{0}\" is not a valid git pyRevit clone.", Path);
            }
        }
    }

    public static class PyRevitClones
    {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        // managing clones ===========================================================================================
        // clones are git clones. pyRevit module likes to know about available clones to
        // perform operations on (switching engines, clones, uninstalling, ...)

        // register a clone in a configs
        // @handled @logs
        public static void RegisterClone(string cloneName, string repoPath, bool forceUpdate = false)
        {
            var normalPath = repoPath.NormalizeAsPath();
            logger.Debug("Registering clone \"{0}\"", normalPath);

            var clone = new PyRevitClone(repoPath, name: cloneName);

            var registeredClones = GetRegisteredClones();

            if (forceUpdate && registeredClones.Contains(clone))
                registeredClones.Remove(clone);

            if (!registeredClones.Contains(clone))
            {
                registeredClones.Add(clone);
                SaveRegisteredClones(registeredClones);
            }
            else
                throw new PyRevitException(
                    string.Format("Clone with repo path \"{0}\" already exists.", clone.ClonePath)
                    );
        }

        // renames a clone in a configs
        // @handled @logs
        public static void RenameClone(string cloneName, string newName)
        {
            logger.Debug("Renaming clone \"{0}\" to \"{1}\"", cloneName, newName);
            var renamed = false;
            var renamedClones = new List<PyRevitClone>();
            foreach (var clone in GetRegisteredClones())
            {
                if (clone.Name == cloneName)
                {
                    clone.Rename(newName);
                    logger.Debug("Renamed clone \"{0}\" to \"{1}\"", cloneName, clone.Name);
                    renamed = true;
                }
                renamedClones.Add(clone);
            }
            if (renamed)
            {
                SaveRegisteredClones(renamedClones);
            }
        }

        // unregister a clone from configs
        // @handled @logs
        public static void UnregisterClone(PyRevitClone clone)
        {
            logger.Debug("Unregistering clone \"{0}\"", clone);

            // remove the clone path from list
            var clones = GetRegisteredClones();
            if (clones.Remove(clone))
            {
                SaveRegisteredClones(clones);
            }
        }

        // unregister all clone from configs
        // @handled @logs
        public static void UnregisterAllClones()
        {
            logger.Debug("Unregistering all clones...");

            foreach (var clone in GetRegisteredClones())
                UnregisterClone(clone);
        }

        // return list of registered clones
        // @handled @logs
        public static List<PyRevitClone> GetRegisteredClones()
        {
            // safely get clone list
            var cfg = PyRevitConfigs.GetConfigFile();
            var clonesDict = cfg.GetDictValue(PyRevitConsts.EnvConfigsSectionName, PyRevitConsts.EnvConfigsInstalledClonesKey);

            var validatedClones = new List<PyRevitClone>();
            if (clonesDict is null)
            {
                return validatedClones;
            }
            var listChanged = false;
            // verify all registered clones, protect against tampering
            foreach (var cloneKeyValue in clonesDict)
            {
                var clonePath = cloneKeyValue.Value.NormalizeAsPath();
                if (!CommonUtils.VerifyPath(clonePath))
                {
                    listChanged = true;
                    continue;
                }
                if (clonePath != cloneKeyValue.Value)
                {
                    listChanged = true;
                }
                try
                {
                    var clone = new PyRevitClone(clonePath, name: cloneKeyValue.Key);
                    if (clone.IsValid && !validatedClones.Contains(clone))
                    {

                        logger.Debug("Verified clone \"{0}={1}\"", clone.Name, clone.ClonePath);
                        validatedClones.Add(clone);
                    }
                }
                catch
                {
                    logger.Debug("Error occured when processing registered clone \"{0}\" at \"{1}\"", cloneKeyValue.Key, clonePath);
                }
            }
            if (listChanged)
            {
                // rewrite the verified clones list back to config file
                SaveRegisteredClones(validatedClones);
            }
            return validatedClones;
        }

        // return requested registered clone
        // @handled @logs
        public static PyRevitClone GetRegisteredClone(string cloneNameOrRepoPath)
        {
            foreach (var clone in GetRegisteredClones())
                if (clone.Matches(cloneNameOrRepoPath))
                    return clone;

            throw new PyRevitException(string.Format("Can not find clone \"{0}\"", cloneNameOrRepoPath));
        }

        public static void CreateImageFromClone(PyRevitClone clone, IEnumerable<string> paths, string destPath)
        {
            // create paths
            var imagePath = CommonUtils.EnsureFileExtension(destPath, GithubAPI.ArchiveFileExtension);
            var targetDir = Path.Combine(Path.GetDirectoryName(imagePath), Path.GetFileNameWithoutExtension(imagePath));
            CommonUtils.EnsurePath(targetDir);

            // copy paths from clone to temp directory
            foreach (var cloneItem in paths)
            {
                var srcItem = Path.Combine(clone.ClonePath, cloneItem);
                var destItem = Path.Combine(targetDir, cloneItem);
                if (File.Exists(srcItem))
                {
                    // then copy and overwrite
                    File.Copy(srcItem, destItem, overwrite: true);
                }
                // otherwise it must be a directory
                else
                {
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
        public static bool IsAtLeastOneClones()
        {
            return GetRegisteredClones().Count > 0;
        }

        // install pyRevit by cloning from git repo
        // @handled @logs
        public static void DeployFromRepo(string cloneName,
                                          string deploymentName = null,
                                          string branchName = null,
                                          string repoUrl = null,
                                          string destPath = null,
                                          GitInstallerCredentials credentials = null)
        {
            string repoSourcePath = repoUrl ?? PyRevitLabsConsts.OriginalRepoGitPath;
            string repoBranch = branchName != null ? branchName : PyRevitLabsConsts.TargetBranch;
            logger.Debug("Repo source determined as \"{0}:{1}\"", repoSourcePath, repoBranch);

            // determine destination path if not provided
            if (destPath is null)
                destPath = Path.Combine(PyRevitLabsConsts.PyRevitPath, PyRevitConsts.DefaultCloneInstallName);
            logger.Debug("Destination path determined as \"{0}\"", destPath);
            // make sure destPath exists
            CommonUtils.EnsurePath(destPath);

            // check existing destination path
            if (CommonUtils.VerifyPath(destPath))
            {
                logger.Debug("Destination path already exists {0}", destPath);
                destPath = Path.Combine(destPath, cloneName);
                logger.Debug("Using subpath {0}", destPath);
                if (CommonUtils.VerifyPath(destPath))
                    throw new PyRevitException(string.Format("Destination path already exists \"{0}\"", destPath));
            }

            // start the clone process
            LibGit2Sharp.Repository repo = null;
            if (deploymentName != null)
            {
                // TODO: Add core checkout option. Figure out how to checkout certain folders in libgit2sharp
                throw new NotImplementedException("Deployment with git clones not implemented yet.");
            }
            else
            {
                repo = GitInstaller.Clone(repoSourcePath, repoBranch, destPath, credentials);
            }

            // Check installation
            if (repo != null)
            {
                // make sure to delete the repo if error occured after cloning
                var clonedPath = repo.Info.WorkingDirectory;
                try
                {
                    PyRevitClone.VerifyCloneValidity(clonedPath);
                    logger.Debug("Clone successful \"{0}\"", clonedPath);
                    RegisterClone(cloneName, clonedPath);
                }
                catch (Exception ex)
                {
                    logger.Debug(string.Format("Exception occured after clone complete. Deleting clone \"{0}\" | {1}",
                                               clonedPath, ex.Message));
                    try
                    {
                        CommonUtils.DeleteDirectory(clonedPath);
                    }
                    catch (Exception delEx)
                    {
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

        public static void DeployFromImage(string cloneName,
                                           string deploymentName = null,
                                           string branchName = null,
                                           string imagePath = null,
                                           string destPath = null)
        {
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
            if (CommonUtils.VerifyPath(destPath))
            {
                destPath = destPath.NormalizeAsPath();
                logger.Debug("Destination path already exists {0}", destPath);
                destPath = Path.Combine(destPath, cloneName);
                logger.Debug("Using subpath {0}", destPath);
                if (CommonUtils.VerifyPath(destPath))
                    throw new PyRevitException(string.Format("Destination path already exists \"{0}\"", destPath));
            }

            logger.Debug("Destination path determined as \"{0}\"", destPath);

            // process source
            // decide to download if source is a url
            if (imageSource.IsValidHttpUrl())
            {
                try
                {
                    var pkgDest = Path.Combine(Environment.GetEnvironmentVariable("TEMP"), Path.GetFileName(imageSource));
                    logger.Info("Downloading package \"{0}\"", imageSource);
                    logger.Debug("Downloading package \"{0}\" to \"{1}\"", imageSource, pkgDest);
                    imageFilePath =
                        CommonUtils.DownloadFile(imageSource, pkgDest);
                    logger.Debug("Downloaded to \"{0}\"", imageFilePath);
                }
                catch (Exception ex)
                {
                    throw new PyRevitException(
                        string.Format("Error downloading repo image file \"{0}\" | {1}", imageSource, ex.Message)
                        );
                }
            }
            // otherwise check if the source is a file and exists
            else if (CommonUtils.VerifyFile(imageSource))
            {
                imageFilePath = imageSource;
            }
            // otherwise the source format is unknown
            else
            {
                throw new PyRevitException(string.Format("Unknown source \"{0}\"", imageSource));
            }

            // now extract the file
            if (imageFilePath == null)
            {
                throw new PyRevitException(
                    string.Format("Unknown error occured getting package from \"{0}\"", imageSource)
                    );
            }
            var stagedImage = Path.Combine(
                Environment.GetEnvironmentVariable("TEMP"),
                Path.GetFileNameWithoutExtension(imageFilePath)
                );

            // delete existing
            if (CommonUtils.VerifyPath(stagedImage))
            {
                logger.Debug("Deleting existing temp staging path \"{0}\"", stagedImage);
                CommonUtils.DeleteDirectory(stagedImage);
            }

            // unpack image
            logger.Info("Preparing package for deployment...");

            try
            {
                logger.Debug("Staging package to \"{0}\"", stagedImage);
                ZipFile.ExtractToDirectory(imageFilePath, stagedImage);
                if (Directory.GetFiles(stagedImage).Length == 0)
                {
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
            catch (Exception ex)
            {
                throw new PyRevitException(
                    string.Format("Error unpacking \"{0}\" | {1}", imageFilePath, ex.Message)
                    );
            }

            // make a pyrevit clone and handle deployment
            try
            {
                var clone = new PyRevitClone(stagedImage);

                // deployment: copy the needed directories
                logger.Info("Deploying to \"{0}\"", destPath);

                if (deploymentName != null)
                {
                    // deploy the requested deployment
                    // throws exceptions if deployment does not exist or on copy error
                    Deploy(clone.ClonePath, deploymentName, destPath);
                }
                else
                {
                    logger.Debug("Deploying complete clone from image...");
                    CommonUtils.CopyDirectory(clone.ClonePath, destPath);
                }

                // cleanup temp files
                logger.Debug("Cleaning up temp files after clone from image...");
                try
                {
                    CommonUtils.DeleteDirectory(stagedImage);
                }
                catch (Exception delEx)
                {
                    logger.Error(string.Format("Error cleaning up temp staging files \"{0}\" | {1}",
                                               destPath, delEx.Message));
                }

                // record image deployment settings
                try
                {
                    RecordDeploymentArgs(cloneName, deploymentName, branchName, imageSource, destPath);
                }
                catch (Exception ex)
                {
                    logger.Debug(string.Format("Exception occured after clone from image complete. " +
                                               "Deleting clone \"{0}\" | {1}", destPath, ex.Message));
                    try
                    {
                        CommonUtils.DeleteDirectory(destPath);
                    }
                    catch (Exception delEx)
                    {
                        logger.Error(string.Format("Error post-install cleanup on \"{0}\" | {1}",
                                                   destPath, delEx.Message));
                    }

                    // cleanup completed, now baloon up the exception
                    throw;
                }

                // register the clone
                VerifyAndRegisterClone(cloneName, destPath);

                logger.Info("Package deployed and registered.");
            }
            catch (PyRevitException ex)
            {
                logger.Error("Can not find a valid clone inside extracted package. | {0}", ex.Message);
            }
        }

        // test clone validity and register
        // @handled @logs
        private static void VerifyAndRegisterClone(string cloneName, string clonePath)
        {
            try
            {
                PyRevitClone.VerifyCloneValidity(clonePath);
                logger.Debug("Clone successful \"{0}\"", clonePath);
                RegisterClone(cloneName, clonePath);
            }
            catch (Exception ex)
            {
                logger.Debug(string.Format("Exception occured after clone complete. Deleting clone \"{0}\" | {1}",
                                           clonePath, ex.Message));
                try
                {
                    CommonUtils.DeleteDirectory(clonePath);
                }
                catch (Exception delEx)
                {
                    logger.Error(string.Format("Error post-install cleanup on \"{0}\" | {1}",
                                               clonePath, delEx.Message));
                }

                // cleanup completed, now baloon up the exception
                throw;
            }
        }

        // private helper to deploy destination location by name
        // @handled
        private static void Deploy(string fromPath, string deploymentName, string destPath)
        {
            if (!PyRevitClone.VerifyHasDeployments(fromPath))
                throw new PyRevitException("There are no deployments configured.");

            var validDeployments = PyRevitClone.GetConfiguredDeployments(fromPath);
            foreach (var dep in validDeployments)
            {
                // compare lowercase deployment names
                if (dep.Name.ToLower() == deploymentName.ToLower())
                {
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
        private static void Deploy(string imagePath, PyRevitDeployment deployment, string destPath)
        {
            logger.Debug("Deploying from \"{0}\"", deployment.Name);
            foreach (var depPath in deployment.Paths)
            {
                var depSrcPath = Path.Combine(imagePath, depPath);
                var depDestPath = Path.Combine(destPath, depPath);

                // if source is a file
                if (File.Exists(depSrcPath))
                {
                    // then copy and overwrite
                    File.Copy(depSrcPath, depDestPath, overwrite: true);
                }
                // otherwise it must be a directory
                else
                {
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
                                                 string clonePath)
        {
            var cloneMemoryFilePath = Path.Combine(clonePath, PyRevitConsts.DeployFromImageConfigsFilename);
            logger.Debug(string.Format("Recording deploy parameters for image clone \"{0}\" to \"{1}\"",
                                       cloneName, cloneMemoryFilePath));

            try
            {
                var f = File.CreateText(cloneMemoryFilePath);
                f.WriteLine(imagePath);
                f.WriteLine(branchName);
                f.WriteLine(deploymentName);
                f.Close();
            }
            catch (Exception ex)
            {
                throw new PyRevitException(string.Format("Error writing deployment arguments to \"{0}\" | {1}",
                                                         cloneMemoryFilePath, ex.Message));
            }
        }

        private static void ReDeployClone(PyRevitClone clone, GitInstallerCredentials credentials)
        {
            // grab clone arguments from inside of clone
            var cloneName = clone.Name;
            var clonePath = clone.ClonePath;
            var cloneDeployArgs = clone.DeploymentArgs;
            logger.Debug("Clone Name=\"{0}\", Path=\"{1}\" Args=> {2}", cloneName, clonePath, cloneDeployArgs);

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
        public static void Delete(PyRevitClone clone, bool clearConfigs = false)
        {
            logger.Debug("Unregistering clone \"{0}\"", clone);
            UnregisterClone(clone);

            logger.Debug("Removing directory \"{0}\"", clone.ClonePath);
            CommonUtils.DeleteDirectory(clone.ClonePath);

            if (clearConfigs)
                PyRevitConfigs.DeleteConfig();
        }

        // uninstall all registered clones
        // @handled @logs
        public static void DeleteAllClones(bool clearConfigs = false)
        {
            foreach (var clone in GetRegisteredClones())
                Delete(clone, clearConfigs: false);

            if (clearConfigs)
                PyRevitConfigs.DeleteConfig();
        }

        // force update given or all registered clones
        // @handled @logs
        public static void Update(PyRevitClone clone, GitInstallerCredentials credentials)
        {
            // current user config
            logger.Debug("Updating pyRevit clone \"{0}\"", clone.Name);
            if (clone.IsRepoDeploy)
            {
                var res = GitInstaller.ForcedUpdate(clone.ClonePath, credentials);
                if (res <= UpdateStatus.Conflicts)
                    throw new PyRevitException(string.Format("Error updating clone \"{0}\"", clone.Name));
            }
            else
            {
                // re-deploying is how the no-git clones get updated
                ReDeployClone(clone, credentials);
            }
        }

        // force update given or all registered clones
        // @handled @logs
        public static void UpdateAllClones(GitInstallerCredentials credentials)
        {
            logger.Debug("Updating all pyRevit clones");
            foreach (var clone in GetRegisteredClones())
                Update(clone, credentials);
        }

        // updates the config value for registered clones
        public static void SaveRegisteredClones(IEnumerable<PyRevitClone> clonesList)
        {
            var cfg = PyRevitConfigs.GetConfigFile();
            var newValueDic = clonesList.ToDictionary(x => x.Name, x => x.ClonePath);
            cfg.SetValue(
                PyRevitConsts.EnvConfigsSectionName,
                PyRevitConsts.EnvConfigsInstalledClonesKey,
                newValueDic);
        }
    }
}
