using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Security.Principal;
using System.Text;
using System.Text.RegularExpressions;

using pyRevitLabs.Common;
using pyRevitLabs.Common.Extensions;
using pyRevitLabs.Configurations;
using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Json.Linq;
using pyRevitLabs.NLog;
using Environment = System.Environment;

/*
 * There are 3 types of extension functions here 
 *  - Shipped extensions are the ones shipped as part of a clone (builtin) and specific to a clone
 *  - Installed extensions are installed globally in paths. All clones will see these extension
 *  - Registered extensions are extension metadata registered in json files. They ar used to extract info about an extension and find the install source
 */ 

namespace pyRevitLabs.PyRevit {
    public static class PyRevitExtensions {
        private static readonly Logger _logger = LogManager.GetCurrentClassLogger();

        // managing extensions =======================================================================================
        // check if extension name matches the given pattern
        private static bool CompareExtensionNames(string extName, string searchTerm) {
            var extMatcher = new Regex(searchTerm,
                                       RegexOptions.IgnoreCase | RegexOptions.IgnorePatternWhitespace);
            return extMatcher.IsMatch(extName);
        }

        // find all extensions under a given directory
        public static List<PyRevitExtension> FindExtensions(string searchPath) {
            var installedExtensions = new List<PyRevitExtension>();

            _logger.Debug("Looking for installed extensions under \"{0}\"...", searchPath);
            foreach (var subdir in Directory.GetDirectories(searchPath)) {
                if (PyRevitExtension.IsExtensionDirectory(subdir)) {
                    _logger.Debug("Found installed extension \"{0}\"...", subdir);
                    installedExtensions.Add(new PyRevitExtension(subdir));
                }
            }

            return installedExtensions;
        }

        // find a specific extension under a given directory
        public static PyRevitExtension FindExtension(string searchPath, string searchPattern) {
            foreach (PyRevitExtension ext in FindExtensions(searchPath))
                if (CompareExtensionNames(ext.Name, searchPattern))
                    return ext;
            
            throw new PyRevitException(string.Format("Can not find extension matching \"{0}\"", searchPattern));
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
                _logger.Error(
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
                        _logger.Error(
                            string.Format(
                                "Error looking up extension with pattern \"{0}\" in extension lookup source \"{1}\""
                                + " | {2}", searchPattern, extLookupSrc, ex.Message)
                                );
                    }
                }

            // return empty results since nothing has been found and no exception has occured
            return matchedExtensions;
        }

        // lookup registered extension by name
        // @handled @logs
        public static PyRevitExtensionDefinition FindRegisteredExtension(string extensionName) {
            _logger.Debug("Looking up registered extension \"{0}\"...", extensionName);
            var matchingExts = LookupRegisteredExtensions(extensionName);
            if (matchingExts.Count == 0) {
                throw new PyRevitException(string.Format("Can not find extension \"{0}\"", extensionName));
            }
            else if (matchingExts.Count == 1) {
                _logger.Debug("Extension found \"{0}\"...", matchingExts[0].Name);
                return matchingExts[0];
            }
            else if (matchingExts.Count > 1)
                Errors.LatestError = ErrorCodes.MoreThanOneItemMatched;

            return null;
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
                installedExtensions.AddRange(PyRevitExtensions.FindExtensions(path));

            return installedExtensions;
        }

        // find extension installed under registered search paths
        // @handled @logs
        public static PyRevitExtension GetInstalledExtension(string searchPattern) {
            _logger.Debug("Looking up installed extension \"{0}\"...", searchPattern);
            foreach (var ext in GetInstalledExtensions()) {
                _logger.Debug("-----------> {0}", ext.Name);
                if (CompareExtensionNames(ext.Name, searchPattern)) {
                    _logger.Debug(string.Format("\"{0}\" Matched installed extension \"{1}\"",
                                               searchPattern, ext.Name));
                    return ext;
                }
            }

            throw new PyRevitException(string.Format("Installed extension \"{0}\" not found.", searchPattern));
        }

        // return a list of installed extensions found under registered search paths
        // @handled @logs
        public static List<PyRevitExtension> GetShippedExtensions(PyRevitClone clone) => clone.GetExtensions();

        // find extension installed under registered search paths
        // @handled @logs
        public static PyRevitExtension GetShippedExtension(PyRevitClone clone, string searchPattern) => clone.GetExtension(searchPattern);

