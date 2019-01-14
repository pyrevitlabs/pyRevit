using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Text.RegularExpressions;
using Microsoft.Win32;

using pyRevitLabs.Common;
using pyRevitLabs.Common.Extensions;

using NLog;
using System.Xml;

namespace pyRevitLabs.TargetApps.Revit {
    // EXCEPTIONS ====================================================================================================

    // DATA TYPES ====================================================================================================
    public enum RevitModelFileOpenWorksetConfig {
        All = 0,
        Unknown = 1,
        Editable = 2,
        LastViewed = 3,
        Specify = 4
    }


    public class RevitModelFile {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        private static Regex IsWorksharedFinder = new Regex(@".*Worksharing: (?<workshared>.+?)( U|$)");
        private static Regex LastSavedPathFinder = new Regex(@".*Last Save Path: (?<path>.+?)( O|$)");
        private static Regex CentralPathFinder = new Regex(@".*Central Model Path: (?<path>.+?)( R|$)");
        private static Regex OpenWorksetFinder = new Regex(@".*Open Workset Default: (?<type>\d+)( P|$)");
        private static Regex DocumentIncrementFinder = new Regex(@".*Unique Document Increments: (?<type>\d+)( M|$)");


        public RevitModelFile(string filePath) {
            FilePath = filePath.NormalizeAsPath();

            // extract basic info and prepare string
            // throws exception if stream doesn't exist
            var rawBasicInfoData = CommonUtils.GetStructuredStorageStream(FilePath,		"BasicFileInfo");
            if (rawBasicInfoData != null)
                ProcessBasicFileInfo(Encoding.Unicode.GetString(rawBasicInfoData));
            else
                throw new pyRevitException(string.Format("Target is not a valid Revit model \"{0}\"", filePath));

            // extract partatom (Revit Family Files) and prepare string
            // throws exception if stream doesn't exist
            var rawPartAtomData = CommonUtils.GetStructuredStorageStream(FilePath,		"PartAtom");
            if (rawPartAtomData != null) {
                IsFamily = true;
                ProcessPartAtom(Encoding.ASCII.GetString(rawPartAtomData));
            }
        }

        public static bool IsRevitFile(string filePath) {
            try {
                var model = new RevitModelFile(filePath);
                return true;
            }
            catch { return false; }
        }

        private void ProcessBasicFileInfo(string rawBasicInfo) {
            bool workSharedFound = false;
            bool lastPathFound = false;
            bool centralPathFound = false;
            bool openWorksetFound = false;
            bool documentIncrementFound = false;
            bool guidFound = false;
            foreach (string line in rawBasicInfo.Split(new string[] { "\0",		"\r\n" },
                                                    StringSplitOptions.RemoveEmptyEntries)) {
                // find build number
                logger.Debug("Parsing info from BasicFileInfo: \"{0}\"", line);
                var revitProduct = RevitProduct.LookupRevitProduct(line);
                if (revitProduct != null)
                    RevitProduct = revitProduct;

                // find workshared
                if (!workSharedFound) {
                    var match = IsWorksharedFinder.Match(line);
                    if (match.Success) {
                        var workshared = match.Groups["workshared"].Value;
                        logger.Debug("IsWorkshared: {0}", workshared);
                        if (!workshared.Contains("Not"))
                            IsWorkshared = true;
                        workSharedFound = true;
                    }
                }

                // find last saved path
                if (!lastPathFound) {
                    var match = LastSavedPathFinder.Match(line);
                    if (match.Success) {
                        var path = match.Groups["path"].Value;
                        logger.Debug("Last Saved Path: {0}", path);
                        LastSavedPath = path;
                        lastPathFound = true;
                    }
                }

                // find central model path
                if (!centralPathFound) {
                    var match = CentralPathFinder.Match(line);
                    if (match.Success) {
                        var path = match.Groups["path"].Value;
                        logger.Debug("Central Model Path: {0}", path);
                        CentralModelPath = path;
                        centralPathFound = true;
                    }
                }

                // find central model path
                if (!openWorksetFound) {
                    var match = OpenWorksetFinder.Match(line);
                    if (match.Success) {
                        var owconfig = match.Groups["type"].Value;
                        logger.Debug("Open Workset Default: {0}", owconfig);
                        OpenWorksetConfig = (RevitModelFileOpenWorksetConfig)Enum.ToObject(typeof(RevitModelFileOpenWorksetConfig), int.Parse(owconfig));
                        openWorksetFound = true;
                    }
                }

                // find central model path
                if (!documentIncrementFound) {
                    var match = DocumentIncrementFinder.Match(line);
                    if (match.Success) {
                        var docincrement = match.Groups["type"].Value;
                        logger.Debug("Unique Document Increments: {0}", docincrement);
                        DocumentIncrement = int.Parse(docincrement);
                        documentIncrementFound = true;
                    }
                }

                // find document guid
                if (!guidFound && line.Contains("Unique Document GUID: ")) {
                    var guid = line.ExtractGuid();
                    logger.Debug("Extracted GUID: {0}", guid);
                    UniqueId = guid;
                    guidFound = true;
                }
            }
        }

