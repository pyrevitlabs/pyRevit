using System;
using System.Collections.Generic;
using System.IO;
using System.Text.RegularExpressions;
using System.Linq;
using System.Reflection;

using pyRevitLabs.Common;
using pyRevitLabs.Common.Extensions;
using pyRevitLabs.TargetApps.Revit;

using Nett;
using pyRevitLabs.NLog;

namespace pyRevitLabs.PyRevit {
    public struct PyRevitCloneFromImageArgs {
        public string Url;
        public string BranchName;
        public string DeploymentName;
    }

    public class PyRevitClone {
        // private logger and data
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        private static readonly List<string> reservedNames = new List<string>() {
            "git", "pyrevit",
            "blog", "docs", "source", "youtube", "support", "env", "clone", "clones",
            "add", "forget", "rename", "delete", "branch", "commit", "version",
            "attach", "attatched", "latest", "dynamosafe", "detached",
            "extend", "extensions", "search", "install", "uninstall", "update", "paths", "revits",
            "config", "configs", "logs", "none", "verbose", "debug", "allowremotedll", "checkupdates",
            "autoupdate", "rocketmode", "filelogging", "loadbeta", "telemetry", "enable", "disable",
            "file", "server", "outputcss", "seed"
        };

        // constructors
        public PyRevitClone(string clonePath, string name = null) {
            // clone path could be any path inside or outside the clonePath
            // find the clone root first
            var _clonePath = FindValidClonePathAbove(clonePath);
            if (_clonePath is null) {
                _clonePath = FindValidClonePathBelow(clonePath);
                if (_clonePath is null)
                    throw new PyRevitException(
                        string.Format("Path does not point to a valid clone \"{0}\"", clonePath)
                    );
            }

            ClonePath = _clonePath.NormalizeAsPath();

            if (name != null) {
                if (!reservedNames.Contains(name)) {
                    Name = name;
                }
                else
                    throw new PyRevitException(string.Format("Name \"{0}\" is reserved.", name));
            }
            else
                Name = string.Format("Unnamed-{0}", ClonePath.GenerateMD5Hash().GetHashShort());
        }

        private PyRevitClone(string clonePath) : this(clonePath, null) {}

        // properties
        public string Name { get; private set; }

        public string ClonePath { get; private set; }

        public string ExtensionsPath => GetExtensionsPath(ClonePath);

        public override string ToString() {
            if (IsRepoDeploy)
                return string.Format(
                    "{0} | Branch: \"{1}\" | Version: \"{2}\" | Path: \"{3}\"",
                    Name, Branch, string.Format("{0}:{1}", ModuleVersion, ShortCommit), ClonePath);
            else {
                return string.Format(
                    "{0} | Deploy: \"{1}\" | Branch: \"{2}\" | Version: \"{3}\" | Path: \"{4}\"",
                    Name, Deployment?.Name, Branch, ModuleVersion, ClonePath);
            }
        }

        public bool IsRepoDeploy {
            get {
                try {
                    return IsDeployedWithRepo(ClonePath);
                }
                catch { return false; }
            }
        }

        public bool IsValid => IsCloneValid(ClonePath);

        public bool HasDeployments {
            get { return VerifyHasDeployments(ClonePath); }
        }

        public string ModuleVersion => GetDeployedVersion(ClonePath);

        public string Branch {
            get {
                if (IsRepoDeploy)
                    return GetBranch(ClonePath);
                else
                    return GetDeployedBranch(ClonePath);
            }
        }

        public string Tag => GetTag(ClonePath);

        public string Commit => GetCommit(ClonePath);

        public string ShortCommit => Commit.GetHashShort();

        public string Origin => GetOrigin(ClonePath);

        public PyRevitDeployment Deployment => GetCurrentDeployment(ClonePath);

        // equality checks
        public override bool Equals(object obj) {
            var other = obj as PyRevitClone;

            if (ClonePath != other.ClonePath)
                return false;

            return true;
        }

        public override int GetHashCode() {
            return ClonePath.GetHashCode();
        }

        public bool Matches(string copyNameOrPath) {
            if (Name.ToLower() == copyNameOrPath.ToLower())
                return true;

            try {
                return ClonePath == copyNameOrPath.NormalizeAsPath();
            }
            catch { }

            return false;
        }

        public void Rename(string newName) {
            if (newName != null)
                Name = newName;
        }

