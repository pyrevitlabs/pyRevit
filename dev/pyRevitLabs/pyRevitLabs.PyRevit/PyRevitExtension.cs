using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

using pyRevitLabs.Common;

using pyRevitLabs.Json.Linq;
using pyRevitLabs.NLog;

namespace pyRevitLabs.PyRevit {
    public enum PyRevitExtensionTypes {
        Unknown,
        UIExtension,
        LibraryExtension,
        RunnerExtension
    }

    public struct PyRevitExtensionMetaData {
        public string Name;
        public PyRevitExtensionTypes Type;
        public string Description;
        public string Author;
        public string AuthorProfile;
        public string Url;
        public string Website;
        public string ImageUrl;
        public List<PyRevitExtensionMetaData> Dependencies;

        public bool DefaultEnabled;
        public bool RocketModeCompatible;
    }

    public class PyRevitExtensionDefinition {
        private dynamic _jsonObj;

        public PyRevitExtensionDefinition(JObject jsonObj) {
            _jsonObj = jsonObj;
            if (_jsonObj is null)
                throw new PyRevitException("jsonObj can not be null.");
        }

        public PyRevitExtensionDefinition(string extDefJsonFile) {
            _jsonObj = JObject.Parse(File.ReadAllText(extDefJsonFile));
            if (_jsonObj is null)
                throw new PyRevitException("jsonObj can not be null.");
        }

        public override string ToString() {
            return string.Format("Name: \"{0}\" | Type: \"{1}\" | Repo: \"{2}\"", Name, Type, Url);
        }

        public bool BuiltIn { get { return bool.Parse(_jsonObj.builtin); } }

        public bool DefaultEnabled { get { return bool.Parse(_jsonObj.default_enabled); } }

        public bool RocketModeCompatible { get { return bool.Parse(_jsonObj.rocket_mode_compatible); } }

        public string Name { get { return _jsonObj.name; } }

        public PyRevitExtensionTypes Type {
            get {
                switch ("." + _jsonObj.type) {
                    case PyRevit.ExtensionUIPostfix: return PyRevitExtensionTypes.UIExtension;
                    case PyRevit.ExtensionLibraryPostfix: return PyRevitExtensionTypes.LibraryExtension;
                    case PyRevit.ExtensionRunnerPostfix: return PyRevitExtensionTypes.RunnerExtension;
                    default: return PyRevitExtensionTypes.Unknown;
                }
            }
        }

        public string Description { get { return _jsonObj.description; } }

        public string Author { get { return _jsonObj.author; } }

        public string AuthorProfile { get { return _jsonObj.author_url; } }

        public string Url { get { return _jsonObj.url; } }

        public string Website { get { return _jsonObj.website; } }

        public string ImageUrl { get { return _jsonObj.image; } }

        public dynamic Templates { get { return _jsonObj.templates; } }

        public dynamic Dependencies { get { return _jsonObj.dependencies; } }
    }

    public class PyRevitExtension {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        public PyRevitExtension(string extensionPath) {
            InstallPath = extensionPath;
            var extDefFile = GetExtensionDefFilePath(InstallPath);
            if (CommonUtils.VerifyFile(extDefFile))
                Definition = new PyRevitExtensionDefinition(extDefFile);
            else {
                // if def file is not found try to grab the definitions from registered extensions
                try {
                    Definition = PyRevitExtensions.FindRegisteredExtension(Name);
                }
                catch {
                    // let Definition be null if extension is not registered
                }
            }
        }

        public string InstallPath { get; private set; }

        public PyRevitExtensionDefinition Definition { get; private set; } = null;

        public override string ToString() {
            return string.Format("{0} | Type: {1} | Repo: \"{2}\" | Installed: \"{3}\"",
                                 Name, Type, Url, InstallPath);
        }

        // grab parameters from definition or set to default
        public bool BuiltIn => Definition != null ? Definition.BuiltIn : false;
        public bool RocketModeCompatible => Definition != null ? Definition.RocketModeCompatible : false;
        // grab name from path if def does not exist
        public string Name => Definition != null ? Definition.Name : GetExtensionNameFromInstall(InstallPath);
        public PyRevitExtensionTypes Type => Definition != null ? Definition.Type : PyRevitExtensionTypes.Unknown;
        public string Description => Definition != null ? Definition.Description : "";
        public string Author => Definition != null ? Definition.Author : "";
        public string AuthorProfile => Definition != null ? Definition.AuthorProfile : "";
        public string Url {
            get {
                // try to get origin url from repo
                string originUrl = "";
                try {
                    originUrl = Origin;
                }
                catch {
                    // if not found return url from definition
                    return Definition != null ? Definition.Url : "";
                }

                return originUrl;
            }
        }
        public string Website => Definition != null ? Definition.Website : "";
        public string ImageUrl => Definition != null ? Definition.ImageUrl : "";
        public dynamic Templates => Definition != null ? Definition.Templates : null;
        public dynamic Dependencies => Definition != null ? Definition.Dependencies : null;

