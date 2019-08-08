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
    public class RevitProduct {
        private string _registeredInstallPath = null;

        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        // keep this updated from:
        // https://knowledge.autodesk.com/support/revit-products/learn-explore/caas/sfdcarticles/sfdcarticles/How-to-tie-the-Build-number-with-the-Revit-update.html
        private static Dictionary<string, (string, string)> _revitBuildNumberLookupTable = new Dictionary<string, (string, string)>() {

            // 2008
            // https://www.revitforum.org/architecture-general-revit-questions/105-revit-builds-updates-product-support.html
            {"20070607_1700", ("0.0.0.0",       "2008 Architecture Service Pack 2")},
            {"20070810_1700", ("0.0.0.0",       "2008 Architecture Service Pack 2")},
            {"20080101_2345", ("0.0.0.0",       "2008 Architecture Service Pack 3")},  // https://forums.autodesk.com/t5/revit-architecture-forum/sp3-build-20080101-2345/td-p/2152807

            // 2009
            // https://www.revitforum.org/architecture-general-revit-questions/105-revit-builds-updates-product-support.html
            {"20080602_1900", ("0.0.0.0",       "2009 Architecture Service Pack 1")},
            {"20080915_2100", ("0.0.0.0",       "2009 Architecture Service Pack 2")},
            {"20081118_1045", ("0.0.0.0",       "2009 Architecture Service Pack 3")},

            // 2010
            // https://www.revitforum.org/architecture-general-revit-questions/105-revit-builds-updates-product-support.html
            {"20090612_2115", ("0.0.0.0",       "2010 Architecture Service Pack 1")},  // https://forums.autodesk.com/t5/revit-architecture-forum/sp3-build-20080101-2345/td-p/2152807
            {"20090917_1515", ("0.0.0.0",       "2010 Architecture Service Pack 2")},

            // 2011
            {"20100326_1700", ("0.0.0.0",       "2011 Architecture")}, // http://forums.augi.com/showthread.php?138574-Revit-Architecture-Door-Centerline-not-selectable-during-dimensioning
            {"20100615_2115", ("0.0.0.0",       "2011 Architecture Service Pack 1")},   // http://revitclinic.typepad.com/my_weblog/2010/06/revit-2011-build-number-update-display.html
            {"20100903_2115", ("0.0.0.0",       "2011 Architecture Service Pack 2")},   // http://revitoped.blogspot.com/2010/09/revit-web-update-2-posted-subscription.html

            // 2012
            // http://web.archive.org/web/20150123061214/https://knowledge.autodesk.com/support/revit-products/troubleshooting/caas/sfdcarticles/sfdcarticles/How-to-tie-the-Build-number-with-the-Revit-update.html
            {"20110309_2315", ("0.0.0.0",       "2012 First Customer Ship")},
            {"20110622_0930", ("0.0.0.0",       "2012 Update Release 1")},
            {"20110916_2132", ("0.0.0.0",       "2012 Update Release 2")},

            // 2013
            // http://web.archive.org/web/20150123061214/https://knowledge.autodesk.com/support/revit-products/troubleshooting/caas/sfdcarticles/sfdcarticles/How-to-tie-the-Build-number-with-the-Revit-update.html
            {"20120221_2030", ("12.02.21203",   "2013 First Customer Ship")},
            {"20120716_1115", ("0.0.0.0",       "2013 Update Release 1")},
            {"20121003_2115", ("0.0.0.0",       "2013 Update Release 2")},
            {"20130531_2115", ("12.11.10090",   "2013 Update Release 3")},  // https://github.com/eirannejad/pyRevit/issues/622
            {"20120821_1330", ("0.0.0.0",       "2013 LT First Customer Ship")},
            {"20130531_0300", ("0.0.0.0",       "2013 LT Update Release 1")},

            // 2014
            // tested on local machine
            {"20130308_1515", ("13.03.08151",   "2014 First Customer Ship")},
            {"20130709_2115", ("0.0.0.0",       "2014 Update Release 1")},
            {"20131024_2115", ("0.0.0.0",       "2014 Update Release 2")},
            {"20140709_2115", ("13.11.00004",   "2014 Update Release 3")},  //https://github.com/eirannejad/pyRevit/issues/543

            // 2015
            // https://knowledge.autodesk.com/support/revit-products/downloads/caas/downloads/content/autodesk-revit-2015-product-updates.html
            {"20140223_1515", ("15.0.136.0",    "2015 First Customer Ship")},
            {"20140322_1515", ("15.0.136.0",    "2015 Update Release 1")},
            {"20140323_1530", ("15.0.166.0",    "2015 Update Release 2")},
            {"20140606_1530", ("15.0.207.0",    "2015 Update Release 3")},
            {"20140903_1530", ("15.0.270.0",    "2015 Update Release 4")},
            {"20140905_0730", ("15.0.1103.0",   "2015 Release 2 (Subscription only release)")},
            {"20141119_1515", ("15.0.310.0",    "2015 Update Release 5")},
            {"20141119_0715", ("15.0.1133.0",   "2015 Release 2 Update Release 5 (Subscription only release)")},
            {"20150127_1515", ("15.0.315.0",    "2015 Update Release 6")},
            {"20150127_0715", ("15.0.1142.0",   "2015 Release 2 Update Release 6 (Subscription only release)")},
            {"20150303_1515", ("15.0.318.0",    "2015 Update Release 7")},
            {"20150303_0715", ("15.0.1148.0",   "2015 Release 2 Update Release 7 (Subscription only release)")},
            {"20150512_1015", ("15.0.341.0",    "2015 Update Release 8")},
            {"20150511_0715", ("15.0.1170.0",   "2015 Release 2 Update Release 8 (Subscription only release)")},
            {"20150702_1515", ("15.0.361.0",    "2015 Update Release 9")},
            {"20150704_0715", ("15.0.1190.0",   "2015 Release 2 Update Release 9 (Subscription only release)")},
            {"20151007_1515", ("15.0.379.0",    "2015 Update Release 10")},
            {"20151008_0715", ("15.0.1203.0",   "2015 Release 2 Update Release 10 (Subscription only release)")},
            {"20151207_1515", ("15.0.390.0",    "2015 Update Release 11 *Issue with Revit Server")},
            {"20151208_0715", ("15.0.1225.0",   "2015 Release 2 Update Release 11 (Subscription only release) *Issue with Revit Server")},
            {"20160119_1515", ("15.0.403.0",    "2015 Update Release 12")},
            {"20160120_0715", ("15.0.1238.0",   "2015 Release 2 Update Release 12 (Subscription only release)")},
            {"20160220_1515", ("15.0.406.0",    "2015 Update Release 13")},
            {"20160220_0715", ("15.0.1243.0",   "2015 Release 2 Update Release 13 (Subscription only release)")},
            {"20160512_1515", ("15.0.421.0",    "2015 Update Release 14")},
            {"20160512_0715", ("15.0.1259.0",   "2015 Release 2 Update Release 14  (Subscription only release)")},

            // 2016
            {"20150220_1215", ("16.0.428.0",    "2016 First Customer Ship")},
            {"20150506_1715", ("16.0.462.0",    "2016 Service Pack 1")},
            {"20150701_1515", ("16.0.485.0",    "2016 Unreleased Update")},    // https://knowledge.autodesk.com/support/revit-products/troubleshooting/caas/sfdcarticles/sfdcarticles/Revit-2016-Release-2-Error-1642.html
            {"20150714_1515", ("16.0.490.0",    "2016 Service Pack 2")},
            {"20151007_0715", ("16.0.1063",     "2016 Release 2 (R2)")},
            {"20151209_0715", ("16.0.1092.0",   "2016 Update 1 for R2")},
            {"20160126_1600", ("16.0.1108.0",   "2016 Update 2 for R2")},
            {"20160217_1800", ("16.0.1118.0",   "2016 Update 3 for R2")},
            {"20160314_0715", ("16.0.1124.0",   "2016 Update 4 for R2")},
            {"20160525_1230", ("16.0.1144.0",   "2016 Update 5 for R2")},
            {"20160720_0715", ("16.0.1161.0",   "2016 Update 6 for R2")},
            {"20161004_0715", ("16.0.1185.0",   "2016 Update 7 for R2")},
            {"20170117_1200", ("16.0.1205.0",   "2016 Update 8 for R2 (2016.1.8)")},

            // 2017
            {"20160225_1515", ("17.0.416.0",    "2017 First Customer Ship")},
            {"20160606_1515", ("17.0.476.0",    "2017 Service Pack 1")},
            {"20160720_1515", ("17.0.501.0",    "2017 Service Pack 2")},
            {"20161205_1400", ("17.0.503.0",    "2017.0.3")},
            {"20161006_0315", ("17.0.1081.0",   "2017.1")},
            {"20161117_1200", ("17.0.1099.0",   "2017.1.1")},
            {"20170118_1100", ("17.0.1117.0",   "2017.2")},
            {"20170419_0315", ("17.0.1128.0",   "2017.2.1")},
            {"20170816_0615", ("17.0.1146.0",   "2017.2.2")},
            {"20171027_0315", ("17.0.1150.0",   "2017.2.3")},
            {"20181011_1545", ("17.0.511.0",    "2017.0.4")}, // https://github.com/eirannejad/pyRevit/issues/456
            {"20190507_1515", ("17.0.517.0",    "2017.0.5 Security Fix")},
            {"20181011_1645", ("17.0.1158.0",   "2017.2.4")},
            {"20190508_0315", ("17.0.1169.0",   "2017.2.5 Security Fix")},

            // 2018
            {"20170223_1515", ("18.0.0.420",    "2018 First Customer Ship")},
            {"20170421_2315", ("18.0.1.2",      "2018.0.1")},
            {"20170525_2315", ("18.0.2.11",     "2018.0.2")},
            {"20181015_0930", ("18.0.3.6",      "2018.0.3")},
            {"20170630_0700", ("18.1.0.92",     "2018.1")},
            {"20170907_2315", ("18.1.1.18",     "2018.1.1")},
            {"20170927_1515", ("18.2.0.51",     "2018.2")},
            {"20180329_1100", ("18.3.0.81",     "2018.3")}, // https://github.com/eirannejad/pyRevit/issues/456
            {"20180423_1000", ("18.3.1.2",      "2018.3.1")},
            {"20181011_1500", ("18.3.2.7",      "2018.3.2")},
            {"20190510_1515", ("18.3.3.18",     "2018.3.3 Security Fix")},

            // 2019
            {"20180216_1515", ("19.0.0.405",    "2019 First Customer Ship")},
            {"20180328_1600", ("19.0.1.1",      "2019 Update for Trial Build")},
            //{"20180328_1800", ("19.0.1.1",	"2019 Update for Trial Build")}, // listed incorrectly with _1800 on https://knowledge.autodesk.com/support/revit-products/learn-explore/caas/sfdcarticles/sfdcarticles/How-to-tie-the-Build-number-with-the-Revit-update.html
            {"20180518_1600", ("19.0.10.18",    "2019.0.1")},
            {"20180927_2315", ("19.0.20.1",     "2019.0.2")},
            {"20180806_1515", ("19.1.0.112",    "2019.1")},
            {"20181217_1515", ("19.2.0.65",     "2019.2 (Update)")},
            {"20190108_1515", ("19.2.1.1",      "2019.2 (Full Install)")}, // reported by: https://twitter.com/JarodJSchultz/status/1100459171491676160
            {"20190225_1515", ("19.2.10.7",     "2019.2.1")}, // release notes https://up.autodesk.com/2019/RVT/Autodesk_Revit_2019_2_1_Readme.html

            // 2020
            {"20190327_2315", ("20.0.0.377",    "2020 First Customer Ship")},
            {"20190412_1200", ("20.0.1.2",      "2020.0.1")},
        };

        private static Regex BuildNumberFinder = new Regex(@".*(?<build>\d{8}_\d{4}).*");

        private RevitProduct(string buildNumber) {
            BuildNumber = buildNumber;
        }

        public override string ToString() {
            return string.Format("{0} | Version: {1} | Build: {2}({3}) | Language: {4} | Path: \"{5}\"", ProductName, Version, BuildNumber, BuildTarget, LanguageCode, InstallLocation);
        }

        public override int GetHashCode() {
            return BuildNumber.GetHashCode();
        }

        public string BuildNumber { get; private set; }

        public string BuildTarget { get; private set; } = "x64";

        public Version Version {
            get {
                // build version from build-number lookup
                if (_revitBuildNumberLookupTable.ContainsKey(BuildNumber)) {
                    try {
                        return new Version(_revitBuildNumberLookupTable[BuildNumber].Item1);
                    }
                    catch {
                    }
                }

                // otherwise build version from registry info if available
                if (RegisteredVersion != null || RegisteredVersion != string.Empty) {
                    try {
                        return new Version(RegisteredVersion);
                    }
                    catch {
                    }
                }

                // return none
                return null;
            }
        }

        private Version FullVersion {
            get {
                if (Version != null) {
                    if (Version.Revision >= 0)
                        return new Version(2000 + Version.Major, Version.Minor, Version.Build, Version.Revision);
                    else if (Version.Build >= 0)
                        return new Version(2000 + Version.Major, Version.Minor, Version.Build);
                    else
                        return new Version(2000 + Version.Major, Version.Minor);
                }

                else
                    return null;
            }
        }

        public int ProductYear {
            get {
                if (FullVersion != null) {
                    var productYearFinder = new Regex(@".*\s(?<product_year>\d{4}).*");
                    var match = productYearFinder.Match(this.ProductName);
                    if (match.Success) {
                        var productYear = match.Groups["product_year"].Value;
                        return int.Parse(productYear);
                    }
                }

                // if product year not found, return 0
                return 0;
            }
        }

        public string ProductName {
            get {
                if (_revitBuildNumberLookupTable.ContainsKey(BuildNumber))
                    return string.Format("Autodesk Revit {0}", _revitBuildNumberLookupTable[BuildNumber].Item2);
                else if (RegisteredName != null || RegisteredName != string.Empty)
                    return RegisteredName;
                else
                    return "";
            }
        }

        public string DefaultInstallLocation {
            get {
                return Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles);
            }
        }

        private string RegisteredName { get; set; }

        private string RegisteredVersion { get; set; }

        public string InstallLocation {
            get {
                if (_registeredInstallPath == null) {
                    string revitInstallDirName = null;
                    if (FullVersion != null)
                        revitInstallDirName = string.Format("Revit {0}", FullVersion.Major);
                    else if (Version != null)
                        revitInstallDirName = string.Format("Revit {0}", 2000 + Version.Major);
                    var expectedPath = Path.Combine(DefaultInstallLocation, "Autodesk", revitInstallDirName);
                    logger.Debug("Expected path {0}", expectedPath);
                    if (CommonUtils.VerifyPath(expectedPath))
                        return expectedPath;
                }

                return _registeredInstallPath;
            }

            set {
                _registeredInstallPath = value;
            }
        }

        public string ExecutiveLocation => GetBinaryLocation(InstallLocation);

        public int LanguageCode { get; set; }

        // static:
        public static string GetBinaryLocation(string installPath) {
            var possibleLocations = new List<string>() {
                Path.Combine(installPath, "Revit.exe"),
                Path.Combine(installPath, "Program", "Revit.exe")
            };
            foreach (var binaryLoc in possibleLocations)
                if (File.Exists(binaryLoc))
                    return binaryLoc;
            return null;
        }

        public static string GetBinaryBuildNumber(string binaryPath) {
            var fileInfo = FileVersionInfo.GetVersionInfo(binaryPath);
            return fileInfo.ProductVersion;
        }

        public static RevitProduct LookupRevitProduct(string buildOrVersionString) {
            // check if the string has build number e.g. "20110309_2315"
            Match match = BuildNumberFinder.Match(buildOrVersionString);
            if (match.Success) {
                return new RevitProduct(match.Groups["build"].Value);
            }

            // check if the string is version e.g. "18.0.0.0"
            foreach (string buildNumber in _revitBuildNumberLookupTable.Keys) {
                if (buildOrVersionString == _revitBuildNumberLookupTable[buildNumber].Item1) {
                    return new RevitProduct(buildNumber);
                }
            }

            return null;
        }

        public static RevitProduct LookupRevitProduct(Version version) {
            return LookupRevitProduct(version.ToString());
        }

        public static List<RevitProduct> ListInstalledProducts() {
            var installedRevits = new HashSet<RevitProduct>();

            // pattern for finding revit installation entries in registry
            // matching:
            //     Revit 2019
            //     Revit 2019 - German
            //     Revit Architecture 2016 - Imperial
            // fails:
            //     Revit Content Libraries 2016
            var revitFinder = new Regex(@"^Revit\s[A-Za-z]*\s*\d{4}\s?($|\s-)");

            // open parent regkey
            var uninstallKey =
                Registry.LocalMachine.OpenSubKey(@"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall");
            // loop thru subkeys and find matching
            foreach (var key in uninstallKey.GetSubKeyNames()) {
                var subkey = uninstallKey.OpenSubKey(key);
                var appName = subkey.GetValue("DisplayName") as string;
                logger.Debug("Analysing registered app: {0}", appName);
                if (appName != null && revitFinder.IsMatch(appName)) {
                    logger.Debug("App is a Revit product: {0}", appName);
                    try {
                        // collect info from reg key
                        var regName = subkey.GetValue("DisplayName") as string;
                        var regVersion = subkey.GetValue("DisplayVersion") as string;
                        var regPath = (subkey.GetValue("InstallLocation") as string).NormalizeAsPath();
                        int regLangCode = (int)subkey.GetValue("Language");
                        logger.Debug("Read version from registery key: \"{0}\"", regVersion);
                        logger.Debug("Read install path from registery key: \"{0}\"", regPath);
                        logger.Debug("Read language code from registery key: \"{0}\"", regLangCode);

                        // attempt at finding revit product
                        RevitProduct revitProduct = null;
                        revitProduct = LookupRevitProduct(regVersion);
                        // if could not determine product by version
                        if (revitProduct == null) {
                            logger.Debug("Could not determine Revit Product from version \"{0}\"", regVersion);
                            // try to get product key from binary
                            var binaryLocation = GetBinaryLocation(regPath);
                            if (binaryLocation != null) {
                                var buildNumber = GetBinaryBuildNumber(binaryLocation);
                                logger.Debug("Read build number \"{0}\" from binary at \"{1}\"", buildNumber, binaryLocation);
                                revitProduct = LookupRevitProduct(buildNumber);
                            }
                        }

                        logger.Debug("Revit Product is : {0}", revitProduct);
                        if (revitProduct != null) {
                            revitProduct.RegisteredName = regName;
                            revitProduct.RegisteredVersion = regVersion;
                            revitProduct.InstallLocation = regPath;
                            revitProduct.LanguageCode = regLangCode;
                            installedRevits.Add(revitProduct);
                        }
                        else {
                            logger.Debug("Can not determine Revit product.");
                        }
                    }
                    catch (Exception rpEx) {
                        logger.Error("Error determining installed Revit Product from: {0} | {1} | {2}",
                                     appName, rpEx.Message, rpEx.InnerException.Message);
                    }
                }
            }

            return installedRevits.ToList();
        }

        public static List<RevitProduct> ListSupportedProducts() {
            var installedRevits = new HashSet<RevitProduct>();
            foreach (var regProduct in _revitBuildNumberLookupTable)
                installedRevits.Add(LookupRevitProduct(regProduct.Key));
            return installedRevits.ToList();
        }
    }
}