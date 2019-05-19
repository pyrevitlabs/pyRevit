using System;
using System.Collections.Generic;
using System.Linq;
using System.IO;
using System.Text;
using System.Threading.Tasks;
using System.Drawing;
using System.Diagnostics;

using pyRevitLabs.Common;
using pyRevitLabs.CommonCLI;
using pyRevitLabs.Common.Extensions;
using pyRevitLabs.TargetApps.Revit;
using pyRevitLabs.Language.Properties;

using NLog;
using pyRevitLabs.Json;
using pyRevitLabs.Json.Serialization;

using Console = Colorful.Console;

namespace pyRevitManager {
    internal static class PyRevitCLIExtensionCmds {
        static Logger logger = LogManager.GetCurrentClassLogger();

        internal static void
        PrintExtensions(IEnumerable<PyRevitExtension> extList = null, string headerPrefix = "Installed") {
            if (extList == null)
                extList = PyRevit.GetInstalledExtensions();

            PyRevitCLIAppCmds.PrintHeader(string.Format("{0} Extensions", headerPrefix));
            foreach (PyRevitExtension ext in extList.OrderBy(x => x.Name))
                Console.WriteLine(ext);
        }

        internal static void
        PrintExtensionDefinitions(string searchPattern, string headerPrefix = "Registered") {
            PyRevitCLIAppCmds.PrintHeader(string.Format("{0} Extensions", headerPrefix));
            foreach (PyRevitExtensionDefinition ext in PyRevit.LookupRegisteredExtensions(searchPattern))
                Console.WriteLine(ext);
        }

        internal static void
        PrintExtensionSearchPaths() {
            PyRevitCLIAppCmds.PrintHeader("Default Extension Search Path");
            Console.WriteLine(PyRevit.pyRevitDefaultExtensionsPath);
            PyRevitCLIAppCmds.PrintHeader("Extension Search Paths");
            foreach (var searchPath in PyRevit.GetRegisteredExtensionSearchPaths())
                Console.WriteLine(searchPath);
        }

        internal static void
        PrintExtensionLookupSources() {
            PyRevitCLIAppCmds.PrintHeader("Extension Sources - Default");
            Console.WriteLine(PyRevit.GetDefaultExtensionLookupSource());
            PyRevitCLIAppCmds.PrintHeader("Extension Sources - Additional");
            foreach (var extLookupSrc in PyRevit.GetRegisteredExtensionLookupSources())
                Console.WriteLine(extLookupSrc);
        }

        internal static void
        Extend(string extName, string destPath, string branchName) {
            var ext = PyRevit.FindRegisteredExtension(extName);
            if (ext != null) {
                logger.Debug("Matching extension found \"{0}\"", ext.Name);
                PyRevit.InstallExtension(ext, destPath, branchName);
            }
            else {
                if (Errors.LatestError == ErrorCodes.MoreThanOneItemMatched)
                    throw new pyRevitException(
                        string.Format("More than one extension matches the name \"{0}\"",
                                        extName));
                else
                    throw new pyRevitException(
                        string.Format("Not valid extension name or repo url \"{0}\"",
                                        extName));
            }

        }

        internal static void
        Extend(bool ui, bool lib, bool run, string extName, string destPath, string repoUrl, string branchName) {
            PyRevitExtensionTypes extType = PyRevitExtensionTypes.Unknown;
            if (ui)
                extType = PyRevitExtensionTypes.UIExtension;
            else if (lib)
                extType = PyRevitExtensionTypes.LibraryExtension;
            else if (run)
                extType = PyRevitExtensionTypes.RunnerExtension;

            PyRevit.InstallExtension(extName, extType, repoUrl, destPath, branchName);
        }

        internal static void
        ProcessExtensionInfoCommands(string extName, bool info, bool help, bool open) {
            if (extName != null) {
                var ext = PyRevit.FindRegisteredExtension(extName);
                if (Errors.LatestError == ErrorCodes.MoreThanOneItemMatched)
                    logger.Warn("More than one extension matches the search pattern \"{0}\"", extName);
                else {
                    if (info)
                        Console.WriteLine(ext.ToString());
                    else if (help)
                        Process.Start(ext.Website);
                    else if (open) {
                        var instExt = PyRevit.GetInstalledExtension(extName);
                        CommonUtils.OpenInExplorer(instExt.InstallPath);
                    }
                }
            }
        }

        internal static void
        DeleteExtension(string extName) {
            PyRevit.UninstallExtension(extName);
        }

        internal static void
        GetSetExtensionOrigin(string extName, string originUrl, bool reset) {
            if (extName != null) {
                var extension = PyRevit.GetInstalledExtension(extName);
                if (extension != null) {
                    if (reset) {
                        var ext = PyRevit.FindRegisteredExtension(extension.Name);
                        if (ext != null)
                            extension.SetOrigin(ext.Url);
                        else
                            throw new pyRevitException(
                                string.Format("Can not find the original url in the extension " +
                                              "database for extension \"{0}\"",
                                              extension.Name));
                    }
                    else if (originUrl != null) {
                        extension.SetOrigin(originUrl);
                    }
                    else {
                        Console.WriteLine(string.Format("Extension \"{0}\" origin is at \"{1}\"",
                                                        extension.Name, extension.Origin));
                    }
                }
            }
        }

        internal static void
        ForgetAllExtensionPaths(bool all, string searchPath) {
            if (all)
                foreach (string regSearchPath in PyRevit.GetRegisteredExtensionSearchPaths())
                    PyRevit.UnregisterExtensionSearchPath(regSearchPath);
            else
                PyRevit.UnregisterExtensionSearchPath(searchPath);
        }

        internal static void
        AddExtensionPath(string searchPath) {
            if (searchPath != null)
                PyRevit.RegisterExtensionSearchPath(searchPath);
        }

        internal static void
        ToggleExtension(bool enable, string extName) {
            if (extName != null) {
                if (enable)
                    PyRevit.EnableExtension(extName);
                else
                    PyRevit.DisableExtension(extName);
            }
        }

        internal static void
        ForgetExtensionLookupSources(bool all, string lookupPath) {
            if (all)
                PyRevit.UnregisterAllExtensionLookupSources();
            else if (lookupPath != null)
                PyRevit.UnregisterExtensionLookupSource(lookupPath);
        }

        internal static void
        AddExtensionLookupSource(string lookupPath) {
            if (lookupPath != null)
                PyRevit.RegisterExtensionLookupSource(lookupPath);
        }

        internal static void
        UpdateExtension(bool all, string extName) {
            if (all)
                PyRevit.UpdateAllInstalledExtensions();
            else if (extName != null)
                PyRevit.UpdateExtension(extName);
        }
    }
}
