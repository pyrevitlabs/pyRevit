using Microsoft.VisualStudio.TestTools.UnitTesting;
using System;
using System.Collections.Generic;

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
        // 2020.2.9 and 2021.1.7 both ship build 20220517_1515 (issue #3573)
        private const string Shared2020_2021Build = "20220517_1515";
        // 2021.1.6 and 2022.1.2 both ship build 20220123_1515
        private const string Shared2021_2022Build = "20220123_1515";
        // 2023.1.1 and 2023.1.1.1 both ship build 20221122_1550
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
            // the 7.0 host database has no 2020 record, so the build alone looks
            // unique; it still must not claim a Revit 2020 install is Revit 2021
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
            // what a running Revit 2022.1.2 hands to the resolver
            var found = RevitProductData.FindProductInfo(Colliding2021And2022Records(),
                                                          "Revit 2022.1.2 (20220123_1515(x64))");
            Assert.IsNotNull(found);
            Assert.AreEqual("2022.1.2", found.release);
        }

        [TestMethod()]
        public void FindProductInfo_RegistryDisplayVersionNotInDatabase_DoesNotMatch() {
            // Revit 2020.2 registers "2020.2", which no record is named after
            var found = RevitProductData.FindProductInfo(Colliding2020And2021Records(), "2020.2");
            Assert.IsNull(found);
        }

        [TestMethod()]
        public void FindProductInfo_RegistryVersionOfAnotherProductYear_IsRejected() {
            // registry data naming a release the install path contradicts must
            // not bind the install to that release
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
}
