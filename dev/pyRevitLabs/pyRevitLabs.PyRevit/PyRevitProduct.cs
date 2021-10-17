using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;

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

    public class PyRevitProductData {
        public static string ProductFileURL = GithubAPI.GetRawUrl(PyRevitLabsConsts.OriginalRepoId, PyRevitLabsConsts.TragetBranch, @"bin/pyrevit-products.json");

        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        private static JSONDataSource<PyRevitProductInfo> _dstore = new JSONDataSource<PyRevitProductInfo>(
            "pyrevit-products.json",
            dataSourceUrl: ProductFileURL,
            dataCachePath: PyRevitLabsConsts.CacheDirectory
            );

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

        public static List<PyRevitProductInfo> GetAllProductInfo() => _dstore.GetAllData();

        public static void Update() => _dstore.UpdateData(forceUpdate: true);
    }

    public class PyRevitProduct {
        public PyRevitProduct(PyRevitProductInfo prodInfo) {
            Name = prodInfo.product;
            Release = prodInfo.release;
            try {
                Version = new Version(prodInfo.version);
            }
            catch {
                Version = null;
            }
            InstallerId = prodInfo.key;
        }

        public override string ToString() {
            return string.Format("{0} | Version: {1} | Release: {2} | Installer Id: \"{3}\"", Name, Version, Release, InstallerId);
        }

        public override int GetHashCode() {
            return InstallerId.GetHashCode();
        }


        public string Name { get; set; }
        public string Release { get; set; }
        public Version Version { get; set; }
        public string InstallerId { get; set; }

        public static PyRevitProduct LookupRevitProduct(string releaseOrVersionOrIdString) {
            var prodInfo = PyRevitProductData.GetProductInfo(releaseOrVersionOrIdString);
            if (prodInfo != null)
                return new PyRevitProduct(prodInfo);
            return null;
        }

        public static List<PyRevitProduct> ListKnownProducts() {
            var products = new List<PyRevitProduct>();
            foreach (PyRevitProductInfo prodInfo in PyRevitProductData.GetAllProductInfo())
                products.Add(new PyRevitProduct(prodInfo));
            return products;
        }
    }

}
