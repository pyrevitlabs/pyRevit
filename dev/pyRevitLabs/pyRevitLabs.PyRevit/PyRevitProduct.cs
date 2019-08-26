using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using System.Web.Script.Serialization;

using Microsoft.Win32;

using pyRevitLabs.Common;
using pyRevitLabs.Common.Extensions;
using pyRevitLabs.NLog;

namespace pyRevitLabs.PyRevit {
    public class PyRevitProductInfo {
        public string product { get; set; }
        public string release { get; set; }
        public string version { get; set; }
        public string key { get; set; }
    }

    public class PyRevitProduct {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        private static List<PyRevitProductInfo> _cache = new List<PyRevitProductInfo>();
        private static string _cacheVersion = string.Empty;
        private static string _datasource = string.Empty;

        public const string DefaultDataSourceFileName = "pyrevit-products.json";
        public static string DefaultDataSourceFilePath => Path.Combine(CommonUtils.GetAssemblyPath<PyRevitProduct>(), DefaultDataSourceFileName);
        public static bool RevertToDefaultSourceOnErrors = true;
        public static string DataSourceFilePath {
            get {
                if (_datasource != null && _datasource != string.Empty && CommonUtils.VerifyFile(_datasource))
                    return _datasource;
                return DefaultDataSourceFilePath;
            }
            set {
                if (value != null && value != string.Empty)
                    _datasource = value;
            }
        }

        public static PyRevitProductInfo GetProductInfo(string identifier) {
            logger.Debug("Getting pyRevit product info for: {0}", identifier);

            if (identifier != null && identifier != string.Empty) {
                identifier = identifier.ToLower();
                foreach (PyRevitProductInfo prodInfo in GetAllProductInfo()) {
                    // release, version, and build are unique to hosts and could be used as identifiers
                    if (prodInfo.key.ToLower() == identifier
                        || prodInfo.version.ToLower() == identifier
                        || prodInfo.release.ToLower() == identifier)
                        return prodInfo;
                }
            }
            return null;
        }

        public static List<PyRevitProductInfo> GetAllProductInfo() {
            var dataSources = new List<string>() { DataSourceFilePath };
            if (RevertToDefaultSourceOnErrors)
                dataSources.Add(DefaultDataSourceFilePath);
            foreach (string dataSource in dataSources) {
                var cacheVersion = CommonUtils.GetFileSignature(dataSource);
                if (_cache is null || _cache.Count == 0 || (_cacheVersion != string.Empty && cacheVersion != _cacheVersion)) {
                    var productInfoDataSet = File.ReadAllText(dataSource);
                    _cache = new JavaScriptSerializer().Deserialize<List<PyRevitProductInfo>>(productInfoDataSet);
                    if (_cache != null && _cache.Count > 0) {
                        _cacheVersion = cacheVersion;
                        return _cache;
                    }
                }
            }
            return _cache;
        }
    }
}
