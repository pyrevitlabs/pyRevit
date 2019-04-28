using System;
using System.Collections.Generic;
using System.IO;
using System.Text.RegularExpressions;
using System.Linq;
using System.Reflection;

using pyRevitLabs.Common;
using pyRevitLabs.Common.Extensions;

using Nett;
using NLog;

namespace pyRevitLabs.TargetApps.Revit {
    // helper struct
    public struct PyRevitCloneFromArchiveArgs {
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
            "autoupdate", "rocketmode", "filelogging", "loadbeta", "usagelogging", "enable", "disable",
            "file", "server", "outputcss", "seed"
        };

        // constructors
        public PyRevitClone(string name, string clonePath) {
            // TODO: check repo validity?
            if (!reservedNames.Contains(name)) {
                Name = name;
                ClonePath = clonePath.NormalizeAsPath();
            }
            else
                throw new pyRevitException(string.Format("Name \"{0}\" is reserved.", name));
        }

        private PyRevitClone(string clonePath) {
            // clone path could be any path inside or outside the clonePath
            // find the clone root first
            var _clonePath = FindValidClonePathAbove(clonePath);
            if (_clonePath == null) {
                _clonePath = FindValidClonePathBelow(clonePath);
                if (_clonePath == null)
                    throw new pyRevitException(
                        string.Format("Path does not point to a valid clone \"{0}\"", clonePath)
                    );
            }

            ClonePath = _clonePath.NormalizeAsPath();
            Name = "Unnamed";
        }

        // properties
        public string Name { get; private set; }

        public string ClonePath { get; private set; }