        private void ProcessPartAtom(string rawPartAtom) {
            logger.Debug("Parsing PartAtom Data:\n{0}", rawPartAtom);
            var doc = new XmlDocument();
            try {
                doc.LoadXml(rawPartAtom);
                XmlNamespaceManager nsmgr = new XmlNamespaceManager(doc.NameTable);
                nsmgr.AddNamespace("rfa", @"http://www.w3.org/2005/Atom");
                nsmgr.AddNamespace("A", @"urn:schemas-autodesk-com:partatom");

                // extract family category
                var catElements = doc.SelectNodes("//rfa:entry/rfa:category/rfa:term", nsmgr);
                CategoryName = catElements.Count > 0 ? catElements[catElements.Count - 1].InnerText : "";

                // extract host
                var hostElement = doc.SelectSingleNode("//rfa:entry/A:features/A:feature/A:group/rfa:Host", nsmgr);
                HostCategoryName = hostElement != null ? hostElement.InnerText : "";
            }
            catch (Exception ex) {
                logger.Debug("Error parsing PartAtom XML. | {0}", ex.Message);
            }
        }

        public string FilePath { get; private set; }

        public bool IsFamily { get; private set; }

        public bool IsWorkshared { get; private set; } = false;

        public string LastSavedPath { get; private set; } = null;

        public string CentralModelPath { get; private set; } = null;

        public RevitModelFileOpenWorksetConfig OpenWorksetConfig { get; private set; } = 0;

        public int DocumentIncrement { get; private set; } = 0;

        public Guid UniqueId { get; private set; } = new Guid();

        public RevitProduct RevitProduct { get; private set; } = null;

        public string CategoryName { get; private set; }

        public string HostCategoryName { get; private set; }
    }


    public class RevitProcess {
        private Process _process;

        public RevitProcess(Process runningRevitProcess) {
            _process = runningRevitProcess;
        }

        public static bool IsRevitProcess(Process runningProcess) {
            if (runningProcess.ProcessName.ToLower() == "revit")
                return true;
            return false;
        }

        public int ProcessId {
            get {
                return _process.Id;
            }
        }

        public string Module {
            get {
                return _process.MainModule.FileName;
            }
        }

        public RevitProduct RevitProduct {
            get {
                var fileInfo = FileVersionInfo.GetVersionInfo(Module);
                return RevitProduct.LookupRevitProduct(fileInfo.ProductVersion);
            }
        }

        public override string ToString() {
            return string.Format("PID: {0} | {1}", _process.Id, RevitProduct.ToString());
        }

        public void Kill() {
            _process.Kill();
        }
    }


