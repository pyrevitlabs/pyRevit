using System;
using System.IO;

using pyRevitLabs.Common;
using pyRevitLabs.NLog;

namespace pyRevitLabs.TargetApps.Revit {
    public enum RevitCacheType {
        BIM360Cache
    }

    public class RevitCaches {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        // Revit 2024 is the first version to support custom cloud cache paths via Revit.ini
        public const int CustomCacheMinVersion = 2024;
        public const string CloudModelCacheSection = "CloudModelCache";
        public const string CloudModelCacheKey = "CacheLocation";

        // default bim360 cache folder under %LOCALAPPDATA%
        public static string GetDefaultBIM360CacheDirectory(int revitYear) {
            return Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "Autodesk",
                "Revit",
                $"Autodesk Revit {revitYear}",
                "CollaborationCache");
        }

        // Revit.ini path under %APPDATA% for the given product year
        public static string GetRevitIniPath(int revitYear) {
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
                logger.Debug("Revit.ini not found: {0}", iniPath);
                return null;
            }

            try {
                string currentSection = null;
                foreach (var rawLine in File.ReadLines(iniPath)) {
                    var line = rawLine.Trim();
                    if (line.Length == 0 || line.StartsWith(";") || line.StartsWith("#"))
                        continue;

                    if (line.StartsWith("[") && line.EndsWith("]")) {
                        currentSection = line.Substring(1, line.Length - 2).Trim();
                        continue;
                    }

                    if (!string.Equals(currentSection, CloudModelCacheSection, StringComparison.OrdinalIgnoreCase))
                        continue;

                    var idx = line.IndexOf('=');
                    if (idx < 0)
                        continue;

                    var key = line.Substring(0, idx).Trim();
                    if (!string.Equals(key, CloudModelCacheKey, StringComparison.OrdinalIgnoreCase))
                        continue;

                    var value = StripSurroundingQuotes(line.Substring(idx + 1).Trim());
                    if (string.IsNullOrWhiteSpace(value)) {
                        logger.Debug("Empty CacheLocation in Revit.ini: {0}", iniPath);
                        return null;
                    }

                    logger.Debug("CacheLocation from Revit.ini ({0}): {1}", iniPath, value);
                    return value;
                }
            }
            catch (Exception ex) {
                logger.Warn("Failed to read Revit.ini @ {0} | {1}", iniPath, ex.Message);
            }

            return null;
        }

        /// <summary>
        /// Resolve a custom BIM360/ACC cache root from Revit.ini for Revit 2024+.
        /// Returns null so callers fall back to the default location.
        /// </summary>
        public static string GetCustomBIM360CacheDirectory(int revitYear, string iniPath = null) {
            if (revitYear < CustomCacheMinVersion)
                return null;

            var pathToIni = string.IsNullOrWhiteSpace(iniPath) ? GetRevitIniPath(revitYear) : iniPath;
            logger.Debug("Checking Revit.ini for custom cache path: {0}", pathToIni);

            var raw = ReadCloudModelCacheLocation(pathToIni);
            if (string.IsNullOrWhiteSpace(raw))
                return null;

            var customPath = Path.GetFullPath(CommonUtils.ExpandEnvironmentPath(raw));
            if (!CommonUtils.VerifyPath(customPath)) {
                logger.Debug("Custom cache path from Revit.ini does not exist: {0}", customPath);
                return null;
            }

            logger.Debug("Using custom cache root from Revit.ini: {0}", customPath);
            return customPath;
        }

        // bim360 cache folder (custom CacheLocation for 2024+ when present, else default)
        public static string GetBIM360CacheDirectory(int revitYear) {
            var custom = GetCustomBIM360CacheDirectory(revitYear);
            if (!string.IsNullOrEmpty(custom))
                return custom;
            return GetDefaultBIM360CacheDirectory(revitYear);
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