        public List<PyRevitEngine> GetEngines() => GetEngines(ClonePath);

        public PyRevitEngine GetEngine(int engineVer) => GetEngine(ClonePath, engineVer: engineVer);

        public List<PyRevitEngine> GetConfiguredEngines() => GetConfiguredEngines(ClonePath);

        public List<PyRevitDeployment> GetConfiguredDeployments() => GetConfiguredDeployments(ClonePath);

        public void SetBranch(string branchName) => SetBranch(ClonePath, branchName);

        public void SetTag(string tagName) => SetTag(ClonePath, tagName);

        public void SetCommit(string commitHash) => SetCommit(ClonePath, commitHash);

        public void SetOrigin(string originUrl) => SetOrigin(ClonePath, originUrl);

        public PyRevitCloneFromImageArgs DeploymentArgs => ReadDeploymentArgs(ClonePath);

        public List<PyRevitExtension> GetExtensions() => GetExtensions(ClonePath);

        public PyRevitExtension GetExtension(string searchPattern) => GetExtension(ClonePath, searchPattern);

        // static methods ============================================================================================
        // determine if this is a git repo
        public static bool IsDeployedWithRepo(string clonePath) {
            return CommonUtils.VerifyPath(Path.Combine(clonePath, PyRevitLabsConsts.DefaultGitDirName));
        }

        // get extensions path
        public static string GetExtensionsPath(string clonePath) =>
            Path.Combine(clonePath, PyRevitConsts.ExtensionsDirName).NormalizeAsPath();

        // get pyrevitlib path
        public static string GetPyRevitLibPath(string clonePath) =>
            Path.Combine(clonePath, PyRevitConsts.LibDirName).NormalizeAsPath();

        // get pyrevitlib/pyrevit path
        public static string GetPyRevitPath(string clonePath) =>
            Path.Combine(GetPyRevitLibPath(clonePath), PyRevitConsts.ModuleDirName).NormalizeAsPath();

        // get pyrevitlib/pyrevit/version path
        public static string GetPyRevitVersionFilePath(string clonePath) =>
            Path.Combine(GetPyRevitPath(clonePath), PyRevitConsts.VersionFilename).NormalizeAsPath();

        // get pyRevitFile path
        public static string GetPyRevitFilePath(string clonePath) {
            var prFile = Path.Combine(clonePath, PyRevitConsts.PyRevitfileFilename);
            if (File.Exists(prFile))
                return prFile;

            return null;
        }

        // check if path is valid pyrevit clone
        // @handled @logs
        public static void VerifyCloneValidity(string clonePath) {
            if (clonePath != null && clonePath != string.Empty) {
                var normClonePath = clonePath.NormalizeAsPath();
                logger.Debug("Checking pyRevit clone validity \"{0}\"", normClonePath);
                if (CommonUtils.VerifyPath(normClonePath)) {
                    // determine clone validity based on directory availability
                    logger.Debug("Checking clone validity by directory structure...");
                    var pyrevitDir = GetPyRevitPath(normClonePath);
                    logger.Debug("Checking pyRevit path \"{0}\"", pyrevitDir);
                    if (!CommonUtils.VerifyPath(pyrevitDir)) {
                        throw new pyRevitInvalidPyRevitCloneException(normClonePath);
                    }

                    // if is a repo, and repo is NOT valid, throw an exception
                    logger.Debug("Checking clone validity by git repo...");
                    if (IsDeployedWithRepo(normClonePath) && !GitInstaller.IsValidRepo(normClonePath))
                        throw new pyRevitInvalidGitCloneException(normClonePath);

                    logger.Debug("Valid pyRevit clone \"{0}\"", normClonePath);
                    return;
                }
                throw new pyRevitResourceMissingException(normClonePath);
            }
            throw new PyRevitException("Clone path can not be null.");
        }

        // get clone from manifest file
        public static PyRevitClone GetCloneFromManifest(RevitAddonManifest manifest) {
            return new PyRevitClone(Path.GetDirectoryName(manifest.Assembly));
        }

        // return true of false for clone validity
        public static bool IsCloneValid(string clonePath) {
            try {
                VerifyCloneValidity(clonePath);
                return true;
            }
            catch (Exception ex) {
                logger.Debug("Invalid pyRevit clone. | {0}", ex.Message);
                return false;
            }
        }