    public class RevitProduct {
        private string _registeredInstallPath = null;

        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        // keep this updated from:
        // https://knowledge.autodesk.com/support/revit-products/learn-explore/caas/sfdcarticles/sfdcarticles/How-to-tie-the-Build-number-with-the-Revit-update.html
        private static Dictionary<string, (string, string)> _revitBuildNumberLookupTable = new Dictionary<string, (string, string)>() {

            // 2008
            {"20080101_2345", ("08.0.0",        "2008 Architecture Service Pack 3")},  // https://forums.autodesk.com/t5/revit-architecture-forum/sp3-build-20080101-2345/td-p/2152807

            // 2009
            // 2010
            
            // 2011
            {"20100326_1700", ("10.0.0",		"2011 Architecture")}, // http://forums.augi.com/showthread.php?138574-Revit-Architecture-Door-Centerline-not-selectable-during-dimensioning
            {"20100615_2115", ("10.1.0",		"2011 Architecture Web Update 1 Service Pack")},   // http://revitclinic.typepad.com/my_weblog/2010/06/revit-2011-build-number-update-display.html
            {"20100903_2115", ("10.2.0",		"2011 Architecture Web Update 2 Service Pack")},   // http://revitoped.blogspot.com/2010/09/revit-web-update-2-posted-subscription.html

            // 2012
            {"20110309_2315", ("12.0.0",		"2012 First Customer Ship")},
            {"20110622_0930", ("12.0.1",		"2012 Update Release 1")},
            {"20110916_2132", ("12.0.2",		"2012 Update Release 2")},

            // 2013
            {"20120221_2030", ("12.02.21203",	"2013 First Customer Ship")},
            {"20120716_1115", ("13.0.1",		"2013 Update Release 1")},
            {"20121003_2115", ("13.0.2",		"2013 Update Release 2")},
            {"20130531_2115", ("13.0.3",		"2013 Update Release 3")},
            {"20120821_1330", ("13.0",		    "2013 LT First Customer Ship")},
            {"20130531_0300", ("13.1",		    "2013 LT Update Release 1")},

            // 2014
            // tested on local machine
            {"20130308_1515", ("13.03.08151",	"2014 First Customer Ship")},
            {"20130709_2115", ("14.0.1",		"2014 Update Release 1")},
            {"20131024_2115", ("14.0.2",		"2014 Update Release 2")},
            {"20140709_2115", ("14.0.3",		"2014 Update Release 3")},

            // 2015
            {"20140223_1515", ("15.0.136.0",	"2015 First Customer Ship")},
            {"20140322_1515", ("15.0.1",		"2015 Update Release 1")},
            {"20140323_1530", ("15.0.2",		"2015 Update Release 2")},
            {"20140606_1530", ("15.0.3",		"2015 Update Release 3")},
            {"20140903_1530", ("15.0.4",		"2015 Update Release 4")},
            {"20141119_1515", ("15.0.5",		"2015 Update Release 5")},
            {"20140905_0730", ("15.2.0",		"2015 Release 2 (Subscription only release)")},
            {"20141119_0715", ("15.2.5",		"2015 Release 2 Update Release 5 (Subscription only release)")},
            {"20150127_1515", ("15.0.6",		"2015 Update Release 6")},
            {"20150127_0715", ("15.2.6",		"2015 Release 2 Update Release 6 (Subscription only release)")},
            {"20150303_1515", ("15.0.7",		"2015 Update Release 7")},
            {"20150303_0715", ("15.2.7",		"2015 Release 2 Update Release 7 (Subscription only release)")},
            {"20150512_1015", ("15.0.8",		"2015 Update Release 8")},
            {"20150511_0715", ("15.2.8",		"2015 Release 2 Update Release 8 (Subscription only release)")},
            {"20150702_1515", ("15.0.9",		"2015 Update Release 9")},
            {"20150704_0715", ("15.2.9",		"2015 Release 2 Update Release 9 (Subscription only release)")},
            {"20151007_1515", ("15.0.10",		"2015 Update Release 10")},
            {"20151008_0715", ("15.2.10",		"2015 Release 2 Update Release 10 (Subscription only release)")},
            {"20151207_1515", ("15.0.11",		"2015 Update Release 11 *Issue with Revit Server")},
            {"20151208_0715", ("15.2.11",		"2015 Release 2 Update Release 11 (Subscription only release) *Issue with Revit Server")},
            {"20160119_1515", ("15.0.12",		"2015 Update Release 12")},
            {"20160120_0715", ("15.2.12",		"2015 Release 2 Update Release 12 (Subscription only release)")},
            {"20160220_1515", ("15.0.13",		"2015 Update Release 13")},
            {"20160220_0715", ("15.2.13",		"2015 Release 2 Update Release 13 (Subscription only release)")},
            {"20160512_1515", ("15.0.14",		"2015 Update Release 14")},
            {"20160512_0715", ("15.2.14",		"2015 Release 2 Update Release 14  (Subscription only release)")},

            // 2016
            {"20150220_1215", ("16.0.428.0",	"2016 First Customer Ship")},
            {"20150506_1715", ("16.0.462.0",	"2016 Service Pack 1")},
            {"20150701_1515", ("16.0.485.0",	"2016 Unreleased Update")},    // https://knowledge.autodesk.com/support/revit-products/troubleshooting/caas/sfdcarticles/sfdcarticles/Revit-2016-Release-2-Error-1642.html
            {"20150714_1515", ("16.0.490.0",	"2016 Service Pack 2")},
            {"20151007_0715", ("16.0.1063",		"2016 Release 2 (R2)")},
            {"20151209_0715", ("16.0.1092.0",	"2016 Update 1 for R2")},
            {"20160126_1600", ("16.0.1108.0",	"2016 Update 2 for R2")},
            {"20160217_1800", ("16.0.1118.0",	"2016 Update 3 for R2")},
            {"20160314_0715", ("16.0.1124.0",	"2016 Update 4 for R2")},
            {"20160525_1230", ("16.0.1144.0",	"2016 Update 5 for R2")},
            {"20160720_0715", ("16.0.1161.0",	"2016 Update 6 for R2")},
            {"20161004_0715", ("16.0.1185.0",	"2016 Update 7 for R2")},
            {"20170117_1200", ("16.0.1205.0",	"2016 Update 8 for R2 (2016.1.8)")},

            // 2017
            {"20160225_1515", ("17.0.416.0",	"2017 First Customer Ship")},
            {"20160606_1515", ("17.0.476.0",	"2017 Service Pack 1")},
            {"20160720_1515", ("17.0.501.0",	"2017 Service Pack 2")},
            {"20161205_1400", ("17.0.503.0",	"2017.0.3")},
            {"20181011_1545", ("17.0.511.0",	"2017.0.4")}, // https://github.com/eirannejad/pyRevit/issues/456
            {"20161006_0315", ("17.0.1081.0",	"2017.1")},
            {"20161117_1200", ("17.0.1099.0",	"2017.1.1")},
            {"20170118_1100", ("17.0.1117.0",	"2017.2")},
            {"20170419_0315", ("17.0.1128.0",	"2017.2.1")},
            {"20170816_0615", ("17.0.1146.0",	"2017.2.2")},
            {"20171027_0315", ("17.0.1150.0",	"2017.2.3")},
            {"20181011_1645", ("17.0.1158.0",	"2017.2.4")},

            // 2018
            {"20170223_1515", ("18.0.0.420",	"2018 First Customer Ship")},
            {"20170421_2315", ("18.0.1.2",		"2018.0.1")},
            {"20170525_2315", ("18.0.2.11",		"2018.0.2")},
            {"20181015_0930", ("18.0.3.6",		"2018.0.3")},
            {"20170630_0700", ("18.1.0.92",		"2018.1")},
            {"20170907_2315", ("18.1.1.18",		"2018.1.1")},
            {"20170927_1515", ("18.2.0.51",		"2018.2")},
            {"20180329_1100", ("18.3.0.81",		"2018.3")}, // https://github.com/eirannejad/pyRevit/issues/456
            {"20180423_1000", ("18.3.1.2",		"2018.3.1")},
            {"20181011_1500", ("18.3.2.7",		"2018.3.2")},

            // 2019
            {"20180216_1515", ("19.0.0.405",	"2019 First Customer Ship")},
            {"20180328_1800", ("19.0.1.1",		"2019 Update for Trial Build")},
            {"20180518_1600", ("19.0.10.18",	"2019.0.1")},
            {"20180927_2315", ("19.0.20.1",		"2019.0.2")},
            {"20180806_1515", ("19.1.0.112",	"2019.1")},
        };