        public string ConfigName => MakeConfigName(Name, Type);

        // repo origin
        public string Origin => GetOrigin(InstallPath);
        public void SetOrigin(string originUrl) => SetOrigin(InstallPath, originUrl);

        // find a run command
        public string GetRunCommand(string commandName) => GetRunCommand(InstallPath, commandName);

        // static methods ============================================================================================
        private static string GetExtensionNameFromInstall(string extPath) {
            string extName = Path.GetFileName(extPath);
            foreach (string extPostFix in GetAllExtentionDirExts())
                extName = extName.Replace(extPostFix, "");
            return extName;
        }

        public static string GetExtensionDefFilePath(string extPath) =>
            Path.Combine(extPath, PyRevit.ExtensionDefFileName);

        public static string GetRunCommand(string extPath, string commandName) {
            foreach (var filePath in Directory.GetFiles(extPath)) {
                var fileName = Path.GetFileName(filePath);
                if (CommonUtils.VerifyPythonScript(filePath)
                        && fileName.ToLower().EndsWith(PyRevit.ExtensionRunnerCommandPostfix)
                        && fileName.ToLower().Replace(PyRevit.ExtensionRunnerCommandPostfix, "") == commandName.ToLower())
                    return filePath;
            }

            throw new PyRevitException(string.Format("Run command \"{0}\" does not exist.", commandName));
        }

        // get origin remote url
        // @handled @logs
        public static string GetOrigin(string installPath) {
            return GitInstaller.GetRemoteUrl(installPath, PyRevit.DefaultExtensionRemoteName);
        }

        // set origin url to new url
        // @handled @logs
        public static void SetOrigin(string installPath, string originUrl) {
            if (originUrl != null)
                GitInstaller.SetRemoteUrl(installPath, PyRevit.DefaultExtensionRemoteName, originUrl);
        }

        public static string MakeConfigName(string extName, PyRevitExtensionTypes extType) {
            return extName + GetExtensionDirExt(extType);
        }

        public static bool IsExtensionDirectory(string path) {
            foreach (string extPostFix in GetAllExtentionDirExts())
                if (path.EndsWith(extPostFix))
                    return true;
            return false;
        }

        public static List<PyRevitExtensionTypes> GetAllExtensionTypes() {
            var allExtTypes = new List<PyRevitExtensionTypes>();
            foreach (PyRevitExtensionTypes extType in Enum.GetValues(typeof(PyRevitExtensionTypes)))
                if (extType != PyRevitExtensionTypes.Unknown)
                    allExtTypes.Add(extType);
            return allExtTypes;
        }

        public static string GetExtensionDirExt(PyRevitExtensionTypes extType) {
            switch (extType) {
                case PyRevitExtensionTypes.UIExtension: return PyRevit.ExtensionUIPostfix;
                case PyRevitExtensionTypes.LibraryExtension: return PyRevit.ExtensionLibraryPostfix;
                case PyRevitExtensionTypes.RunnerExtension: return PyRevit.ExtensionRunnerPostfix;
                default: return null;
            }
        }

        public static List<string> GetAllExtentionDirExts() {
            var extPostfixes = new List<string>();
            foreach (var extType in GetAllExtensionTypes())
                extPostfixes.Add(GetExtensionDirExt(extType));
            return extPostfixes;
        }

        public static PyRevitExtensionTypes GetExtensionTypeFromDirExt(string dirExt) {
            foreach (var extType in GetAllExtensionTypes())
                if (dirExt.EndsWith(GetExtensionDirExt(extType)))
                    return extType;
            return PyRevitExtensionTypes.Unknown;
        }

        public static List<PyRevitExtension> FindExtensions(string searchPath) {
            var installedExtensions = new List<PyRevitExtension>();

            logger.Debug("Looking for installed extensions under \"{0}\"...", searchPath);
            foreach (var subdir in Directory.GetDirectories(searchPath)) {
                if (IsExtensionDirectory(subdir)) {
                    logger.Debug("Found installed extension \"{0}\"...", subdir);
                    installedExtensions.Add(new PyRevitExtension(subdir));
                }
            }

            return installedExtensions;
        }
    }
}
