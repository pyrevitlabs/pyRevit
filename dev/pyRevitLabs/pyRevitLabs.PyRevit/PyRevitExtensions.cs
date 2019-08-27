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
using pyRevitLabs.NLog;

namespace pyRevitLabs.PyRevit {
    public static class PyRevitExtensions {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

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
            if (searchPath is null)
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

            throw new PyRevitException(string.Format("Installed extension \"{0}\" not found.", extensionName));
        }

        // lookup registered extension by name
        // @handled @logs
        public static PyRevitExtensionDefinition FindRegisteredExtension(string extensionName) {
            logger.Debug("Looking up registered extension \"{0}\"...", extensionName);
            var matchingExts = LookupRegisteredExtensions(extensionName);
            if (matchingExts.Count == 0) {
                throw new PyRevitException(string.Format("Can not find extension \"{0}\"", extensionName));
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
                    throw new PyRevitException(string.Format("Extension \"{0}\" is already installed under \"{1}\"",
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
            destPath = destPath ?? PyRevitConsts.DefaultExtensionsPath;
            string finalExtRepoPath = Path.Combine(destPath, extDestDirName).NormalizeAsPath();

            // determine branch name
            branchName = branchName ?? PyRevitConsts.DefaultExtensionRepoDefaultBranch;

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
                throw new PyRevitException(string.Format("Error installing extension. Null repo error on \"{0}\"",
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
                throw new PyRevitException(
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
            var cfg = PyRevitConfigs.GetConfigFile();
            cfg.SetValue(ext.ConfigName, PyRevitConsts.ExtensionDisabledKey, !state);
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

        public static void SaveExtensionLookupSources(IEnumerable<string> sourcesList) {
        }

        // get list of registered extension search paths
        // @handled @logs
        public static List<string> GetRegisteredExtensionSearchPaths() {
            var validatedPaths = new List<string>();
            var cfg = PyRevitConfigs.GetConfigFile();
            var searchPaths = cfg.GetListValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsUserExtensionsKey);
            if (searchPaths != null) {
                // make sure paths exist
                foreach (var path in searchPaths) {
                    var normPath = path.NormalizeAsPath();
                    if (CommonUtils.VerifyPath(path) && !validatedPaths.Contains(normPath)) {
                        logger.Debug("Verified extension search path \"{0}\"", normPath);
                        validatedPaths.Add(normPath);
                    }
                }

                // rewrite verified list
                cfg.SetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsUserExtensionsKey, validatedPaths);
            }
            return validatedPaths;
        }

        // add extension search path
        // @handled @logs
        public static void RegisterExtensionSearchPath(string searchPath) {
            var cfg = PyRevitConfigs.GetConfigFile();
            if (CommonUtils.VerifyPath(searchPath)) {
                logger.Debug("Adding extension search path \"{0}\"", searchPath);
                var searchPaths = GetRegisteredExtensionSearchPaths();
                searchPaths.Add(searchPath.NormalizeAsPath());
                cfg.SetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsUserExtensionsKey, searchPaths);
            }
            else
                throw new pyRevitResourceMissingException(searchPath);
        }

        // remove extension search path
        // @handled @logs
        public static void UnregisterExtensionSearchPath(string searchPath) {
            var cfg = PyRevitConfigs.GetConfigFile();
            var normPath = searchPath.NormalizeAsPath();
            logger.Debug("Removing extension search path \"{0}\"", normPath);
            var searchPaths = GetRegisteredExtensionSearchPaths();
            searchPaths.Remove(normPath);
            cfg.SetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsUserExtensionsKey, searchPaths);
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
            var cfg = PyRevitConfigs.GetConfigFile();
            var normSources = new List<string>();
            var sources = cfg.GetListValue(PyRevitConsts.EnvConfigsSectionName, PyRevitConsts.EnvConfigsExtensionLookupSourcesKey);
            if (sources != null) {
                foreach (var src in sources) {
                    var normSrc = src.NormalizeAsPath();
                    logger.Debug("Extension lookup source \"{0}\"", normSrc);
                    normSources.Add(normSrc);
                    SaveExtensionLookupSources(normSources);
                }
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
                        throw new PyRevitException(
                            string.Format("Error downloading extension metadata file. | {0}", ex.Message)
                            );
                    }
                }
            }
            else
                throw new PyRevitException(
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
                            throw new PyRevitException(string.Format("Error parsing extension metadata. | {0}", ex.Message));
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
                    throw new PyRevitException(
                        string.Format("Definition file is not a valid json file \"{0}\"", filePath)
                        );
            }

            return pyrevtExts;
        }

    }
}
