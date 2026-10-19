using NUnit.Framework;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;

using pyRevitLabs.Common;
using pyRevitLabs.NLog;
using pyRevitLabs.NLog.Config;
using pyRevitLabs.NLog.Targets;
using pyRevitLabs.TargetApps.Revit;

namespace pyRevitLabs.TargetApps.Revit.Tests {
    /// <summary>
    /// Covers how a Revit installation is matched to a host database record.
    /// </summary>
    /// <remarks>
    /// Build numbers are not unique across releases, so every case here feeds the
    /// resolver a set of records with a deliberate build collision and pins the
    /// outcome to the identity the caller can actually supply.
    /// </remarks>
    [TestFixture()]
    [FixtureLifeCycle(LifeCycle.InstancePerTestCase)]
    [Category("HostFree")]
    [Category("Unit")]
    public class RevitProductDataTests {
        /// <summary>The host database is sourced from the development branch.</summary>
        [Test]
        public void HostFileURL_UsesDevelopBranch_Test() {
            Assert.That(RevitProductData.HostFileURL.Contains("develop"), Is.True);
            Assert.That(RevitProductData.HostFileURL.Contains("release/pyrevit-hosts.json"), Is.True);
        }

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

        [Test()]
        public void FindProductInfo_CollidingBuild_UsesFullVersionOfHost() {
            var records = Colliding2020And2021Records();

            var for2020 = RevitProductData.FindProductInfo(records, Shared2020_2021Build,
                                                            productVersion: new Version(20, 2, 90, 12));
            Assert.That(for2020.release, Is.EqualTo("2020.2.9"));

            var for2021 = RevitProductData.FindProductInfo(records, Shared2020_2021Build,
                                                            productVersion: new Version(21, 1, 70, 21));
            Assert.That(for2021.release, Is.EqualTo("2021.1.7"));
        }

