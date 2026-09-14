using Microsoft.VisualStudio.TestTools.UnitTesting;
using System;
using System.IO;

using pyRevitLabs.TargetApps.Revit;

namespace pyRevitLabs.UnitTests.RevitCaches {
    [TestClass()]
    public class RevitCachesTests {
        private string _tempRoot;

        [TestInitialize]
        public void Setup() {
            _tempRoot = Path.Combine(Path.GetTempPath(), "pyRevitRevitCachesTests_" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(_tempRoot);
        }

        [TestCleanup]
        public void Cleanup() {
            if (Directory.Exists(_tempRoot)) {
                try {
                    Directory.Delete(_tempRoot, recursive: true);
                }
                catch {
                    // best-effort cleanup in temp
                }
            }
        }

        [TestMethod()]
        public void GetBIM360CacheDirectory_UsesLocalAppDataDefault() {
            var path = pyRevitLabs.TargetApps.Revit.RevitCaches.GetBIM360CacheDirectory(2025);
            var expectedBase = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);

            Assert.IsTrue(path.StartsWith(expectedBase, StringComparison.OrdinalIgnoreCase),
                $"Default cache path should start with {expectedBase}: {path}");
            Assert.IsTrue(
                path.EndsWith(Path.Combine("Autodesk", "Revit", "Autodesk Revit 2025", "CollaborationCache"),
                              StringComparison.OrdinalIgnoreCase),
                $"Unexpected default cache path: {path}");
        }

        [TestMethod()]
        public void GetRevitIniFile_UsesAppData() {
            var path = pyRevitLabs.TargetApps.Revit.RevitCaches.GetRevitIniFile(2024);
            var expectedBase = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);

            Assert.IsTrue(path.StartsWith(expectedBase, StringComparison.OrdinalIgnoreCase),
                $"Revit.ini path should start with {expectedBase}: {path}");
            Assert.IsTrue(
                path.EndsWith(Path.Combine("Autodesk", "Revit", "Autodesk Revit 2024", "Revit.ini"),
                              StringComparison.OrdinalIgnoreCase),
                $"Unexpected Revit.ini path: {path}");
        }

        [TestMethod()]
        public void ReadCloudModelCacheLocation_ReadsConfiguredValue() {
            var iniPath = WriteIni(
                "[CloudModelCache]\n" +
                "CacheLocation = D:\\Custom\\BIM360Cache\n");

            var value = pyRevitLabs.TargetApps.Revit.RevitCaches.ReadCloudModelCacheLocation(iniPath);
            Assert.AreEqual(@"D:\Custom\BIM360Cache", value);
        }

        [TestMethod()]
        public void ReadCloudModelCacheLocation_StripsQuotesAndIgnoresOtherSections() {
            var iniPath = WriteIni(
                "[Other]\n" +
                "CacheLocation = C:\\Wrong\n" +
                "[CloudModelCache]\n" +
                "CacheLocation=\"C:\\Quoted\\Cache\"\n" +
                "OtherKey=value\n");

            var value = pyRevitLabs.TargetApps.Revit.RevitCaches.ReadCloudModelCacheLocation(iniPath);
            Assert.AreEqual(@"C:\Quoted\Cache", value);
        }

        [TestMethod()]
        public void ReadCloudModelCacheLocation_MissingOrEmpty_ReturnsNull() {
            Assert.IsNull(pyRevitLabs.TargetApps.Revit.RevitCaches.ReadCloudModelCacheLocation(
                Path.Combine(_tempRoot, "missing.ini")));

            var emptyIni = WriteIni("[CloudModelCache]\nCacheLocation=\n", "empty.ini");
            Assert.IsNull(pyRevitLabs.TargetApps.Revit.RevitCaches.ReadCloudModelCacheLocation(emptyIni));

            var noSection = WriteIni("[Directories]\nTempPath=C:\\Temp\n", "nosec.ini");
            Assert.IsNull(pyRevitLabs.TargetApps.Revit.RevitCaches.ReadCloudModelCacheLocation(noSection));
        }

