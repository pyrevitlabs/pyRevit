using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

using pyRevitLabs.Common;

using Newtonsoft.Json.Linq;
using NLog;

namespace pyRevitLabs.TargetApps.Revit {
    public class PyRevitExtension {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        private dynamic _jsonObj;

        public PyRevitExtension(JObject jsonObj) {
            _jsonObj = jsonObj;
        }

        public PyRevitExtension(string extensionPath) {
            InstallPath = extensionPath;
        }

        public override string ToString() { return _jsonObj.ToString(); }

        public static string MakeConfigName(string extName, PyRevitExtensionTypes extType) {
            return extType ==
                PyRevitExtensionTypes.UIExtension ?
                    extName + PyRevitConsts.ExtensionUIPostfix : extName + PyRevitConsts.ExtensionLibraryPostfix;
        }

        public static bool IsExtensionDirectory(string path) {
            return path.EndsWith(PyRevitConsts.ExtensionUIPostfix)
                    || path.EndsWith(PyRevitConsts.ExtensionLibraryPostfix);
        }

        private string GetNameFromInstall() {
            return Path.GetFileName(InstallPath)
                       .Replace(PyRevitConsts.ExtensionUIPostfix, "")
                       .Replace(PyRevitConsts.ExtensionLibraryPostfix, "");
        }

        public bool BuiltIn { get { return bool.Parse(_jsonObj.builtin); } }

        public bool RocketModeCompatible { get { return bool.Parse(_jsonObj.rocket_mode_compatible); } }

        public string Name {
            get {
                if (_jsonObj != null)
                    return _jsonObj.name;
                else
                    return GetNameFromInstall();
            }
        }

        public string Description { get { return _jsonObj != null ? _jsonObj.description : ""; } }

        public string Author { get { return _jsonObj != null ? _jsonObj.author : ""; } }

        public string AuthorProfile { get { return _jsonObj != null ? _jsonObj.author_url : ""; } }

        public string Url { get { return _jsonObj != null ? _jsonObj.url : ""; } }

        public string Origin { get { return GetOrigin(InstallPath); } }

        public string Website { get { return _jsonObj != null ? _jsonObj.website : ""; } }

        public string InstallPath { get; private set; }

        public PyRevitExtensionTypes Type {
            get {
                if (_jsonObj != null) {
                    return _jsonObj.type == "extension" ?
                        PyRevitExtensionTypes.UIExtension : PyRevitExtensionTypes.LibraryExtension;
                }
                else if (InstallPath != null) {
                    return InstallPath.Contains(PyRevitConsts.ExtensionUIPostfix) ?
                        PyRevitExtensionTypes.UIExtension : PyRevitExtensionTypes.LibraryExtension;
                }

                return PyRevitExtensionTypes.Unknown;
            }
        }

        public string ConfigName {
            get {
                return MakeConfigName(Name, Type);
            }
        }

        // get origin remote url
        // @handled @logs
        public static string GetOrigin(string installPath) {
            return GitInstaller.GetRemoteUrl(installPath, PyRevitConsts.DefaultExtensionRemoteName);
        }

        // set origin url to new url
        // @handled @logs
        public static void SetOrigin(string installPath, string originUrl) {
            if (originUrl != null)
                GitInstaller.SetRemoteUrl(installPath, PyRevitConsts.DefaultExtensionRemoteName, originUrl);
        }

        public void SetOrigin(string originUrl) => SetOrigin(InstallPath, originUrl);
    }
}
