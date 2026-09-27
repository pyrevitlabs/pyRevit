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

namespace pyRevitLabs.TargetApps.Revit {
    public class HostProductInfoMeta {
        public string schema { get; set; } = "1.0";
        public string source { get; set; }
    }

    public class HostProductInfo {
        public HostProductInfoMeta meta { get; set; }
        public string product { get; set; }
        public string release { get; set; }
        public string version { get; set; }
        public string build { get; set; }
        public string target { get; set; }
        public string notes { get; set; }
    }

    public class RevitProductData {
        public static string HostFileURL = GithubAPI.GetRawUrl(PyRevitLabsConsts.OriginalRepoId, PyRevitLabsConsts.HostsFileBranch, @"release/pyrevit-hosts.json");

        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        private static JSONDataSource<HostProductInfo> _dstore = new JSONDataSource<HostProductInfo>(
            "pyrevit-hosts.json",
            dataSourceUrl: HostFileURL,
            dataCachePath: PyRevitLabsConsts.CacheDirectory
            );

        private static Regex BuildNumberFinder = new Regex(@".*(?<build>\d{8}_\d{4}).*");
        private static Regex BuildTargetFinder = new Regex(@".*\((?<target>[xX]\d{2})\).*");
        private static Regex InstallPathYearFinder = new Regex(@"Revit\s+(?<product_year>\d{4})", RegexOptions.IgnoreCase);

        /// <summary>
        /// Oldest Revit product year this pyRevit line supports.
        /// </summary>
        /// <remarks>
        /// The C# loader replaced the legacy pure-Python loader, which was the
        /// only pyRevit runtime that ran on pre-2021 Revit (see
        /// <c>docs/architecture.md</c>), so <c>pyrevit-hosts.json</c> carries no
        /// record before this year. Older installs are still detected so they can
        /// be reported, but they must never be matched against a supported host
        /// record: binding pyRevit to another release's record is what makes the
        /// loader pull in assemblies built for a different Revit.
        /// </remarks>
        public const int MinimumSupportedProductYear = 2021;

        public static string ExtractBuildNumberFromString(string inputString) {
            Match match = BuildNumberFinder.Match(inputString);
            if (match.Success)
                return match.Groups["build"].Value;
            return string.Empty;
        }

        public static string ExtractBuildTargetFromString(string inputString) {
            Match match = BuildTargetFinder.Match(inputString);
            if (match.Success)
                return match.Groups["target"].Value;
            return string.Empty;
        }

        /// <summary>Whether this pyRevit line supports the given Revit product year.</summary>
        public static bool IsSupportedProductYear(int productYear) {
            return productYear >= MinimumSupportedProductYear;
        }

        /// <summary>Product year read off an install path, e.g. "C:\Program Files\Autodesk\Revit 2020\".</summary>
        /// <returns>The product year, or 0 if the path carries no "Revit &lt;year&gt;" segment.</returns>
        public static int GetProductYearFromPath(string installPath) {
            if (installPath is null)
                return 0;
            var match = InstallPathYearFinder.Match(installPath);
            if (match.Success)
                return int.Parse(match.Groups["product_year"].Value);
            return 0;
        }

        /// <summary>Product year implied by a Revit file version, e.g. "20.2.90.12" for Revit 2020.</summary>
        /// <returns>The product year, or 0 if the version string can not be parsed.</returns>
        public static int GetProductYearFromVersionString(string versionString) {
            Version version;
            if (versionString != null && Version.TryParse(versionString, out version))
                return GetProductYear(version);
            return 0;
        }

        /// <summary>Note explaining that a product year is not supported by this pyRevit line.</summary>
        /// <returns>The note to append to a product listing, or null if the year is supported.</returns>
        public static string GetUnsupportedProductNote(int productYear) {
            if (IsSupportedProductYear(productYear))
                return null;
            return string.Format("Note: Revit {0} is not supported by this version of pyRevit (requires Revit {1} or newer)",
                                 productYear, MinimumSupportedProductYear);
        }