        [TestMethod()]
        public void GetCustomBIM360CacheDirectory_Pre2024_ReturnsNull() {
            var cacheDir = Path.Combine(_tempRoot, "cache2023");
            Directory.CreateDirectory(cacheDir);
            var iniPath = WriteIni($"[CloudModelCache]\nCacheLocation={cacheDir}\n");

            var custom = pyRevitLabs.TargetApps.Revit.RevitCaches.GetCustomBIM360CacheDirectory(2023, iniPath);
            Assert.IsNull(custom, "Custom cache paths are only supported for Revit 2024+");
        }

        [TestMethod()]
        public void GetCustomBIM360CacheDirectory_ReturnsConfiguredPathEvenIfMissing() {
            var missingDir = Path.Combine(_tempRoot, "does-not-exist");
            var iniPath = WriteIni($"[CloudModelCache]\nCacheLocation={missingDir}\n");

            var custom = pyRevitLabs.TargetApps.Revit.RevitCaches.GetCustomBIM360CacheDirectory(2024, iniPath);
            Assert.AreEqual(Path.GetFullPath(missingDir), custom);
        }

        [TestMethod()]
        public void GetCustomBIM360CacheDirectory_ExpandsEnvironmentVariables() {
            var cacheDir = Path.Combine(_tempRoot, "envcache");
            Directory.CreateDirectory(cacheDir);
            var previousValue = Environment.GetEnvironmentVariable("PYREVIT_TEST_BIM360_CACHE");
            Environment.SetEnvironmentVariable("PYREVIT_TEST_BIM360_CACHE", cacheDir);
            try {
                var iniPath = WriteIni("[CloudModelCache]\nCacheLocation=%PYREVIT_TEST_BIM360_CACHE%\n");
                var custom = pyRevitLabs.TargetApps.Revit.RevitCaches.GetCustomBIM360CacheDirectory(2024, iniPath);
                Assert.AreEqual(Path.GetFullPath(cacheDir), custom);
            }
            finally {
                Environment.SetEnvironmentVariable("PYREVIT_TEST_BIM360_CACHE", previousValue);
            }
        }

        [TestMethod()]
        public void GetActiveBIM360CacheDirectory_UsesExistingCustomPath() {
            var cacheDir = Path.Combine(_tempRoot, "cache2025");
            Directory.CreateDirectory(cacheDir);
            var iniPath = WriteIni($"[CloudModelCache]\nCacheLocation={cacheDir}\n");

            var active = pyRevitLabs.TargetApps.Revit.RevitCaches.GetActiveBIM360CacheDirectory(2025, iniPath);
            Assert.AreEqual(Path.GetFullPath(cacheDir), active);
        }

        [TestMethod()]
        public void GetActiveBIM360CacheDirectory_FallsBackWhenCustomMissing() {
            var missingDir = Path.Combine(_tempRoot, "does-not-exist");
            var iniPath = WriteIni($"[CloudModelCache]\nCacheLocation={missingDir}\n");

            var active = pyRevitLabs.TargetApps.Revit.RevitCaches.GetActiveBIM360CacheDirectory(2024, iniPath);
            var expected = pyRevitLabs.TargetApps.Revit.RevitCaches.GetBIM360CacheDirectory(2024);
            Assert.AreEqual(expected, active);
        }

        [TestMethod()]
        public void GetActiveBIM360CacheDirectory_Pre2024_UsesDefault() {
            var cacheDir = Path.Combine(_tempRoot, "cache2023");
            Directory.CreateDirectory(cacheDir);
            var iniPath = WriteIni($"[CloudModelCache]\nCacheLocation={cacheDir}\n");

            var active = pyRevitLabs.TargetApps.Revit.RevitCaches.GetActiveBIM360CacheDirectory(2023, iniPath);
            var expected = pyRevitLabs.TargetApps.Revit.RevitCaches.GetBIM360CacheDirectory(2023);
            Assert.AreEqual(expected, active);
        }

        private string WriteIni(string contents, string fileName = "Revit.ini") {
            var path = Path.Combine(_tempRoot, fileName);
            File.WriteAllText(path, contents);
            return path;
        }
    }
}