        public override string ToString() {
            if (IsRepoDeploy)
                return string.Format(
                    "{0} | Branch: \"{1}\" | Version: \"{2}\" | Path: \"{3}\"",
                    Name, Branch, string.Format("{0}:{1}", ModuleVersion, Commit), ClonePath);
            else {
                return string.Format(
                    "{0} | Deploy: \"{1}\" | Branch: \"{2}\" | Version: \"{3}\" | Path: \"{4}\"",
                    Name, Deployment.Name, Branch, ModuleVersion, ClonePath);
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

        public bool IsValidClone => IsCloneValid(ClonePath);

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

        // TODO: add container inclusion check overload

        // static methods ============================================================================================
        // public
        // determine if this is a git repo
        public static bool IsDeployedWithRepo(string clonePath) {
            return CommonUtils.VerifyPath(Path.Combine(clonePath, PyRevitConsts.DefaultGitDirName));
        }

        // get pyrevitlib path
        public static string GetPyRevitLibPath(string clonePath) =>
            Path.Combine(clonePath, PyRevitConsts.PyRevitLibDirName).NormalizeAsPath();

        // get pyrevitlib/pyrevit path
        public static string GetPyRevitPath(string clonePath) =>
            Path.Combine(GetPyRevitLibPath(clonePath), PyRevitConsts.PyRevitModuleDirName).NormalizeAsPath();

        // get pyrevitlib/pyrevit/version path
        public static string GetPyRevitVersionFilePath(string clonePath) =>
            Path.Combine(GetPyRevitPath(clonePath), PyRevitConsts.PyRevitVersionFilename).NormalizeAsPath();

        // get pyRevitFile path
        public static string GetPyRevitFilePath(string clonePath) {
            var prFile = Path.Combine(clonePath, PyRevitConsts.PyRevitfileFilename);
            if (File.Exists(prFile))
                return prFile;

            return null;
        }

        // check if path is valid pyrevit clone
        // @handled @logs
        public static bool VerifyCloneValidity(string clonePath) {
            var normClonePath = clonePath.NormalizeAsPath();
            logger.Debug("Checking pyRevit copy validity \"{0}\"", normClonePath);
            if (CommonUtils.VerifyPath(normClonePath)) {
                // say yes if under test
                if (!GlobalConfigs.AllClonesAreValid) {
                    // determine clone validity based on directory availability
                    var pyrevitDir = GetPyRevitPath(normClonePath);
                    if (!CommonUtils.VerifyPath(pyrevitDir)) {
                        throw new pyRevitInvalidpyRevitCloneException(normClonePath);
                    }

                    // if is a repo, and repo is NOT valid, throw an exception
                    if (IsDeployedWithRepo(normClonePath) && !GitInstaller.IsValidRepo(normClonePath))
                        throw new pyRevitInvalidGitCloneException(normClonePath);
                }
                logger.Debug("Valid pyRevit clone \"{0}\"", normClonePath);
                return true;
            }

            throw new pyRevitResourceMissingException(normClonePath);
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
        public static PyRevitEngine GetEngine(string clonePath, int engineVer = 000) {
            logger.Debug("Finding engine \"{0}\" path in \"{1}\"", engineVer, clonePath);
            var enginesDir = FindEnginesDirectory(clonePath);
            return FindEngine(enginesDir, engineVer: engineVer);
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
                        logger.Debug("\"{0}\" : \"{1}\"", entry.Key, entry.Value.TomlType);

                    engines.Add(
                        new PyRevitEngine(
                            engineVer: infoTable["version"].Get<int>(),
                            enginePath: Path.Combine(clonePath, infoTable["path"].Get<string>()),
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

        // static
        // private
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
                PyRevitEngine latestEnginerVer = new PyRevitEngine(000, null);

                foreach (var engine in FindEngines(enginesDir)) {
                    if (engine.Version > latestEnginerVer.Version)
                        latestEnginerVer = engine;
                }

                logger.Debug("Latest engine path \"{0}\"", latestEnginerVer.Path ?? "NULL");
                return latestEnginerVer;
            }
            else {
                foreach (var engine in FindEngines(enginesDir)) {
                    if (engineVer == engine.Version) {
                        logger.Debug("Engine path \"{0}\"", engine.Path ?? "NULL");
                        return engine;
                    }
                }
            }

            throw new pyRevitException(string.Format("Engine \"{0}\" is not available at \"{1}\"", engineVer, enginesDir));
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
                        engines.Add(new PyRevitEngine(engineVer, engineDir));
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
                                             PyRevitConsts.PyReviBinDirName,
                                             PyRevitConsts.PyReviBinEnginesDirName);
            if (!CommonUtils.VerifyPath(enginesDir)) {
                enginesDir = Path.Combine(clonePath,
                                          PyRevitConsts.PyRevitLibDirName,
                                          PyRevitConsts.PyRevitModuleDirName,
                                          PyRevitConsts.PyRevitModuleLoaderDirName,
                                          PyRevitConsts.PyRevitModuleAddinDirName);
                if (!CommonUtils.VerifyPath(enginesDir))
                    throw new pyRevitInvalidGitCloneException(clonePath);
            }

            return enginesDir;
        }

        // instance methods ==========================================================================================
        // public instance methods
        // rename clone
        public void Rename(string newName) {
            if (newName != null)
                Name = newName;
        }

        public List<PyRevitEngine> GetEngines() => GetEngines(ClonePath);

        public PyRevitEngine GetEngine(int engineVer = 000) => GetEngine(ClonePath, engineVer: engineVer);

        public List<PyRevitEngine> GetConfiguredEngines() => GetConfiguredEngines(ClonePath);

        public List<PyRevitDeployment> GetConfiguredDeployments() => GetConfiguredDeployments(ClonePath);

        public void SetBranch(string branchName) => SetBranch(ClonePath, branchName);

        public void SetTag(string tagName) => SetTag(ClonePath, tagName);

        public void SetCommit(string commitHash) => SetCommit(ClonePath, commitHash);

        public void SetOrigin(string originUrl) => SetOrigin(ClonePath, originUrl);

        public PyRevitCloneFromArchiveArgs DeploymentArgs => ReadDeploymentArgs(ClonePath);

        // private 
        private static PyRevitCloneFromArchiveArgs ReadDeploymentArgs(string clonePath) {
            var cloneMemoryFilePath = Path.Combine(clonePath, PyRevitConsts.DeployFromArchiveConfigsFilename);
            logger.Debug("Reading nogit clone parmeters from \"{0}\"", cloneMemoryFilePath);

            try {
                var contents = File.ReadAllLines(cloneMemoryFilePath);
                logger.Debug("Archive Path: \"{0}\"", contents[0]);
                logger.Debug("Branch: \"{0}\"", contents[1]);
                logger.Debug("Deployment: \"{0}\"", contents[2]);

                var args = new PyRevitCloneFromArchiveArgs {
                    Url = contents[0] == "" ? null : contents[0],
                    BranchName = contents[1] == "" ? null : contents[1],
                    DeploymentName = contents[2] == "" ? null : contents[2]
                };

                return args;
            }
            catch (Exception ex) {
                throw new pyRevitException(string.Format("Error reading deployment arguments from \"{0}\" | {1}",
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
                foreach (var subFolder in Directory.GetDirectories(startingPath)) {
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
                if (testPath == null || testPath == string.Empty)
                    return null;
            }

            logger.Debug("Valid clone found at: {0}", testPath);
            return testPath;
        }
    }
}