        /// <summary>
        /// Match an identifier against the host database.
        /// </summary>
        /// <param name="identifier">Release name, file version, or a string carrying a build number.</param>
        /// <param name="installPath">Install path of the host, used to break ties on a shared build number.</param>
        /// <param name="productVersion">Full file version of the host, the strongest tie-breaker.</param>
        /// <returns>The matching record, or null when nothing matches or the match stays ambiguous.</returns>
        public static HostProductInfo GetProductInfo(string identifier,
                                                    string installPath = null,
                                                    Version productVersion = null) {
            logger.Debug("Getting host product info for: {0}", identifier);
            return FindProductInfo(GetAllProductInfo(), identifier, installPath, productVersion);
        }

        /// <summary>
        /// Match a host record against a set of product records.
        /// </summary>
        /// <param name="products">Records to match against, e.g. the host database.</param>
        /// <param name="identifier">
        /// A release name, a file version, or any string carrying a build number
        /// (e.g. the ProductVersion of Revit.exe). A build number anywhere in the
        /// identifier is the most specific identity it holds, so it takes
        /// precedence over the rest of the text.
        /// </param>
        /// <param name="installPath">
        /// Install path of the host. Used to tell apart releases that ship the
        /// same build number.
        /// </param>
        /// <param name="productVersion">
        /// Full file version of the host. The strongest tie-breaker available,
        /// since it comes from the host binary itself.
        /// </param>
        /// <returns>
        /// The matching record, or null when nothing matches or when the match
        /// stays ambiguous. Callers must read null as "not in the host database"
        /// and fall back to the binary's own version info.
        /// </returns>
        /// <remarks>
        /// <b>Important:</b> build numbers are <i>not</i> unique across releases.
        /// Revit 2020.2.9 and 2021.1.7 both ship build 20220517_1515, and 2021.1.6
        /// and 2022.1.2 both ship 20220123_1515. A build match is therefore only
        /// a candidate set, never a proof: records whose product year contradicts
        /// the host's own year are dropped, and a candidate set that survives
        /// every tie-breaker resolves to null instead of an arbitrary first match.
        /// </remarks>
        public static HostProductInfo FindProductInfo(IEnumerable<HostProductInfo> products,
                                                      string identifier,
                                                      string installPath = null,
                                                      Version productVersion = null) {
            if (products is null || string.IsNullOrEmpty(identifier))
                return null;

            // identifier can be build, version, or name (any of the properties in the data set
            // check if the string has build number e.g. "20110309_2315"
            var buildNumber = ExtractBuildNumberFromString(identifier);
            var key = (buildNumber != string.Empty ? buildNumber : identifier).ToLower();
            var matches = products.Where(prodInfo => prodInfo != null
                                                       && prodInfo.meta?.schema == "1.0"
                                                       && (prodInfo.release?.ToLower() == key
                                                           || prodInfo.version?.ToLower() == key
                                                           || prodInfo.build?.ToLower() == key))
                                  .ToList();
            if (matches.Count == 0) {
                logger.Debug("No host product matches \"{0}\"", identifier);
                return null;
            }
            var hostYear = productVersion != null ? GetProductYear(productVersion) : 0;
            if (hostYear == 0)
                hostYear = GetProductYearFromPath(installPath);
            if (hostYear != 0)
                matches = matches.Where(prodInfo => GetProductYearFromVersionString(prodInfo.version) == hostYear).ToList();

            if (matches.Count == 1)
                return matches[0];
            if (matches.Count == 0) {
                logger.Debug("Host product \"{0}\" (product year {1}) has no record matching \"{2}\"", identifier, hostYear, key);
                return null;
            }
            var namedIdentifier = identifier.ToLower();
            var named = matches.Where(prodInfo => (prodInfo.release != null && namedIdentifier.Contains(prodInfo.release.ToLower()))
                                                 || (prodInfo.version != null && namedIdentifier.Contains(prodInfo.version.ToLower())))
                               .ToList();
            if (named.Count == 1)
                return named[0];
            if (named.Count == 0 && matches.Select(prodInfo => GetProductYearFromVersionString(prodInfo.version)).Distinct().Count() == 1)
                return matches[0];

            logger.Warn("Ambiguous host product \"{0}\": \"{1}\" matches {2}. Not guessing; report this to pyRevitLabs so the host database can disambiguate it.",
                        identifier, key, string.Join(", ", matches.Select(prodInfo => prodInfo.release + " (" + prodInfo.version + ")")));
            return null;
        }

