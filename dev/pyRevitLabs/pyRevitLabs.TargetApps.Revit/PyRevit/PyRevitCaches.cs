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

namespace pyRevitLabs.TargetApps.Revit {
    public static class PyRevitCaches {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        // pyrevit cache folder 
        // @reviewed
        public static string GetCacheDirectory(int revitYear) {
            return Path.Combine(PyRevit.pyRevitAppDataPath, revitYear.ToString());
        }

        // clear cache
        // @handled @logs
        public static void ClearCache(int revitYear) {
            // make sure all revit instances are closed
            if (CommonUtils.VerifyPath(PyRevit.pyRevitAppDataPath)) {
                RevitController.KillRunningRevits(revitYear);
                CommonUtils.DeleteDirectory(GetCacheDirectory(revitYear));
            }
            // it's just clearing caches. Let's not be paranoid and throw an exception is directory does not exist
            // if it's not there, the clear cache request is technically already satisfied
            //else
            //    throw new pyRevitResourceMissingException(pyRevitAppDataPath);
        }

        // clear all caches
        // @handled @logs
        public static void ClearAllCaches() {
            var cacheDirFinder = new Regex(@"\d\d\d\d");
            if (CommonUtils.VerifyPath(PyRevit.pyRevitAppDataPath)) {
                foreach (string subDir in Directory.GetDirectories(PyRevit.pyRevitAppDataPath)) {
                    var dirName = Path.GetFileName(subDir);
                    if (cacheDirFinder.IsMatch(dirName))
                        ClearCache(int.Parse(dirName));
                }
            }
            else
                throw new pyRevitResourceMissingException(PyRevit.pyRevitAppDataPath);
        }


    }
}
