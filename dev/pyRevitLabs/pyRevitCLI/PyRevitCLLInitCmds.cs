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
    internal static class PyRevitCLLInitCmds {
        static Logger logger = LogManager.GetCurrentClassLogger();

        internal static void
        InitExtension(bool ui, bool lib, bool run, string extensionName, string templatesDir, bool useTemplate) {
            PyRevitExtensionTypes extType = PyRevitExtensionTypes.Unknown;
            if (ui)
                extType = PyRevitExtensionTypes.UIExtension;
            else if (lib)
                extType = PyRevitExtensionTypes.LibraryExtension;
            else if (run)
                extType = PyRevitExtensionTypes.RunnerExtension;


            var extDirPostfix = PyRevitExtension.GetExtensionDirExt(extType);

            if (extensionName != null) {
                var pwd = Directory.GetCurrentDirectory();

                if (CommonUtils.EnsureFileNameIsUnique(pwd, extensionName)) {
                    var extDir = Path.Combine(
                        pwd,
                        string.Format("{0}{1}", extensionName, extDirPostfix)
                        );

                    var extTemplateDir = GetExtensionTemplate(extType, templatesDir: templatesDir);
                    if (useTemplate && extTemplateDir != null) {
                        CommonUtils.CopyDirectory(extTemplateDir, extDir);
                        Console.WriteLine(
                            string.Format("Extension directory created from template: \"{0}\"", extDir)
                            );
                    }
                    else {
                        if (!Directory.Exists(extDir)) {
                            var dinfo = Directory.CreateDirectory(extDir);
                            Console.WriteLine(string.Format("{0} directory created: \"{1}\"", extType, extDir));
                        }
                        else
                            throw new PyRevitException("Directory already exists.");
                    }

                }
                else
                    throw new PyRevitException(
                        string.Format("Another extension with name \"{0}\" already exists.", extensionName)
                        );
            }
        }
        
        internal static void
        InitBundle(bool tab, bool panel, bool panelopt, bool pull, bool split,
                   bool splitpush, bool push, bool smart, bool command,
                   string bundleName, string templatesDir, bool useTemplate) {
            // determine bundle
            PyRevitBundleTypes bundleType = PyRevitBundleTypes.Unknown;

            if (tab)
                bundleType = PyRevitBundleTypes.Tab;
            else if (panel)
                bundleType = PyRevitBundleTypes.Panel;
            else if (panelopt)
                bundleType = PyRevitBundleTypes.PanelButton;
            else if (pull)
                bundleType = PyRevitBundleTypes.PullDown;
            else if (split)
                bundleType = PyRevitBundleTypes.SplitButton;
            else if (splitpush)
                bundleType = PyRevitBundleTypes.SplitPushButton;
            else if (push)
                bundleType = PyRevitBundleTypes.PushButton;
            else if (smart)
                bundleType = PyRevitBundleTypes.SmartButton;
            else if (command)
                bundleType = PyRevitBundleTypes.NoButton;

            if (bundleType != PyRevitBundleTypes.Unknown) {
                if (bundleName != null) {
                    var pwd = Directory.GetCurrentDirectory();

                    if (CommonUtils.EnsureFileNameIsUnique(pwd, bundleName)) {
                        var bundleDir = Path.Combine(
                            pwd,
                            string.Format("{0}{1}", bundleName, PyRevitBundle.GetBundleDirExt(bundleType))
                            );

                        var bundleTempDir = GetBundleTemplate(bundleType, templatesDir: templatesDir);
                        if (useTemplate && bundleTempDir != null) {
                            CommonUtils.CopyDirectory(bundleTempDir, bundleDir);
                            Console.WriteLine(
                                string.Format("Bundle directory created from template: \"{0}\"", bundleDir)
                                );
                        }
                        else {
                            if (!Directory.Exists(bundleDir)) {
                                var dinfo = Directory.CreateDirectory(bundleDir);
                                Console.WriteLine(string.Format("Bundle directory created: \"{0}\"", bundleDir));
                            }
                            else
                                throw new PyRevitException("Directory already exists.");
                        }

                    }
                    else
                        throw new PyRevitException(
                            string.Format("Another bundle with name \"{0}\" already exists.", bundleName)
                            );
                }
            }

        }
        // private extensions and bundles
        private static string GetExtensionTemplate(PyRevitExtensionTypes extType, string templatesDir = null) {
            templatesDir = templatesDir != null ? templatesDir : PyRevitCLIAppCmds.GetTemplatesPath();
            if (CommonUtils.VerifyPath(templatesDir)) {
                var extTempPath =
                    Path.Combine(templatesDir, "template" + PyRevitExtension.GetExtensionDirExt(extType));
                if (CommonUtils.VerifyPath(extTempPath))
                    return extTempPath;
            }
            else
                throw new PyRevitException(
                    string.Format("Templates directory does not exist at \"{0}\"", templatesDir)
                    );


            return null;
        }

        private static string GetBundleTemplate(PyRevitBundleTypes bundleType, string templatesDir = null) {
            templatesDir = templatesDir != null ? templatesDir : PyRevitCLIAppCmds.GetTemplatesPath();
            if (CommonUtils.VerifyPath(templatesDir)) {
                var bundleTempPath =
                    Path.Combine(templatesDir, "template" + PyRevitBundle.GetBundleDirExt(bundleType));
                if (CommonUtils.VerifyPath(bundleTempPath))
                    return bundleTempPath;
            }
            else
                throw new PyRevitException(
                    string.Format("Templates directory does not exist at \"{0}\"", templatesDir)
                    );

            return null;
        }

    }
}