        private static Regex BuildNumberFinder = new Regex(@".*(?<build>\d{8}_\d{4}).*");

        private RevitProduct(string buildNumber) {
            BuildNumber = buildNumber;
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
                        var revitProduct =
                            RevitProduct.LookupRevitProduct(subkey.GetValue("DisplayVersion") as string);

                        logger.Debug("Revit Product is : {0}", revitProduct);
                        if (revitProduct != null) {
                            revitProduct.InstallLocation = subkey.GetValue("InstallLocation") as string;
                            revitProduct.LanguageCode = (int)subkey.GetValue("Language");
                            installedRevits.Add(revitProduct);
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

        public override string ToString() {
            return String.Format("{0} | Version: {1} | Language: {3} | Path: \"{2}\"", ProductName, Version, InstallLocation, LanguageCode);
        }

        public override int GetHashCode() {
            return BuildNumber.GetHashCode();
        }

        public string BuildNumber { get; private set; }

        public string BuildTarget { get; private set; } = "x64";

        public Version Version {
            get {
                if (_revitBuildNumberLookupTable.ContainsKey(BuildNumber))
                    return new Version(_revitBuildNumberLookupTable[BuildNumber].Item1);
                else
                    return null;
            }
        }

        public Version FullVersion {
            get {
                if (Version != null) {
                    if (Version.Revision >=0 )
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
                else
                    return "";
            }
        }

        public string DefaultInstallLocation {
            get {
                return System.Environment.GetFolderPath(System.Environment.SpecialFolder.ProgramFiles);
            }
        }

        public string InstallLocation {
            get {
                if (_registeredInstallPath == null) {
                    string revitInstallDirName = null;
                    if (FullVersion != null)
                        revitInstallDirName = string.Format("Revit {0}", FullVersion.Major);
                    else if (Version != null)
                        revitInstallDirName = string.Format("Revit {0}", 2000 + Version.Major);
                    var expectedPath = Path.Combine(DefaultInstallLocation,		"Autodesk", revitInstallDirName);
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

        public string ExecutiveLocation {
            get {
                return Path.Combine(InstallLocation, "Revit.exe");
            }
        }

        public int LanguageCode { get; set; }

    }


    // MODEL =========================================================================================================
    public class RevitController {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        public static List<RevitProcess> ListRunningRevits() {
            var runningRevits = new List<RevitProcess>();
            foreach (Process ps in Process.GetProcesses()) {
                if (RevitProcess.IsRevitProcess(ps))
                    runningRevits.Add(new RevitProcess(ps));
            }
            return runningRevits;
        }

        public static List<RevitProcess> ListRunningRevits(Version revitVersion) {
            var runningRevits = new List<RevitProcess>();
            foreach (RevitProcess revit in ListRunningRevits()) {
                if (revit.RevitProduct.Version == revitVersion)
                    runningRevits.Add(revit);
            }
            return runningRevits;
        }

        public static List<RevitProcess> ListRunningRevits(int revitYear) {
            var runningRevits = new List<RevitProcess>();
            foreach (RevitProcess revit in ListRunningRevits()) {
                if (revit.RevitProduct.FullVersion.Major == revitYear)
                    runningRevits.Add(revit);
            }
            return runningRevits;
        }

        public static void KillRunningRevits(Version revitVersion) {
            foreach (RevitProcess revit in ListRunningRevits(revitVersion))
                revit.Kill();
        }

        public static void KillRunningRevits(int revitYear) {
            foreach (RevitProcess revit in ListRunningRevits(revitYear))
                revit.Kill();
        }

        public static void KillAllRunningRevits() {
            foreach (RevitProcess revit in ListRunningRevits())
                revit.Kill();
        }
    }
}