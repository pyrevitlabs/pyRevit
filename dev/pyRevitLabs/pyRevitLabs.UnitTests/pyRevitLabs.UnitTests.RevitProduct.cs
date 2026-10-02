using Microsoft.VisualStudio.TestTools.UnitTesting;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;

using pyRevitLabs.Common;
using pyRevitLabs.NLog;
using pyRevitLabs.NLog.Config;
using pyRevitLabs.NLog.Targets;
using pyRevitLabs.TargetApps.Revit;

namespace pyRevitLabs.UnitTests.RevitProducts {
    /// <summary>
    /// Covers how a Revit installation is matched to a host database record.
    /// </summary>
    /// <remarks>
    /// Build numbers are not unique across releases, so every case here feeds the
    /// resolver a set of records with a deliberate build collision and pins the
    /// outcome to the identity the caller can actually supply.
    /// </remarks>
    [TestClass()]
    public class RevitProductDataTests {
        private const string Shared2020_2021Build = "20220517_1515";
        private const string Shared2021_2022Build = "20220123_1515";
        private const string Shared2023Build = "20221122_1550";

        private static HostProductInfo Record(string release, string version, string build) {
            return new HostProductInfo {
                meta = new HostProductInfoMeta { schema = "1.0" },
                product = "Autodesk Revit",
                release = release,
                version = version,
                build = build,
                target = "x64"
            };
        }

        /// <summary>The 6.5-line host database, where the 2020/2021 collision exists.</summary>
        private static List<HostProductInfo> Colliding2020And2021Records() {
            return new List<HostProductInfo>() {
                Record("2020.2.9", "20.2.90.12", Shared2020_2021Build),
                Record("2021.1.7", "21.1.70.21", Shared2020_2021Build)
            };
        }

        /// <summary>The current host database, which dropped 2020 and so only keeps one half of the collision.</summary>
        private static List<HostProductInfo> CollidingRecordWithout2020() {
            return new List<HostProductInfo>() {
                Record("2021.1.7", "21.1.70.21", Shared2020_2021Build)
            };
        }

        private static List<HostProductInfo> Colliding2021And2022Records() {
            return new List<HostProductInfo>() {
                Record("2021.1.6", "21.1.60.25", Shared2021_2022Build),
                Record("2022.1.2", "22.1.21.13", Shared2021_2022Build)
            };
        }

        [TestMethod()]
        public void FindProductInfo_CollidingBuild_UsesFullVersionOfHost() {
            var records = Colliding2020And2021Records();

            var for2020 = RevitProductData.FindProductInfo(records, Shared2020_2021Build,
                                                            productVersion: new Version(20, 2, 90, 12));
            Assert.AreEqual("2020.2.9", for2020.release);

            var for2021 = RevitProductData.FindProductInfo(records, Shared2020_2021Build,
                                                            productVersion: new Version(21, 1, 70, 21));
            Assert.AreEqual("2021.1.7", for2021.release);
        }