        // get engine from clone path
        // returns latest with default engineVer value
        // @handled @logs
        public static PyRevitEngine GetEngine(string clonePath, int engineVer) {
            logger.Debug("Finding engine \"{0}\" path in \"{1}\"", engineVer, clonePath);
            return GetEngines(clonePath).Where(x => x.Version == engineVer).First();
        }

        // get all engines from clone path
        // returns latest with default engineVer value
        // @handled @logs
        public static List<PyRevitEngine> GetEngines(string clonePath) {
            if (GetPyRevitFilePath(clonePath) != null) {
                return GetConfiguredEngines(clonePath);
            }
            else {
                logger.Debug("Finding engines in \"{0}\"", clonePath);
                var enginesDir = FindEnginesDirectory(clonePath);
                return FindEngines(enginesDir);
            }
        }

        // extract deployment config from pyRevitfile inside the clone
        public static List<PyRevitEngine> GetConfiguredEngines(string clonePath) {
            var engines = new List<PyRevitEngine>();

            var prFile = GetPyRevitFilePath(clonePath);
            try {
                TomlTable table = Toml.ReadFile(prFile);
                var enginesCfgs = table.Get<TomlTable>("engines");
                foreach (var engineCfg in enginesCfgs) {
                    logger.Debug("Engine configuration found: {0}", engineCfg.Key);
                    var infoTable = engineCfg.Value as TomlTable;
                    foreach (KeyValuePair<string, TomlObject> entry in infoTable)
                        logger.Debug("\"{0}\" : \"{1}\"", entry.Key, entry.Value);

                    engines.Add(
                        new PyRevitEngine(
                            engineVer: infoTable["version"].Get<int>(),
                            runtime: infoTable.TryGetValue("runtime") != null ? infoTable["runtime"].Get<bool>() : true, // be flexible since its a new feature
                            enginePath: Path.Combine(clonePath, infoTable["path"].Get<string>()),
                            assemblyName: infoTable.TryGetValue("assembly") != null? infoTable["assembly"].Get<string>() : PyRevitConsts.LegacyEngineDllName, // be flexible since its a new feature
                            kernelName: infoTable["kernel"].Get<string>(),
                            engineDescription: infoTable["description"].Get<string>(),
                            compatibleProducts: new List<string>(((TomlArray)infoTable["compatproducts"]).To<string>())
                            )
                        );
                }
            }
            catch (Exception ex) {
                logger.Debug(string.Format("Error parsing clone \"{0}\" engines configs from \"{1}\" | {2}",
                                           clonePath, prFile, ex.Message));
            }

            return engines;
        }

        // extract deployment config from pyRevitfile inside the clone
        public static List<PyRevitDeployment> GetConfiguredDeployments(string clonePath) {
            var deps = new List<PyRevitDeployment>();

            var prFile = GetPyRevitFilePath(clonePath);
            try {
                TomlTable table = Toml.ReadFile(prFile);
                var depCfgs = table.Get<TomlTable>("deployments");
                foreach (KeyValuePair<string, TomlObject> entry in depCfgs) {
                    logger.Debug("\"{0}\" : \"{1}\"", entry.Key, entry.Value);
                    deps.Add(
                        new PyRevitDeployment(entry.Key,
                                              new List<string>(((TomlArray)entry.Value).To<string>()))
                        );
                }
            }
            catch (Exception ex) {
                logger.Debug(string.Format("Error parsing clone \"{0}\" deployment configs at \"{1}\" | {2}",
                                           clonePath, prFile, ex.Message));
            }

            return deps;
        }

        // get currently deployed deployment
        public static PyRevitDeployment GetCurrentDeployment(string clonePath) {
            var cloneArgs = ReadDeploymentArgs(clonePath);
            foreach (var dep in GetConfiguredDeployments(clonePath))
                if (dep.Name == cloneArgs.DeploymentName)
                    return dep;
            return null;
        }

        public static bool VerifyHasDeployments(string clonePath) {
            return GetConfiguredDeployments(clonePath).Count > 0;
        }

        // get pyrevit version from deployed clone
        // @handled @logs
        public static string GetDeployedVersion(string clonePath) {
            VerifyCloneValidity(clonePath);
            var vesionFile = GetPyRevitVersionFilePath(clonePath);
            if (CommonUtils.VerifyFile(vesionFile))
                return File.ReadAllText(vesionFile);
            else
                return "Unknown";
        }

