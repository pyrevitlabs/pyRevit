using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading.Tasks;

using pyRevitLabs.Common;
using pyRevitLabs.NLog;

namespace pyRevitLabs.TargetApps.Revit {
    public enum RevitCacheType {
        BIM360Cache
    }

    public class RevitCaches {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        // bim360 cache folder 
        public static string GetBIM360CacheDirectory(int revitYear) {
            return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Autodesk", "Revit", $"Autodesk Revit {revitYear.ToString()}", "CollaborationCache");
        }

        // clear bim360 cache
        public static void ClearCache(int revitYear, RevitCacheType cacheType) {
            // make sure all revit instances are closed
            switch (cacheType) {
                case RevitCacheType.BIM360Cache:
                    var cachePath = GetBIM360CacheDirectory(revitYear);
                    logger.Debug("Attempting to clean {0}", cachePath);
                    if (CommonUtils.VerifyPath(cachePath)) {
                        RevitController.KillRunningRevits(revitYear);
                        CommonUtils.DeleteDirectory(cachePath);
                    }
                    break;
            }
        }

        // clear all bim360 caches
        public static void ClearAllCaches(RevitCacheType cacheType) {
            var cacheDirFinder = new Regex(@"\d\d\d\d");
            foreach (RevitProduct revitProduct in RevitProduct.ListInstalledProducts())
                ClearCache(revitProduct.ProductYear, cacheType);
        }
    }
}