        public static List<HostProductInfo> GetAllProductInfo() => _dstore.GetAllData();

        public static string GetBinaryLocation(string installPath) {
            // make sure installPath is not null
            installPath = installPath ?? "";
            if (!CommonUtils.VerifyPath(installPath)) {
                logger.Debug("Can not verify install path: \"{0}\"", installPath);
                // starting with Revit 2021, install path might be some sort of relative e.g. "Revit 2021\"
                installPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), "Autodesk", installPath);
                logger.Debug("Using default install path: \"{0}\"", installPath);
            }

            var possibleLocations = new List<string>() {
                Path.Combine(installPath, "Revit.exe"),
                Path.Combine(installPath, "Program", "Revit.exe")
            };
            foreach (var binaryLoc in possibleLocations)
                if (File.Exists(binaryLoc))
                    return binaryLoc;
            return null;
        }

        public static int GetProductYear(string inputString) {
            if (inputString != null) {
                var productYearFinder = new Regex(@".*\s+(?<product_year>\d{4}).*");
                var match = productYearFinder.Match(inputString);
                if (match.Success) {
                    var productYear = match.Groups["product_year"].Value;
                    return int.Parse(productYear);
                }
            }
            // if product year not found, return 0
            return 0;
        }

        public static int GetProductYear(Version version) {
            if (version.Major <= 99) {
                if (version.Major <= 13)
                    return 2000 + version.Major + 1;
                else
                    return 2000 + version.Major;
            }

            return version.Major;
        }

        public static HostProductInfo GetBinaryProductInfo(string binaryPath) {
            var fileInfo = FileVersionInfo.GetVersionInfo(binaryPath);
            return new HostProductInfo {
                // attempt at creating a nice name, based on version
                release = string.Format("{0} 20{1}", fileInfo.ProductName, fileInfo.FileVersion.Substring(0, 2)),
                version = fileInfo.FileVersion,
                build = ExtractBuildNumberFromString(fileInfo.ProductVersion),
                target = ExtractBuildTargetFromString(fileInfo.ProductVersion)
            };
        }

        public static void Update() => _dstore.UpdateData(forceUpdate: true);

        public static void RefreshIfStale() => _dstore.UpdateData(forceUpdate: false);
    }

    public class RevitProduct {
        private string _registeredName = string.Empty;
        private string _registeredInstallPath = string.Empty;
        private static List<RevitProduct> _installedProductsCache = null;
        private static readonly object _installedProductsCacheLock = new object();

        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        private RevitProduct(HostProductInfo prodInfo, bool isListedInHostsDatabase = true) {
            Name = prodInfo.release;
            try {
                Version = new Version(prodInfo.version);
            }
            catch { Version = null; }
            BuildNumber = prodInfo.build;
            BuildTarget = prodInfo.target;
            IsListedInHostsDatabase = isListedInHostsDatabase;
        }

        public override string ToString() {
            var result = string.Format("{0} | Version: {1} | Build: {2}({3}) | Language: {4} | Path: \"{5}\"",
                                       Name, Version, BuildNumber, BuildTarget, LanguageCode, InstallLocation);
            if (!IsListedInHostsDatabase)
                result += " | Note: not listed in pyrevit-hosts.json";
            var unsupportedNote = RevitProductData.GetUnsupportedProductNote(ProductYear);
            if (unsupportedNote != null)
                result += " | " + unsupportedNote;
            return result;
        }

        public override int GetHashCode() {
            return BuildNumber.GetHashCode();
        }

        public string Name { get; private set; }
        public bool IsListedInHostsDatabase { get; private set; }

        /// <summary>
        /// Whether this pyRevit line can run on this product.
        /// </summary>
        /// <remarks>
        /// A product can be detected yet still be unsupported, e.g. a Revit 2020
        /// install that pyrevit-hosts.json no longer carries. Callers should
        /// report those instead of acting on them.
        /// </remarks>
        public bool IsSupported {
            get { return RevitProductData.IsSupportedProductYear(ProductYear); }
        }
        public int ProductYear {
            get {
                int prodYear = 0;
                prodYear = RevitProductData.GetProductYear(Name);
                if (prodYear == 0)
                    prodYear = RevitProductData.GetProductYear(Version);
                return prodYear;
            }
        }
        public Version Version { get; private set; }
        public string BuildNumber { get; private set; }
        public string BuildTarget { get; private set; }

        public string DefaultInstallLocation {
            get {
                return Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles);
            }
        }
        public string InstallLocation {
            get {
                if (_registeredInstallPath is null || _registeredInstallPath == string.Empty) {
                    string revitInstallDirName = string.Empty;
                    if (ProductYear != 0)
                        revitInstallDirName = string.Format("Revit {0}", ProductYear);

                    if (revitInstallDirName != string.Empty) {
                        var expectedPath = Path.Combine(DefaultInstallLocation, "Autodesk", revitInstallDirName);
                        logger.Debug("Expected path \"{0}\"", expectedPath);
                        if (CommonUtils.VerifyPath(expectedPath))
                            return expectedPath;
                        else
                            logger.Debug("Product not found at expected path \"{0}\"", expectedPath);
                    }
                }

                return _registeredInstallPath;
            }

            set {
                if (value != null)
                    _registeredInstallPath = value;
            }
        }
        public string ExecutiveLocation => RevitProductData.GetBinaryLocation(InstallLocation);
        public int LanguageCode { get; set; }

        // static:
        public static RevitProduct LookupRevitProduct(string buildOrVersionString,
                                                      string installPath = null,
                                                      Version productVersion = null) {
            var prodInfo = RevitProductData.GetProductInfo(buildOrVersionString, installPath, productVersion);
            if (prodInfo != null)
                return new RevitProduct(prodInfo);
            return null;
        }

        /// <summary>
        /// Re-resolve a product found from an identifier against the host binary's own version.
        /// </summary>
        /// <remarks>
        /// A build number on its own is not an identity: it is shared across releases, and the
        /// catalog may hold only one side of such a pair. When the identifier is nothing but a
        /// build number, the executable's file version is the only remaining evidence of which
        /// release this install is, so it gets to confirm or overturn the match. A lookup that
        /// names a release or a version is already specific and is left alone.
        /// </remarks>
        /// <param name="matched">The record the identifier resolved to.</param>
        /// <param name="identifier">The identifier the record was resolved from.</param>
        /// <param name="binaryFilePath">Path of the host binary.</param>
        /// <param name="pathHint">Install path used for the first lookup.</param>
        /// <returns>
        /// The confirmed record, the original when the binary agrees or cannot be read, or null when
        /// the binary contradicts the match.
        /// </returns>
        private static RevitProduct ConfirmAgainstBinary(RevitProduct matched, string identifier, string binaryFilePath, string pathHint) {
            if (RevitProductData.ExtractBuildNumberFromString(identifier) == string.Empty)
                return matched;

            Version binaryVersion;
            try {
                var binaryInfo = RevitProductData.GetBinaryProductInfo(binaryFilePath);
                if (!Version.TryParse(binaryInfo.version, out binaryVersion))
                    return matched;
                if (RevitProductData.GetProductYear(binaryVersion) == matched.ProductYear)
                    return matched;
            }
            catch (Exception readEx) {
                logger.Debug("Could not read the host binary at \"{0}\": {1}", binaryFilePath, readEx.Message);
                return matched;
            }

            var confirmed = LookupRevitProduct(identifier, pathHint, binaryVersion);
            if (confirmed != null)
                return confirmed;

            logger.Warn(
                "Revit build \"{0}\" resolves to \"{1}\" in the host database, but the binary at \"{2}\" reports a "
                    + "different product year. Not trusting either; report this to pyRevitLabs so the host database "
                    + "can be corrected.",
                identifier, matched.Name, binaryFilePath);
            return null;
        }

        public static RevitProduct LookupRevitProduct(Version version) {
            return LookupRevitProduct(version.ToString());
        }

        /// <summary>
        /// Resolve the Revit product an identifier or binary belongs to.
        /// </summary>
        /// <param name="identifier">
        /// Release name, file version, or a string carrying a build number, e.g.
        /// the registry DisplayVersion or the ProductVersion of Revit.exe.
        /// </param>
        /// <param name="binaryFilePath">
        /// Path of the host binary. When the identifier is not in the host
        /// database, the binary's own version info is used instead.
        /// </param>
        /// <param name="installPath">
        /// Install path of the host, when known separately from
        /// <paramref name="binaryFilePath"/>. Both are usable as a product-year
        /// identity, which is what keeps a build number shared by two releases
        /// from resolving to the wrong host record.
        /// </param>
        /// <returns>
        /// The resolved product, or null when nothing could be determined. A
        /// product that is not in the host database is returned rather than
        /// null, flagged with <see cref="IsListedInHostsDatabase"/> false.
        /// </returns>
        public static RevitProduct ResolveProduct(string identifier, string binaryFilePath = null, string installPath = null) {
            logger.Debug("Looking up Revit Product in database...");
            var pathHint = installPath ?? binaryFilePath;
            var revitProduct = LookupRevitProduct(identifier, pathHint);
            if (revitProduct != null && binaryFilePath != null)
                revitProduct = ConfirmAgainstBinary(revitProduct, identifier, binaryFilePath, pathHint);
            if (revitProduct != null) {
                if (!revitProduct.IsSupported)
                    logger.Warn("Host database record \"{0}\" (product year {1}) is below the minimum supported Revit year ({2}). " +
                                "Use a pyRevit release that supports Revit {1} to run pyRevit here.",
                                revitProduct.Name, revitProduct.ProductYear, RevitProductData.MinimumSupportedProductYear);
                return revitProduct;
            }

            logger.Debug("Could not determine Revit Product from version \"{0}\" in pyrevit-hosts.json", identifier);
            if (binaryFilePath == null) {
                logger.Debug("Revit version \"{0}\" not found in pyrevit-hosts.json and no binary path available to read version info", identifier);
                return null;
            }

            try {
                var prodInfo = RevitProductData.GetBinaryProductInfo(binaryFilePath);
                logger.Debug("Read build number \"{0}\" from binary at \"{1}\"", prodInfo.build, binaryFilePath);
                Version binaryVersion;
                Version.TryParse(prodInfo.version, out binaryVersion);
                revitProduct = LookupRevitProduct(prodInfo.build, pathHint, binaryVersion);
                if (revitProduct is null) {
                    var binaryYear = RevitProductData.GetProductYearFromVersionString(prodInfo.version);
                    if (RevitProductData.IsSupportedProductYear(binaryYear))
                        logger.Info("Version \"{0}\" (build: {1}) not found in pyrevit-hosts.json. Using product information from binary file. " +
                                    "Consider updating pyrevit-hosts.json if this version should be officially supported.",
                                    identifier, prodInfo.build);
                    else
                        logger.Warn("Version \"{0}\" (build: {1}, product year {2}) is not supported by this version of pyRevit, " +
                                    "which requires Revit {3} or newer. Use a pyRevit release that supports Revit {2} to run pyRevit here.",
                                    identifier, prodInfo.build, binaryYear, RevitProductData.MinimumSupportedProductYear);
                    revitProduct = new RevitProduct(prodInfo, isListedInHostsDatabase: false);
                }
                return revitProduct;
            }
            catch (Exception ex) {
                logger.Debug(ex, "Revit version \"{0}\" not found in pyrevit-hosts.json and failed to read product info from binary at \"{1}\"",
                             identifier, binaryFilePath);
            }
            return null;
        }

        public static List<RevitProduct> ListInstalledProducts() {
            if (_installedProductsCache != null)
                return _installedProductsCache.ToList();

            lock (_installedProductsCacheLock) {
                if (_installedProductsCache != null)
                    return _installedProductsCache.ToList();

                var installedRevits = new HashSet<RevitProduct>();

                // pattern for finding revit installation entries in registry
                // matching:
                //     Revit 2019
                //     Revit 2019 - German
                //     Revit Architecture 2016 - Imperial
                // fails:
                //     Revit Content Libraries 2016
                var revitFinder = new Regex(@"^Revit\s[A-Za-z]*\s*\d{4}\s?($|\s-)");
                // also match Revit Preview Release (e.g. 2027 preview) and "Autodesk Revit Preview Release"
                var previewFinder = new Regex(@"^(Autodesk\s+)?Revit\s+Preview\s+Release\s*$", RegexOptions.IgnoreCase);

                // open parent regkey
                var uninstallKey =
                    Registry.LocalMachine.OpenSubKey(@"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall");
                // loop thru subkeys and find matching
                var registeredAppKeys = uninstallKey.GetSubKeyNames();
                foreach (var key in registeredAppKeys) {
                    var subkey = uninstallKey.OpenSubKey(key);
                    var appName = subkey.GetValue("DisplayName") as string;
                    if (appName != null && (revitFinder.IsMatch(appName) || previewFinder.IsMatch(appName))) {
                        logger.Debug("App is a Revit product: {0}", appName);
                        try {
                            // collect info from reg key
                            var regName = subkey.GetValue("DisplayName") as string;
                            var regVersion = subkey.GetValue("DisplayVersion") as string;
                            var regInstallPath = subkey.GetValue("InstallLocation") as string;
                            if (regInstallPath == null) {
                                // Entries without an install location are typically add-ins; skip them.
                                continue;
                            }
                            var languageValue = subkey.GetValue("Language");
                            int regLangCode;
                            if (languageValue is int langCode) {
                                regLangCode = langCode;
                            }
                            else {
                                // Missing or invalid language code; skip this entry to avoid runtime casting errors.
                                logger.Debug("Skipping registered app \"{0}\" because registry key \"Language\" is missing or invalid.", appName);
                                continue;
                            }
                            // try to find binary location
                            var binaryFilePath = RevitProductData.GetBinaryLocation(regInstallPath)?.NormalizeAsPath();
                            logger.Debug("Version from registry key: \"{0}\"", regVersion);
                            logger.Debug("Install path from registry key: \"{0}\"", regInstallPath);
                            logger.Debug("Binary path from registry key: \"{0}\"", binaryFilePath ?? "");
                            logger.Debug("Language code from registry key: \"{0}\"", regLangCode);

                            var revitProduct = FindRevitProduct(regVersion, binaryFilePath, regInstallPath);
                            if (revitProduct is null) {
                                logger.Debug("Could not determine Revit product for \"{0}\" (version: {1}). This installation will be excluded from the list. " +
                                           "This may occur if the version is not listed in pyrevit-hosts.json or if product information could not be read from the binary file.",
                                           regName, regVersion);
                                continue;
                            }
                            logger.Debug("Revit Product is : {0}", revitProduct);
                            // grab the registry name if it doesn't have a name
                            if (revitProduct.Name is null || revitProduct.Name == string.Empty)
                                revitProduct.Name = regName;

                            // build from a registry version if it doesn't already have one
                            if (revitProduct.Version is null && (regVersion != null && regVersion != string.Empty)) {
                                try {
                                    revitProduct.Version = new Version(regVersion);
                                }
                                catch { }
                            }

                            // update install path from registry if it can't find one
                            if (regInstallPath != null && regInstallPath != string.Empty) {
                                if (CommonUtils.VerifyFile(binaryFilePath))
                                    revitProduct.InstallLocation = regInstallPath;
                            }

                            // this can only come from registrys
                            revitProduct.LanguageCode = regLangCode;

                            // add to list now, only if install location is verified
                            string pLocation = revitProduct.InstallLocation;
                            if (pLocation != null && pLocation != string.Empty)
                                installedRevits.Add(revitProduct);
                        }
                        catch (Exception rpEx) {
                            var innerMessage = rpEx.InnerException is null ? "" : $" | {rpEx.InnerException.Message}";
                            logger.Error("Error determining installed Revit Product from: {0} | {1}{2}",
                                         appName, rpEx.Message, innerMessage);
                        }
                    }
                }

                logger.Debug("Scanned {0} registered apps; found {1} installed Revit products",
                             registeredAppKeys.Length, installedRevits.Count);

                _installedProductsCache = installedRevits.ToList();
                return _installedProductsCache.ToList();
            }
        }

        private static RevitProduct FindRevitProduct(string regVersion, string binaryFilePath, string installPath) {
            return ResolveProduct(regVersion, binaryFilePath, installPath);
        }

        public static List<RevitProduct> ListSupportedProducts() {
            var installedRevits = new HashSet<RevitProduct>();
            foreach (var regProduct in RevitProductData.GetAllProductInfo())
                installedRevits.Add(new RevitProduct(regProduct));
            return installedRevits.ToList();
        }
    }
}