        // get branch from deployed clone
        // @handled @logs
        public static string GetDeployedBranch(string clonePath) {
            var cloneArgs = ReadDeploymentArgs(clonePath);
            return cloneArgs.BranchName;
        }

        // get checkedout branch in git repo
        // @handled @logs
        public static string GetBranch(string clonePath) {
            VerifyCloneValidity(clonePath);
            return GitInstaller.GetCheckedoutBranch(clonePath);
        }

        // get checkedout version in git repo
        // @handled @logs
        public static string GetTag(string clonePath) {
            // TODO: implement get version
            throw new NotImplementedException();
        }

        // get checkedout branch in git repo
        // @handled @logs
        public static string GetCommit(string clonePath) {
            VerifyCloneValidity(clonePath);
            return GitInstaller.GetHeadCommit(clonePath);
        }

        // get origin remote url
        // @handled @logs
        public static string GetOrigin(string clonePath) {
            VerifyCloneValidity(clonePath);
            return GitInstaller.GetRemoteUrl(clonePath, PyRevitConsts.DefaultCloneRemoteName);
        }

        // checkout branch in git repo
        // @handled @logs
        public static void SetBranch(string clonePath, string branchName) {
            VerifyCloneValidity(clonePath);
            if (branchName != null)
                GitInstaller.CheckoutBranch(clonePath, branchName);
        }

        // rebase clone to specific tag
        // @handled @logs
        public static void SetTag(string clonePath, string tagName) {
            VerifyCloneValidity(clonePath);
            if (tagName != null)
                GitInstaller.RebaseToTag(clonePath, tagName);
        }

        // rebase clone to specific commit
        // @handled @logs
        public static void SetCommit(string clonePath, string commitHash) {
            VerifyCloneValidity(clonePath);
            if (commitHash != null)
                GitInstaller.RebaseToCommit(clonePath, commitHash);
        }

        // set origin url to new url
        // @handled @logs
        public static void SetOrigin(string clonePath, string originUrl) {
            VerifyCloneValidity(clonePath);
            if (originUrl != null)
                GitInstaller.SetRemoteUrl(clonePath, PyRevitConsts.DefaultCloneRemoteName, originUrl);
        }

        // get list of builtin extensions
        // @handled @logs
        public static List<PyRevitExtension> GetExtensions(string clonePath) {
            VerifyCloneValidity(clonePath);
            return PyRevitExtensions.FindExtensions(PyRevitClone.GetExtensionsPath(clonePath));
        }

        // get a specific builtin extension
        // @handled @logs
        public static PyRevitExtension GetExtension(string clonePath, string searchPattern) {
            VerifyCloneValidity(clonePath);
            return PyRevitExtensions.FindExtension(PyRevitClone.GetExtensionsPath(clonePath), searchPattern);
        }

        // check if given assembly belongs to pyrevit
        public static bool IsPyRevitAssembly(Assembly assm) {
            try {
                var clone = new PyRevitClone(Path.GetDirectoryName(assm.Location));
                return true;
            }
            catch {
                return false;
            }
        }

        // private:
        private static PyRevitCloneFromImageArgs ReadDeploymentArgs(string clonePath) {
            var cloneMemoryFilePath = Path.Combine(clonePath, PyRevitConsts.DeployFromImageConfigsFilename);
            logger.Debug("Reading image clone parmeters from \"{0}\"", cloneMemoryFilePath);

            try {
                var contents = File.ReadAllLines(cloneMemoryFilePath);
                logger.Debug("Image Path: \"{0}\"", contents[0]);
                logger.Debug("Branch: \"{0}\"", contents[1]);
                logger.Debug("Deployment: \"{0}\"", contents[2]);

                var args = new PyRevitCloneFromImageArgs {
                    Url = contents[0] == string.Empty ? PyRevitLabsConsts.OriginalRepoGitPath : contents[0],
                    BranchName = contents[1] == string.Empty ? PyRevitLabsConsts.TragetBranch : contents[1],
                    DeploymentName = contents[2] == string.Empty ? null : contents[2]
                };

                return args;
            }
            catch (Exception ex) {
                throw new PyRevitException(string.Format("Error reading deployment arguments from \"{0}\" | {1}",
                                                         clonePath, ex.Message));
            }
        }

