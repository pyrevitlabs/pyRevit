using System;
using System.IO;

using MadMilkman.Ini;

using pyRevitLabs.Common;
using pyRevitLabs.NLog;

namespace pyRevitLabs.TargetApps.Revit {
    public enum RevitCacheType {
        BIM360Cache
    }

    public class RevitCaches {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        // Revit 2024 is the first version to support custom cloud cache paths
        public const int CustomCacheMinVersion = 2024;
        public const string CloudModelCacheSection = "CloudModelCache";
        public const string CloudModelCacheKey = "CacheLocation";

        // bim360 cache folder (default location)
        public static string GetBIM360CacheDirectory(int revitYear) {
            return Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "Autodesk",
                "Revit",
                $"Autodesk Revit {revitYear}",
                "CollaborationCache");
        }

        // path to Revit.ini for a given revit year
        public static string GetRevitIniFile(int revitYear) {
            return Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                "Autodesk",
                "Revit",
                $"Autodesk Revit {revitYear}",
                "Revit.ini");
        }

        /// <summary>
        /// Read CacheLocation from a Revit.ini file without expanding env vars.
        /// Returns null when the section/key is missing or empty.
        /// </summary>
        public static string ReadCloudModelCacheLocation(string iniPath) {
            if (!CommonUtils.VerifyFile(iniPath)) {
                logger.Debug("Revit.ini not found @ {0}", iniPath);
                return null;
            }

            try {
                var cfgOps = new IniOptions();
                cfgOps.KeySpaceAroundDelimiter = true;
                var iniFile = new IniFile(cfgOps);

                // Allow Revit (or another process) to keep the file open while we read.
                using (var iniStream = File.Open(iniPath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite)) {
                    iniFile.Load(iniStream);
                }

                if (!iniFile.Sections.Contains(CloudModelCacheSection))
                    return null;

                var section = iniFile.Sections[CloudModelCacheSection];
                if (!section.Keys.Contains(CloudModelCacheKey))
                    return null;

                var rawValue = section.Keys[CloudModelCacheKey].Value as string;
                if (string.IsNullOrWhiteSpace(rawValue)) {
                    logger.Debug("Empty CacheLocation in Revit.ini: {0}", iniPath);
                    return null;
                }

                var value = StripSurroundingQuotes(rawValue.Trim());
                if (string.IsNullOrWhiteSpace(value))
                    return null;

                logger.Debug("CacheLocation from Revit.ini ({0}): {1}", iniPath, value);
                return value;
            }
            catch (Exception ex) {
                logger.Warn("Failed to read Revit.ini @ {0} | {1}", iniPath, ex.Message);
                return null;
            }
        }

        /// <summary>
        /// Read the custom cloud cache location from Revit.ini, if configured.
        /// Returns null when Revit.ini is missing, the version is too old,
        /// or the section/key is not present or empty, so callers fall back
        /// to the default cache directory.
        /// </summary>
        public static string GetCustomBIM360CacheDirectory(int revitYear, string iniPath = null) {
            if (revitYear < CustomCacheMinVersion)
                return null;

            var pathToIni = string.IsNullOrWhiteSpace(iniPath) ? GetRevitIniFile(revitYear) : iniPath;
            logger.Debug("Checking Revit.ini for custom cache path: {0}", pathToIni);

            var raw = ReadCloudModelCacheLocation(pathToIni);
            if (string.IsNullOrWhiteSpace(raw))
                return null;

            var customPath = Path.GetFullPath(CommonUtils.ExpandEnvironmentPath(raw));
            logger.Debug("custom cache root from Revit.ini: {0}", customPath);
            return customPath;
        }

        /// <summary>
        /// Resolve the cache directory to use: custom location if configured
        /// and it exists on disk, otherwise the default location.
        /// </summary>
        public static string GetActiveBIM360CacheDirectory(int revitYear, string iniPath = null) {
            var customPath = GetCustomBIM360CacheDirectory(revitYear, iniPath);
            if (customPath != null && CommonUtils.VerifyPath(customPath))
                return customPath;

            return GetBIM360CacheDirectory(revitYear);
        }

        // clear bim360 cache
        public static void ClearCache(int revitYear, RevitCacheType cacheType) {
            // make sure all revit instances are closed
            switch (cacheType) {
                case RevitCacheType.BIM360Cache:
                    var cachePath = GetActiveBIM360CacheDirectory(revitYear);
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
            foreach (RevitProduct revitProduct in RevitProduct.ListInstalledProducts())
                ClearCache(revitProduct.ProductYear, cacheType);
        }

        private static string StripSurroundingQuotes(string value) {
            if (value == null || value.Length < 2)
                return value;
            if ((value[0] == '"' && value[value.Length - 1] == '"') ||
                (value[0] == '\'' && value[value.Length - 1] == '\''))
                return value.Substring(1, value.Length - 2);
            return value;
        }
    }
}