        [TestMethod()]
        public void FindProductInfo_CollidingBuild_UsesInstallPathOfHost() {
            var records = Colliding2020And2021Records();

            var for2020 = RevitProductData.FindProductInfo(records, Shared2020_2021Build,
                                                            installPath: @"C:\Program Files\Autodesk\Revit 2020\");
            Assert.AreEqual("2020.2.9", for2020.release);

            var for2021 = RevitProductData.FindProductInfo(records, Shared2020_2021Build,
                                                            installPath: @"C:\Program Files\Autodesk\Revit 2021\");
            Assert.AreEqual("2021.1.7", for2021.release);
        }

        [TestMethod()]
        public void FindProductInfo_CollidingBuild_WithoutIdentity_DoesNotGuess() {
            var found = RevitProductData.FindProductInfo(Colliding2020And2021Records(), Shared2020_2021Build);
            Assert.IsNull(found, "A build shared by two product years must not resolve to an arbitrary record");
        }

        [TestMethod()]
        public void FindProductInfo_UniqueBuildMatch_ContradictingProductYear_IsRejected() {
            var found = RevitProductData.FindProductInfo(CollidingRecordWithout2020(), Shared2020_2021Build,
                                                          installPath: @"C:\Program Files\Autodesk\Revit 2020\",
                                                          productVersion: new Version(20, 2, 90, 12));
            Assert.IsNull(found, "A record from another product year must not match a Revit 2020 install");
        }

        [TestMethod()]
        public void FindProductInfo_CollidingBuildAcrossSupportedYears_UsesProductIdentity() {
            var records = Colliding2021And2022Records();

            var for2021 = RevitProductData.FindProductInfo(records, Shared2021_2022Build,
                                                            productVersion: new Version(21, 1, 60, 25));
            Assert.AreEqual("2021.1.6", for2021.release);

            var for2022 = RevitProductData.FindProductInfo(records, Shared2021_2022Build,
                                                            installPath: @"C:\Program Files\Autodesk\Revit 2022\");
            Assert.AreEqual("2022.1.2", for2022.release);
        }

        [TestMethod()]
        public void FindProductInfo_CollidingBuildWithinSameProductYear_StillMatches() {
            var records = new List<HostProductInfo>() {
                Record("2023.1.1", "23.1.10.4", Shared2023Build),
                Record("2023.1.1.1", "23.1.10.4", Shared2023Build)
            };

            var found = RevitProductData.FindProductInfo(records, Shared2023Build);
            Assert.IsNotNull(found, "Records of the same product year describe the same host");
            Assert.AreEqual(2023, RevitProductData.GetProductYearFromVersionString(found.version));
        }

        [TestMethod()]
        public void FindProductInfo_RevitExeProductVersionString_ResolvesNamedRelease() {
            var found = RevitProductData.FindProductInfo(Colliding2021And2022Records(),
                                                          "Revit 2022.1.2 (20220123_1515(x64))");
            Assert.IsNotNull(found);
            Assert.AreEqual("2022.1.2", found.release);
        }

        [TestMethod()]
        public void FindProductInfo_RegistryDisplayVersionNotInDatabase_DoesNotMatch() {
            var found = RevitProductData.FindProductInfo(Colliding2020And2021Records(), "2020.2");
            Assert.IsNull(found);
        }

        [TestMethod()]
        public void FindProductInfo_RegistryVersionOfAnotherProductYear_IsRejected() {
            var found = RevitProductData.FindProductInfo(Colliding2020And2021Records(), "2021.1.7",
                                                          installPath: @"C:\Program Files\Autodesk\Revit 2020\");
            Assert.IsNull(found);
        }

        [TestMethod()]
        public void FindProductInfo_UniqueRecord_ResolvesWithoutAnyIdentity() {
            var records = new List<HostProductInfo>() {
                Record("2021.1.7", "21.1.70.21", Shared2020_2021Build)
            };

            Assert.AreEqual("2021.1.7", RevitProductData.FindProductInfo(records, "2021.1.7").release);
            Assert.AreEqual("2021.1.7", RevitProductData.FindProductInfo(records, "21.1.70.21").release);
            Assert.AreEqual("2021.1.7", RevitProductData.FindProductInfo(records, Shared2020_2021Build).release);
        }

        [TestMethod()]
        public void FindProductInfo_NoIdentifierOrNoRecords_ReturnsNull() {
            Assert.IsNull(RevitProductData.FindProductInfo(Colliding2020And2021Records(), null));
            Assert.IsNull(RevitProductData.FindProductInfo(Colliding2020And2021Records(), string.Empty));
            Assert.IsNull(RevitProductData.FindProductInfo(new List<HostProductInfo>(), Shared2020_2021Build));
            Assert.IsNull(RevitProductData.FindProductInfo(null, Shared2020_2021Build));
        }

        [TestMethod()]
        public void FindProductInfo_IgnoresRecordsOfAnUnknownSchema() {
            var records = new List<HostProductInfo>() {
                Record("2021.1.7", "21.1.70.21", Shared2020_2021Build)
            };
            records[0].meta.schema = "2.0";

            Assert.IsNull(RevitProductData.FindProductInfo(records, Shared2020_2021Build));
        }

        [TestMethod()]
        public void MinimumSupportedProductYear_ExcludesRevit2020() {
            Assert.AreEqual(2021, RevitProductData.MinimumSupportedProductYear);
            Assert.IsFalse(RevitProductData.IsSupportedProductYear(2020));
            Assert.IsFalse(RevitProductData.IsSupportedProductYear(0));
            Assert.IsTrue(RevitProductData.IsSupportedProductYear(2021));
            Assert.IsTrue(RevitProductData.IsSupportedProductYear(2026));
        }

        [TestMethod()]
        public void GetUnsupportedProductNote_ReportsTheYearAndTheMinimum() {
            Assert.IsNull(RevitProductData.GetUnsupportedProductNote(2021),
                          "Supported years must not carry a rejection note");

            var note = RevitProductData.GetUnsupportedProductNote(2020);
            Assert.IsNotNull(note);
            StringAssert.Contains(note, "2020");
            StringAssert.Contains(note, "2021");
        }

        [TestMethod()]
        public void GetProductYearFromPath_ReadsTheRevitFolder() {
            Assert.AreEqual(2020, RevitProductData.GetProductYearFromPath(@"C:\Program Files\Autodesk\Revit 2020\"));
            Assert.AreEqual(2025, RevitProductData.GetProductYearFromPath(@"C:\Program Files\Autodesk\Revit 2025\Program\Revit.exe"));
            Assert.AreEqual(0, RevitProductData.GetProductYearFromPath(@"C:\Autodesk\Revit\"));
            Assert.AreEqual(0, RevitProductData.GetProductYearFromPath(null));
        }

        [TestMethod()]
        public void GetProductYearFromVersionString_ReadsTheMajorVersion() {
            Assert.AreEqual(2020, RevitProductData.GetProductYearFromVersionString("20.2.90.12"));
            Assert.AreEqual(2021, RevitProductData.GetProductYearFromVersionString("21.1.70.21"));
            Assert.AreEqual(2022, RevitProductData.GetProductYearFromVersionString("22.1.21.13"));
            Assert.AreEqual(0, RevitProductData.GetProductYearFromVersionString("not-a-version"));
            Assert.AreEqual(0, RevitProductData.GetProductYearFromVersionString(null));
        }
    }

    /// <summary>
    /// Covers how loudly a product below the minimum supported year is reported.
    /// </summary>
    /// <remarks>
    /// pyRevit warns about a below-minimum year only when that year is the host
    /// being launched into. The same product found by the registry scan is a
    /// routine fact about the machine - side-by-side installs are the normal
    /// setup - and warning about it made every session announce a product the
    /// user never launched and advise them to switch pyRevit releases.
    /// </remarks>
    [TestClass()]
    public class BelowMinimumProductReportingTests {
        private const string LevelSeparator = "|";
        private const string SwitchReleaseAdvice = "Use a pyRevit release that supports Revit";
        private const string NotATargetStatement = "is not a target for this pyRevit line";

        private LoggingConfiguration _previousConfig;
        private MemoryTarget _capture;

        [TestInitialize()]
        public void StartCapturingLog() {
            _previousConfig = LogManager.Configuration;
            _capture = new MemoryTarget("belowMinimumProductReports") {
                Layout = "${level}" + LevelSeparator + "${message}"
            };
            var config = new LoggingConfiguration();
            config.AddTarget(_capture);
            config.AddRuleForAllLevels(_capture);
            LogManager.Configuration = config;
            LogManager.ReconfigExistingLoggers();
        }

        [TestCleanup()]
        public void StopCapturingLog() {
            LogManager.Configuration = _previousConfig;
            LogManager.ReconfigExistingLoggers();
            _capture?.Dispose();
        }

        private List<string> CapturedLines() {
            return _capture.Logs.ToList();
        }

        private List<string> CapturedAtLevel(string level) {
            var prefix = level + LevelSeparator;
            return CapturedLines().Where(line => line.StartsWith(prefix)).ToList();
        }

        private string Report(string level) {
            return string.Join(Environment.NewLine, CapturedAtLevel(level));
        }

        /// <summary>
        /// Run the registry scan for real.
        /// </summary>
        /// <remarks>
        /// The scan memoizes its result in a static, so a test that happens to run
        /// after another already scanned would find an empty log and pass without
        /// proving anything. Every test that asserts on what the scan logged clears
        /// the memo first, which also makes the tests independent of run order.
        /// </remarks>
        private List<RevitProduct> ScanInstalledProducts() {
            typeof(RevitProduct)
                .GetField("_installedProductsCache", BindingFlags.NonPublic | BindingFlags.Static)
                .SetValue(null, null);
            return RevitProduct.ListInstalledProducts();
        }

        /// <summary>
        /// A below-minimum Revit install on this machine, which the report
        /// contract is only observable against.
        /// </summary>
        private RevitProduct BelowMinimumInstalledProduct() {
            var belowMinimum = ScanInstalledProducts()
                                              .Where(prod => !prod.IsSupported
                                                            && prod.ProductYear > 0
                                                            && CommonUtils.VerifyFile(prod.ExecutiveLocation))
                                              .OrderBy(prod => prod.ProductYear)
                                              .ToList();
            if (belowMinimum.Count == 0)
                Assert.Inconclusive("No Revit below the minimum supported year is installed on this machine");
            return belowMinimum.First();
        }

        [TestMethod()]
        public void ResolveProduct_RunningHost_BelowMinimumProduct_WarnsToSwitchRelease() {
            var installed = BelowMinimumInstalledProduct();

            var resolved = RevitProduct.ResolveProduct(installed.BuildNumber,
                                                        installed.ExecutiveLocation,
                                                        installed.InstallLocation,
                                                        ResolvedProductRole.RunningHost);

            Assert.IsNotNull(resolved);
            Assert.IsFalse(resolved.IsSupported);
            var warnings = Report("Warn");
            StringAssert.Contains(warnings, SwitchReleaseAdvice);
            StringAssert.Contains(warnings, installed.ProductYear.ToString());
        }

        [TestMethod()]
        public void ResolveProduct_InstalledSibling_BelowMinimumProduct_OnlyReportsInfo() {
            var installed = BelowMinimumInstalledProduct();

            var resolved = RevitProduct.ResolveProduct(installed.BuildNumber,
                                                        installed.ExecutiveLocation,
                                                        installed.InstallLocation,
                                                        ResolvedProductRole.InstalledSibling);

            Assert.IsNotNull(resolved, "A below-minimum install is still detected, only the report changes");
            Assert.IsFalse(resolved.IsSupported);
            Assert.AreEqual(0, CapturedAtLevel("Warn").Count,
                            "An installed product the user did not launch must never warn: " + Report("Warn"));
            var reports = Report("Info");
            StringAssert.Contains(reports, NotATargetStatement);
            StringAssert.Contains(reports, installed.ProductYear.ToString());
            Assert.IsFalse(reports.Contains(SwitchReleaseAdvice),
                           "The scan must not tell the user to switch pyRevit releases for a product they did not launch");
        }

        [TestMethod()]
        public void ListInstalledProducts_DoesNotWarnAboutAnyProductItFinds() {
            var products = ScanInstalledProducts();

            Assert.IsTrue(products.Count > 0, "The registry scan is expected to find the Revits installed here");
            Assert.AreEqual(0, CapturedAtLevel("Warn").Count,
                            "Session start must not warn about products it merely found installed: " + Report("Warn"));
            Assert.AreEqual(0, CapturedAtLevel("Error").Count, Report("Error"));
        }

        [TestMethod()]
        public void ListInstalledProducts_KeepsBelowMinimumProductsListed() {
            var listed = ScanInstalledProducts();
            var belowMinimum = listed.Where(prod => !prod.IsSupported && prod.ProductYear > 0).ToList();

            Assert.IsTrue(belowMinimum.Count > 0,
                          "Downgrading the report must not hide the install: " + string.Join(", ", listed));
            foreach (var product in belowMinimum)
                StringAssert.Contains(product.ToString(), RevitProductData.MinimumSupportedProductYear.ToString());
        }

        [TestMethod()]
        public void ResolveProduct_DefaultsToTreatingTheProductAsTheRunningHost() {
            var roleParameter = typeof(RevitProduct).GetMethod("ResolveProduct")
                                                        .GetParameters()
                                                        .Single(par => par.Name == "role");

            Assert.IsTrue(roleParameter.IsOptional,
                          "Callers that omit the role resolve the host they are launching into");
            Assert.AreEqual(ResolvedProductRole.RunningHost, roleParameter.DefaultValue);
        }
    }
}