        // find valid clone directory downstream
        private static string FindValidClonePathBelow(string startingPath) {
            logger.Debug("Searching for valid clones below: {0}", startingPath);
            if (IsCloneValid(startingPath)) {
                logger.Debug("Valid clone found at: {0}", startingPath);
                return startingPath;
            }
            else
                foreach(var subFolder in Directory.GetDirectories(startingPath)) {
                    var clonePath = FindValidClonePathBelow(subFolder);
                    if (clonePath != null)
                        return clonePath;
                }

            return null;
        }

        // find valid clone directory downstream
        private static string FindValidClonePathAbove(string startingPath) {
            logger.Debug("Searching for valid clones above: {0}", startingPath);
            string testPath = startingPath;
            while (!IsCloneValid(testPath)) {
                testPath = Path.GetDirectoryName(testPath);
                if (testPath is null || testPath == string.Empty)
                    return null;
            }

            logger.Debug("Valid clone found at: {0}", testPath);
            return testPath;
        }

        // find latest engine path
        // @handled @logs
        private static PyRevitEngine FindLatestEngine(string enginesDir) {
            return FindEngine(enginesDir, engineVer: 000);
        }

        // find engine path with given version
        // @handled @logs
        private static PyRevitEngine FindEngine(string enginesDir, int engineVer = 000) {
            // engines are stored in directory named XXX based on engine version (e.g. 273)
            // return latest if zero
            if (engineVer == 000) {
                PyRevitEngine latestEngine = null;

                // FindEngines will throw an error if engine directory is missing
                foreach (var engine in FindEngines(enginesDir)) {
                    if (engine.Version > engineVer)
                        latestEngine = engine;
                }

                if (latestEngine != null && latestEngine.Version != engineVer) {
                    logger.Debug("Latest engine path \"{0}\"", latestEngine.Path ?? "NULL");
                    return latestEngine;
                }
                else
                    throw new PyRevitException(
                        string.Format("Error determining latest engine from \"{0}\"", enginesDir)
                        );
            }
            else {
                foreach (var engine in FindEngines(enginesDir)) {
                    if (engine.Version == engineVer) {
                        logger.Debug("Engine path \"{0}\"", engine.Path ?? "NULL");
                        return engine;
                    }
                }
            }

            throw new PyRevitException(string.Format("Engine \"{0}\" is not available at \"{1}\"", engineVer, enginesDir));
        }

        // find all engines under a given engine path
        // @handled @logs
        private static List<PyRevitEngine> FindEngines(string enginesDir) {
            // engines are stored in directory named XXX based on engine version (e.g. 273)
            var engines = new List<PyRevitEngine>();
            var engineFinder = new Regex(@"\d\d\d");

            if (CommonUtils.VerifyPath(enginesDir)) {
                foreach (string engineDir in Directory.GetDirectories(enginesDir)) {
                    var engineDirName = Path.GetFileName(engineDir);
                    if (engineFinder.IsMatch(engineDirName)) {
                        var engineVer = int.Parse(engineDirName);
                        logger.Debug("Engine found \"{0}\":\"{1}\"", engineDirName, engineDir);

                        // this method is for legacy repos. since engine configuration file is not available in
                        // legacy repos, it needs to decide whether an engine could be used for runtime or not
                        // assumes anything Python 3 and above is not runtime
                        bool runtime = true;
                        if (engineVer >= 300)
                            runtime = false;

                        engines.Add(new PyRevitEngine(engineVer, runtime, engineDir));
                    }
                }

            }
            else
                throw new pyRevitResourceMissingException(enginesDir);

            return engines;
        }

        // find engine path based on repo directory configs
        // @handled @logs
        private static string FindEnginesDirectory(string clonePath) {
            // determine repo version based on directory availability
            string enginesDir = Path.Combine(clonePath,
                                             PyRevitConsts.BinDirName,
                                             PyRevitConsts.BinEnginesDirName);
            if (!CommonUtils.VerifyPath(enginesDir)) {
                enginesDir = Path.Combine(clonePath,
                                          PyRevitConsts.LibDirName,
                                          PyRevitConsts.ModuleDirName,
                                          PyRevitConsts.ModuleLoaderDirName,
                                          PyRevitConsts.ModuleLegacyAddinDirName);
                if (!CommonUtils.VerifyPath(enginesDir))
                    throw new pyRevitInvalidGitCloneException(clonePath);
            }

            return enginesDir;
        }
    }
}