        // installs extension from repo url
        // @handled @logs
        public static void InstallExtension(string extensionName, PyRevitExtensionTypes extensionType,
                                            string repoPath, string destPath = null, string branchName = null,
                                            GitInstallerCredentials credentials = null) {
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

            _logger.Debug("Extension branch name determined as \"{0}\"", branchName);
            _logger.Debug("Installing extension into \"{0}\"", finalExtRepoPath);

            // start the clone process
            var repo = GitInstaller.Clone(repoPath, branchName, finalExtRepoPath, credentials);

            // Check installation
            if (repo != null) {
                // make sure to delete the repo if error occured after cloning
                var clonedPath = repo.Info.WorkingDirectory;
                if (GitInstaller.IsValidRepo(clonedPath)) {
                    _logger.Debug("Clone successful \"{0}\"", clonedPath);
                    RegisterExtensionSearchPath(destPath.NormalizeAsPath());
                }
                else {
                    _logger.Debug("Invalid repo after cloning. Deleting clone \"{0}\"", repoPath);
                    try {
                        CommonUtils.DeleteDirectory(repoPath);
                    }
                    catch (Exception delEx) {
                        _logger.Error(string.Format("Error post-install cleanup on \"{0}\" | {1}",
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
            _logger.Debug("Installing extension \"{0}\"", extDef.Name);
            InstallExtension(extDef.Name, extDef.Type, extDef.Url, destPath, branchName);
        }

        // uninstalls an extension by repo
        // @handled @logs
        public static void RemoveExtension(string repoPath, bool removeSearchPath = false) {
            if (repoPath != null) {
                _logger.Debug("Uninstalling extension at \"{0}\"", repoPath);
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
            _logger.Debug("Uninstalling extension \"{0}\"", extensionName);
            var ext = GetInstalledExtension(extensionName);
            RemoveExtension(ext.InstallPath, removeSearchPath: removeSearchPath);
        }

        // force update extension
        // @handled @logs
        public static void UpdateExtension(PyRevitExtension ext, GitInstallerCredentials credentials = null) {
            _logger.Debug("Updating extension \"{0}\"", ext.Name);
            _logger.Debug("Updating extension repo at \"{0}\"", ext.InstallPath);
            var res = GitInstaller.ForcedUpdate(ext.InstallPath, credentials);
            if (res <= UpdateStatus.Conflicts)
                throw new PyRevitException(
                    string.Format("Error updating extension \"{0}\" installed at \"{1}\"", ext.Name, ext.InstallPath)
                    );
        }

        public static void UpdateExtension(string extName, GitInstallerCredentials credentials = null) {
            var ext = GetInstalledExtension(extName);
            UpdateExtension(ext, credentials);
        }

        // force update all extensions
        // @handled @logs
        public static void UpdateAllInstalledExtensions(GitInstallerCredentials credentials = null) {
            _logger.Debug("Updating all installed extensions.");
            // update all installed extensions
            foreach (var ext in GetInstalledExtensions())
                UpdateExtension(ext, credentials);
        }

        // enable extension in config
        // @handled @logs
        private static void ToggleExtension(string revitVersion, PyRevitExtension ext, bool state) {
            _logger.Debug("{@State} extension \"{@ExtensionName}\"", state ? "Enabling" : "Disabling", ext.Name);
            
            IConfigurationService cfg = PyRevitConfigs.GetConfigFile();
            cfg.SetSectionKeyValue(revitVersion, ext.ConfigName, PyRevitConsts.ExtensionDisabledKey, !state);
        }

        // disable installed extension in config
        // @handled @logs
        public static void EnableInstalledExtension(string revitVersion, string searchPattern) {
            var ext = GetInstalledExtension(searchPattern);
            ToggleExtension(revitVersion, ext, true);
        }

        // disable installed extension in config
        // @handled @logs
        public static void DisableInstalledExtension(string revitVersion, string searchPattern) {
            var ext = GetInstalledExtension(searchPattern);
            ToggleExtension(revitVersion, ext, false);
        }

        // disable shipped extension in config
        // @handled @logs
        public static void EnableShippedExtension(string revitVersion, PyRevitClone clone, string searchPattern) {
            var ext = GetShippedExtension(clone, searchPattern);
            ToggleExtension(revitVersion, ext, true);
        }

        // disable shipped extension in config
        // @handled @logs
        public static void DisableShippedExtension(string revitVersion, PyRevitClone clone, string searchPattern) {
            var ext = GetShippedExtension(clone, searchPattern);
            ToggleExtension(revitVersion, ext, false);
        }

        // get list of registered extension search paths
        // @handled @logs
        public static List<string> GetRegisteredExtensionSearchPaths() {
            // TODO: Make apply config to revit version
            var validatedPaths = new List<string>();
            var cfg = PyRevitConfigs.GetConfigFile();
           
            var searchPaths = cfg.GetSectionKeyValueOrDefault<string[]>(
                ConfigurationService.DefaultConfigurationName, 
                PyRevitConsts.ConfigsCoreSection, 
                PyRevitConsts.ConfigsUserExtensionsKey);
            
            if (searchPaths != null) {
                // make sure paths exist
                foreach (var path in searchPaths) {
                    var normPath = path.NormalizeAsPath();
                    if (CommonUtils.VerifyPath(path) && !validatedPaths.Contains(normPath)) {
                        _logger.Debug("Verified extension search path \"{@ExtensionsSource}\"", normPath);
                        validatedPaths.Add(normPath);
                    }
                }

                // rewrite verified list
                cfg.SetSectionKeyValue(
                    ConfigurationService.DefaultConfigurationName, 
                    PyRevitConsts.ConfigsCoreSection, 
                    PyRevitConsts.ConfigsUserExtensionsKey, 
                    validatedPaths);
            }
            return validatedPaths;
        }

        // add extension search path
        // @handled @logs
        public static void RegisterExtensionSearchPath(string searchPath) {
            // TODO: Make apply config to revit version
            var cfg = PyRevitConfigs.GetConfigFile();
            if (CommonUtils.VerifyPath(searchPath)) {
                _logger.Debug("Adding extension search path \"{@ExtensionSource}\"", searchPath);
                var searchPaths = GetRegisteredExtensionSearchPaths();
                searchPaths.Add(searchPath.NormalizeAsPath());
                cfg.SetSectionKeyValue(
                    ConfigurationService.DefaultConfigurationName,
                    PyRevitConsts.ConfigsCoreSection,
                    PyRevitConsts.ConfigsUserExtensionsKey,
                    searchPaths);
            }
            else
                throw new pyRevitResourceMissingException(searchPath);
        }

        // remove extension search path
        // @handled @logs
        public static void UnregisterExtensionSearchPath(string searchPath) {
            var cfg = PyRevitConfigs.GetConfigFile();
            var normPath = searchPath.NormalizeAsPath();
            _logger.Debug("Removing extension search path \"{@ExtensionSource}\"", normPath);
            var searchPaths = GetRegisteredExtensionSearchPaths();
            searchPaths.Remove(normPath);
            cfg.SetSectionKeyValue(
                ConfigurationService.DefaultConfigurationName,
                PyRevitConsts.ConfigsCoreSection,
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
            var cfg = PyRevitConfigs.GetConfigFile();
            
            var normSources = new List<string>();
            foreach (var src in cfg.Environment.Sources) {
                var normSrc = src.NormalizeAsPath();
                _logger.Debug("Extension lookup source \"{@ExtensionSource}\"", normSrc);
                normSources.Add(normSrc);
                SaveExtensionLookupSources(normSources);
            }
            
            return normSources;
        }

        // register new extension lookup source
        // @handled @logs
        public static void RegisterExtensionLookupSource(string extLookupSource) {
            var normSource = extLookupSource.NormalizeAsPath();
            var sources = GetRegisteredExtensionLookupSources();
            if (!sources.Contains(normSource)) {
                _logger.Debug("Registering extension lookup source \"{0}\"", normSource);
                sources.Add(normSource);
                SaveExtensionLookupSources(sources);
            }
            else
                _logger.Debug("Extension lookup source already exists. Skipping registration.");
        }

        // unregister extension lookup source
        // @handled @logs
        public static void UnregisterExtensionLookupSource(string extLookupSource) {
            var normSource = extLookupSource.NormalizeAsPath();
            var sources = GetRegisteredExtensionLookupSources();
            if (sources.Contains(normSource)) {
                _logger.Debug("Unregistering extension lookup source \"{0}\"", normSource);
                sources.Remove(normSource);
                SaveExtensionLookupSources(sources);
            }
            else
                _logger.Debug("Extension lookup source does not exist. Skipping unregistration.");
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
            _logger.Debug("Determining file or remote source \"{0}\"", fileOrUri);
            Uri uriResult;
            var validPath = Uri.TryCreate(fileOrUri, UriKind.Absolute, out uriResult);
            if (validPath) {
                if (uriResult.IsFile) {
                    filePath = fileOrUri;
                    _logger.Debug("Source is a file \"{0}\"", filePath);
                }
                else if (uriResult.HostNameType == UriHostNameType.Dns
                            || uriResult.HostNameType == UriHostNameType.IPv4
                            || uriResult.HostNameType == UriHostNameType.IPv6) {

                    _logger.Debug("Source is a remote resource \"{0}\"", fileOrUri);
                    _logger.Debug("Downloading remote resource \"{0}\"...", fileOrUri);
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
                    _logger.Debug("Parsing extension metadata file...");

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

                            _logger.Debug("Registered extension \"{0}\"", extDef.Name);
                            if (searchPattern != null) {
                                if (CompareExtensionNames(extDef.Name, searchPattern)) {
                                    _logger.Debug(string.Format("\"{0}\" Matched registered extension \"{1}\"",
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


        // save list of source exensio
        private static void SaveExtensionLookupSources(IEnumerable<string> sources) {
            var cfg = PyRevitConfigs.GetConfigFile();
            cfg.SaveSection(
                ConfigurationService.DefaultConfigurationName,
                new EnvironmentSection() {Sources = sources.ToList()});
        }
    }
}
