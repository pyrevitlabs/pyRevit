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
using pyRevitLabs.PyRevit;
using pyRevitLabs.Language.Properties;

using pyRevitLabs.NLog;
using pyRevitLabs.Json;
using pyRevitLabs.Json.Serialization;

using Console = Colorful.Console;

namespace pyRevitCLI {
    internal static class PyRevitCLIExtensionCmds {
        static Logger logger = LogManager.GetCurrentClassLogger();

        internal static void
        PrintExtensions(IEnumerable<PyRevitExtension> extList = null, string headerPrefix = "Installed") {
            if (extList is null)
                extList = PyRevitExtensions.GetInstalledExtensions();

            PyRevitCLIAppCmds.PrintHeader(string.Format("{0} Extensions", headerPrefix));
            foreach (PyRevitExtension ext in extList.OrderBy(x => x.Name))
                Console.WriteLine(ext);
        }

        internal static void
        PrintExtensionDefinitions(string searchPattern, string headerPrefix = "Registered") {
            PyRevitCLIAppCmds.PrintHeader(string.Format("{0} Extensions", headerPrefix));
            foreach (PyRevitExtensionDefinition ext in PyRevitExtensions.LookupRegisteredExtensions(searchPattern))
                Console.WriteLine(ext);
        }

        internal static void
        PrintExtensionSearchPaths() {
            PyRevitCLIAppCmds.PrintHeader("Default Extension Search Path");
            Console.WriteLine(PyRevitConsts.DefaultExtensionsPath);
            PyRevitCLIAppCmds.PrintHeader("Extension Search Paths");
            foreach (var searchPath in PyRevitExtensions.GetRegisteredExtensionSearchPaths())
                Console.WriteLine(searchPath);
        }

        internal static void
        PrintExtensionLookupSources() {
            PyRevitCLIAppCmds.PrintHeader("Extension Sources - Default");
            Console.WriteLine(PyRevitExtensions.GetDefaultExtensionLookupSource());
            PyRevitCLIAppCmds.PrintHeader("Extension Sources - Additional");
            foreach (var extLookupSrc in PyRevitExtensions.GetRegisteredExtensionLookupSources())
                Console.WriteLine(extLookupSrc);
        }

        internal static void
        Extend(string extName, string destPath, string branchName) {
            var ext = PyRevitExtensions.FindRegisteredExtension(extName);
            if (ext != null) {
                logger.Debug("Matching extension found \"{0}\"", ext.Name);
                PyRevitExtensions.InstallExtension(ext, destPath, branchName);
            }
            else {
                if (Errors.LatestError == ErrorCodes.MoreThanOneItemMatched)
                    throw new PyRevitException(
                        string.Format("More than one extension matches the name \"{0}\"",
                                        extName));
                else
                    throw new PyRevitException(
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

            PyRevitExtensions.InstallExtension(extName, extType, repoUrl, destPath, branchName);
        }

        internal static void
        ProcessExtensionInfoCommands(string extName, bool info, bool help, bool open) {
            if (extName != null) {
                var ext = PyRevitExtensions.FindRegisteredExtension(extName);
                if (Errors.LatestError == ErrorCodes.MoreThanOneItemMatched)
                    logger.Warn("More than one extension matches the search pattern \"{0}\"", extName);
                else {
                    if (info)
                        Console.WriteLine(ext.ToString());
                    else if (help)
                        Process.Start(ext.Website);
                    else if (open) {
                        var instExt = PyRevitExtensions.GetInstalledExtension(extName);
                        CommonUtils.OpenInExplorer(instExt.InstallPath);
                    }
                }
            }
        }

        internal static void
        DeleteExtension(string extName) {
            PyRevitExtensions.UninstallExtension(extName);
        }

        internal static void
        GetSetExtensionOrigin(string extName, string originUrl, bool reset) {
            if (extName != null) {
                var extension = PyRevitExtensions.GetInstalledExtension(extName);
                if (extension != null) {
                    if (reset) {
                        var ext = PyRevitExtensions.FindRegisteredExtension(extension.Name);
                        if (ext != null)
                            extension.SetOrigin(ext.Url);
                        else
                            throw new PyRevitException(
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
                foreach (string regSearchPath in PyRevitExtensions.GetRegisteredExtensionSearchPaths())
                    PyRevitExtensions.UnregisterExtensionSearchPath(regSearchPath);
            else
                PyRevitExtensions.UnregisterExtensionSearchPath(searchPath);
        }

        internal static void
        AddExtensionPath(string searchPath) {
            if (searchPath != null)
                PyRevitExtensions.RegisterExtensionSearchPath(searchPath);
        }

        internal static void
        ToggleExtension(bool enable, string extName) {
            if (extName != null) {
                if (enable)
                    PyRevitExtensions.EnableExtension(extName);
                else
                    PyRevitExtensions.DisableExtension(extName);
            }
        }

        internal static void
        ForgetExtensionLookupSources(bool all, string lookupPath) {
            if (all)
                PyRevitExtensions.UnregisterAllExtensionLookupSources();
            else if (lookupPath != null)
                PyRevitExtensions.UnregisterExtensionLookupSource(lookupPath);
        }

        internal static void
        AddExtensionLookupSource(string lookupPath) {
            if (lookupPath != null)
                PyRevitExtensions.RegisterExtensionLookupSource(lookupPath);
        }

        internal static void
        UpdateExtension(bool all, string extName) {
            if (all)
                PyRevitExtensions.UpdateAllInstalledExtensions();
            else if (extName != null)
                PyRevitExtensions.UpdateExtension(extName);
        }
    }
}