        [Test()]
        public void FindProductInfo_CollidingBuild_UsesInstallPathOfHost() {
            var records = Colliding2020And2021Records();

            var for2020 = RevitProductData.FindProductInfo(records, Shared2020_2021Build,
                                                            installPath: @"C:\Program Files\Autodesk\Revit 2020\");
            Assert.That(for2020.release, Is.EqualTo("2020.2.9"));

            var for2021 = RevitProductData.FindProductInfo(records, Shared2020_2021Build,
                                                            installPath: @"C:\Program Files\Autodesk\Revit 2021\");
            Assert.That(for2021.release, Is.EqualTo("2021.1.7"));
        }

        [Test()]
        public void FindProductInfo_CollidingBuild_WithoutIdentity_DoesNotGuess() {
            var found = RevitProductData.FindProductInfo(Colliding2020And2021Records(), Shared2020_2021Build);
            Assert.That(found, Is.Null, "A build shared by two product years must not resolve to an arbitrary record");
        }

        [Test()]
        public void FindProductInfo_UniqueBuildMatch_ContradictingProductYear_IsRejected() {
            var found = RevitProductData.FindProductInfo(CollidingRecordWithout2020(), Shared2020_2021Build,
                                                          installPath: @"C:\Program Files\Autodesk\Revit 2020\",
                                                          productVersion: new Version(20, 2, 90, 12));
            Assert.That(found, Is.Null, "A record from another product year must not match a Revit 2020 install");
        }

        [Test()]
        public void FindProductInfo_CollidingBuildAcrossSupportedYears_UsesProductIdentity() {
            var records = Colliding2021And2022Records();

            var for2021 = RevitProductData.FindProductInfo(records, Shared2021_2022Build,
                                                            productVersion: new Version(21, 1, 60, 25));
            Assert.That(for2021.release, Is.EqualTo("2021.1.6"));

            var for2022 = RevitProductData.FindProductInfo(records, Shared2021_2022Build,
                                                            installPath: @"C:\Program Files\Autodesk\Revit 2022\");
            Assert.That(for2022.release, Is.EqualTo("2022.1.2"));
        }

        [Test()]
        public void FindProductInfo_CollidingBuildWithinSameProductYear_StillMatches() {
            var records = new List<HostProductInfo>() {
                Record("2023.1.1", "23.1.10.4", Shared2023Build),
                Record("2023.1.1.1", "23.1.10.4", Shared2023Build)
            };

            var found = RevitProductData.FindProductInfo(records, Shared2023Build);
            Assert.That(found, Is.Not.Null, "Records of the same product year describe the same host");
            Assert.That(RevitProductData.GetProductYearFromVersionString(found.version), Is.EqualTo(2023));
        }

        [Test()]
        public void FindProductInfo_RevitExeProductVersionString_ResolvesNamedRelease() {
            var found = RevitProductData.FindProductInfo(Colliding2021And2022Records(),
                                                          "Revit 2022.1.2 (20220123_1515(x64))");
            Assert.That(found, Is.Not.Null);
            Assert.That(found.release, Is.EqualTo("2022.1.2"));
        }

        [Test()]
        public void FindProductInfo_RegistryDisplayVersionNotInDatabase_DoesNotMatch() {
            var found = RevitProductData.FindProductInfo(Colliding2020And2021Records(), "2020.2");
            Assert.That(found, Is.Null);
        }

        [Test()]
        public void FindProductInfo_RegistryVersionOfAnotherProductYear_IsRejected() {
            var found = RevitProductData.FindProductInfo(Colliding2020And2021Records(), "2021.1.7",
                                                          installPath: @"C:\Program Files\Autodesk\Revit 2020\");
            Assert.That(found, Is.Null);
        }

        [Test()]
        public void FindProductInfo_UniqueRecord_ResolvesWithoutAnyIdentity() {
            var records = new List<HostProductInfo>() {
                Record("2021.1.7", "21.1.70.21", Shared2020_2021Build)
            };

            Assert.That(RevitProductData.FindProductInfo(records, "2021.1.7").release, Is.EqualTo("2021.1.7"));
            Assert.That(RevitProductData.FindProductInfo(records, "21.1.70.21").release, Is.EqualTo("2021.1.7"));
            Assert.That(RevitProductData.FindProductInfo(records, Shared2020_2021Build).release, Is.EqualTo("2021.1.7"));
        }

        [Test()]
        public void FindProductInfo_NoIdentifierOrNoRecords_ReturnsNull() {
            Assert.That(RevitProductData.FindProductInfo(Colliding2020And2021Records(), null), Is.Null);
            Assert.That(RevitProductData.FindProductInfo(Colliding2020And2021Records(), string.Empty), Is.Null);
            Assert.That(RevitProductData.FindProductInfo(new List<HostProductInfo>(), Shared2020_2021Build), Is.Null);
            Assert.That(RevitProductData.FindProductInfo(null, Shared2020_2021Build), Is.Null);
        }

        [Test()]
        public void FindProductInfo_IgnoresRecordsOfAnUnknownSchema() {
            var records = new List<HostProductInfo>() {
                Record("2021.1.7", "21.1.70.21", Shared2020_2021Build)
            };
            records[0].meta.schema = "2.0";

            Assert.That(RevitProductData.FindProductInfo(records, Shared2020_2021Build), Is.Null);
        }

        [Test()]
        public void MinimumSupportedProductYear_ExcludesRevit2020() {
            Assert.That(RevitProductData.MinimumSupportedProductYear, Is.EqualTo(2021));
            Assert.That(RevitProductData.IsSupportedProductYear(2020), Is.False);
            Assert.That(RevitProductData.IsSupportedProductYear(0), Is.False);
            Assert.That(RevitProductData.IsSupportedProductYear(2021), Is.True);
            Assert.That(RevitProductData.IsSupportedProductYear(2026), Is.True);
        }

        [Test()]
        public void GetUnsupportedProductNote_ReportsTheYearAndTheMinimum() {
            Assert.That(RevitProductData.GetUnsupportedProductNote(2021), Is.Null, "Supported years must not carry a rejection note");

            var note = RevitProductData.GetUnsupportedProductNote(2020);
            Assert.That(note, Is.Not.Null);
            Assert.That(note, Does.Contain("2020"));
            Assert.That(note, Does.Contain("2021"));
        }

        [Test()]
        public void GetProductYearFromPath_ReadsTheRevitFolder() {
            Assert.That(RevitProductData.GetProductYearFromPath(@"C:\Program Files\Autodesk\Revit 2020\"), Is.EqualTo(2020));
            Assert.That(RevitProductData.GetProductYearFromPath(@"C:\Program Files\Autodesk\Revit 2025\Program\Revit.exe"), Is.EqualTo(2025));
            Assert.That(RevitProductData.GetProductYearFromPath(@"C:\Autodesk\Revit\"), Is.EqualTo(0));
            Assert.That(RevitProductData.GetProductYearFromPath(null), Is.EqualTo(0));
        }

        [Test()]
        public void GetProductYearFromVersionString_ReadsTheMajorVersion() {
            Assert.That(RevitProductData.GetProductYearFromVersionString("20.2.90.12"), Is.EqualTo(2020));
            Assert.That(RevitProductData.GetProductYearFromVersionString("21.1.70.21"), Is.EqualTo(2021));
            Assert.That(RevitProductData.GetProductYearFromVersionString("22.1.21.13"), Is.EqualTo(2022));
            Assert.That(RevitProductData.GetProductYearFromVersionString("not-a-version"), Is.EqualTo(0));
            Assert.That(RevitProductData.GetProductYearFromVersionString(null), Is.EqualTo(0));
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
    /// <para>
    /// These tests resolve real installed products. Run locally with the required
    /// Revit versions; pure metadata matching remains in the HostFree fixtures.
    /// </para>
    /// </remarks>
    [TestFixture()]
    [FixtureLifeCycle(LifeCycle.InstancePerTestCase)]
    [NonParallelizable]
    [Category("Revit")]
    [Category("Integration")]
    public class BelowMinimumProductReportingTests {
        private const string LevelSeparator = "|";
        private const string SwitchReleaseAdvice = "Use a pyRevit release that supports Revit";
        private const string NotATargetStatement = "is not a target for this pyRevit line";

        private LoggingConfiguration _previousConfig;
        private MemoryTarget _capture;

        [SetUp()]
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

        [TearDown()]
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
            var products = RevitProduct.ListInstalledProducts();
            if (products.Count == 0)
                Assert.Inconclusive("No Revit is installed on this machine");
            return products;
        }

        /// <summary>
        /// The below-minimum Revits installed on this machine, which the report
        /// contract is only observable against.
        /// </summary>
        private List<RevitProduct> BelowMinimumInstalledProducts() {
            var belowMinimum = ScanInstalledProducts()
                                              .Where(prod => !prod.IsSupported && prod.ProductYear > 0)
                                              .ToList();
            if (belowMinimum.Count == 0)
                Assert.Inconclusive("No Revit below the minimum supported year is installed on this machine");
            return belowMinimum;
        }

        /// <summary>
        /// The oldest below-minimum Revit whose binary can actually be read, which is
        /// what the resolver needs before it can report anything.
        /// </summary>
        private RevitProduct BelowMinimumInstalledProduct() {
            var readable = BelowMinimumInstalledProducts()
                                          .Where(prod => CommonUtils.VerifyFile(prod.ExecutiveLocation))
                                          .ToList();
            if (readable.Count == 0)
                Assert.Inconclusive("No below-minimum Revit with a readable binary is installed on this machine");
            return readable.OrderBy(prod => prod.ProductYear).First();
        }

        [Test()]
        public void ResolveProduct_RunningHost_BelowMinimumProduct_WarnsToSwitchRelease() {
            var installed = BelowMinimumInstalledProduct();

            var resolved = RevitProduct.ResolveProduct(installed.BuildNumber,
                                                        installed.ExecutiveLocation,
                                                        installed.InstallLocation,
                                                        ResolvedProductRole.RunningHost);

            Assert.That(resolved, Is.Not.Null);
            Assert.That(resolved.IsSupported, Is.False);
            var warnings = Report("Warn");
            Assert.That(warnings, Does.Contain(SwitchReleaseAdvice));
            Assert.That(warnings, Does.Contain(installed.ProductYear.ToString()));
        }

        [Test()]
        public void ResolveProduct_InstalledSibling_BelowMinimumProduct_OnlyReportsInfo() {
            var installed = BelowMinimumInstalledProduct();

            var resolved = RevitProduct.ResolveProduct(installed.BuildNumber,
                                                        installed.ExecutiveLocation,
                                                        installed.InstallLocation,
                                                        ResolvedProductRole.InstalledSibling);

            Assert.That(resolved, Is.Not.Null, "A below-minimum install is still detected, only the report changes");
            Assert.That(resolved.IsSupported, Is.False);
            Assert.That(CapturedAtLevel("Warn").Count, Is.EqualTo(0), "An installed product the user did not launch must never warn: " + Report("Warn"));
            var reports = Report("Info");
            Assert.That(reports, Does.Contain(NotATargetStatement));
            Assert.That(reports, Does.Contain(installed.ProductYear.ToString()));
            Assert.That(reports.Contains(SwitchReleaseAdvice), Is.False, "The scan must not tell the user to switch pyRevit releases for a product they did not launch");
        }

        [Test()]
        public void ListInstalledProducts_DoesNotWarnAboutAnyProductItFinds() {
            ScanInstalledProducts();

            Assert.That(CapturedAtLevel("Warn").Count, Is.EqualTo(0), "Session start must not warn about products it merely found installed: " + Report("Warn"));
            Assert.That(CapturedAtLevel("Error").Count, Is.EqualTo(0), Report("Error"));
        }

        [Test()]
        public void ListInstalledProducts_KeepsBelowMinimumProductsListed() {
            foreach (var product in BelowMinimumInstalledProducts())
                Assert.That(product.ToString(), Does.Contain(RevitProductData.MinimumSupportedProductYear.ToString()));
        }


    }

    /// <summary>Guards the default reporting role without an installed product.</summary>
    [TestFixture]
    [FixtureLifeCycle(LifeCycle.InstancePerTestCase)]
    [Category("HostFree")]
    [Category("Unit")]
    public class RevitProductRoleContractTests {
        /// <summary>Existing callers that omit the role still resolve their running host.</summary>
        [Test()]
        public void ResolveProduct_DefaultsToTreatingTheProductAsTheRunningHost() {
            var roleParameter = typeof(RevitProduct).GetMethod("ResolveProduct")
                                                        .GetParameters()
                                                        .Single(par => par.Name == "role");

            Assert.That(roleParameter.IsOptional, Is.True, "Callers that omit the role resolve the host they are launching into");
            Assert.That(roleParameter.DefaultValue, Is.EqualTo(ResolvedProductRole.RunningHost));
        }
    }

}
