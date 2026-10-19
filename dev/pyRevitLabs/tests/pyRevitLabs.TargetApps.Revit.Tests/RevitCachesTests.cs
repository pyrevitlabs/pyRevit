using NUnit.Framework;
using System;
using System.IO;

using pyRevitLabs.TargetApps.Revit;

namespace pyRevitLabs.TargetApps.Revit.Tests {
    [TestFixture()]
    [FixtureLifeCycle(LifeCycle.InstancePerTestCase)]
    [Category("HostFree")]
    [Category("Integration")]
    public class RevitCachesTests {
        private string _tempRoot;

        [SetUp]
        public void Setup() {
            _tempRoot = Path.Combine(Path.GetTempPath(), "pyRevitRevitCachesTests_" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(_tempRoot);
        }

        [TearDown]
        public void Cleanup() {
            if (Directory.Exists(_tempRoot))
                Directory.Delete(_tempRoot, recursive: true);
        }

        [Test()]
        public void GetBIM360CacheDirectory_UsesLocalAppDataDefault() {
            var path = pyRevitLabs.TargetApps.Revit.RevitCaches.GetBIM360CacheDirectory(2025);
            var expectedBase = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);

            Assert.That(path.StartsWith(expectedBase, StringComparison.OrdinalIgnoreCase), Is.True, $"Default cache path should start with {expectedBase}: {path}");
            Assert.That(path.EndsWith(Path.Combine("Autodesk", "Revit", "Autodesk Revit 2025", "CollaborationCache"),
                              StringComparison.OrdinalIgnoreCase), Is.True, $"Unexpected default cache path: {path}");
        }

        [Test()]
        public void GetRevitIniFile_UsesAppData() {
            var path = pyRevitLabs.TargetApps.Revit.RevitCaches.GetRevitIniFile(2024);
            var expectedBase = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);

            Assert.That(path.StartsWith(expectedBase, StringComparison.OrdinalIgnoreCase), Is.True, $"Revit.ini path should start with {expectedBase}: {path}");
            Assert.That(path.EndsWith(Path.Combine("Autodesk", "Revit", "Autodesk Revit 2024", "Revit.ini"),
                              StringComparison.OrdinalIgnoreCase), Is.True, $"Unexpected Revit.ini path: {path}");
        }

        [Test()]
        public void ReadCloudModelCacheLocation_ReadsConfiguredValue() {
            var iniPath = WriteIni(
                "[CloudModelCache]\n" +
                "CacheLocation = D:\\Custom\\BIM360Cache\n");

            var value = pyRevitLabs.TargetApps.Revit.RevitCaches.ReadCloudModelCacheLocation(iniPath);
            Assert.That(value, Is.EqualTo(@"D:\Custom\BIM360Cache"));
        }

        [Test()]
        public void ReadCloudModelCacheLocation_StripsQuotesAndIgnoresOtherSections() {
            var iniPath = WriteIni(
                "[Other]\n" +
                "CacheLocation = C:\\Wrong\n" +
                "[CloudModelCache]\n" +
                "CacheLocation=\"C:\\Quoted\\Cache\"\n" +
                "OtherKey=value\n");

            var value = pyRevitLabs.TargetApps.Revit.RevitCaches.ReadCloudModelCacheLocation(iniPath);
            Assert.That(value, Is.EqualTo(@"C:\Quoted\Cache"));
        }

        [Test()]
        public void ReadCloudModelCacheLocation_MissingOrEmpty_ReturnsNull() {
            Assert.That(pyRevitLabs.TargetApps.Revit.RevitCaches.ReadCloudModelCacheLocation(
                Path.Combine(_tempRoot, "missing.ini")), Is.Null);

            var emptyIni = WriteIni("[CloudModelCache]\nCacheLocation=\n", "empty.ini");
            Assert.That(pyRevitLabs.TargetApps.Revit.RevitCaches.ReadCloudModelCacheLocation(emptyIni), Is.Null);

            var noSection = WriteIni("[Directories]\nTempPath=C:\\Temp\n", "nosec.ini");
            Assert.That(pyRevitLabs.TargetApps.Revit.RevitCaches.ReadCloudModelCacheLocation(noSection), Is.Null);
        }

        [Test()]
        public void GetCustomBIM360CacheDirectory_Pre2024_ReturnsNull() {
            var cacheDir = Path.Combine(_tempRoot, "cache2023");
            Directory.CreateDirectory(cacheDir);
            var iniPath = WriteIni($"[CloudModelCache]\nCacheLocation={cacheDir}\n");

            var custom = pyRevitLabs.TargetApps.Revit.RevitCaches.GetCustomBIM360CacheDirectory(2023, iniPath);
            Assert.That(custom, Is.Null, "Custom cache paths are only supported for Revit 2024+");
        }

        [Test()]
        public void GetCustomBIM360CacheDirectory_ReturnsConfiguredPathEvenIfMissing() {
            var missingDir = Path.Combine(_tempRoot, "does-not-exist");
            var iniPath = WriteIni($"[CloudModelCache]\nCacheLocation={missingDir}\n");

            var custom = pyRevitLabs.TargetApps.Revit.RevitCaches.GetCustomBIM360CacheDirectory(2024, iniPath);
            Assert.That(custom, Is.EqualTo(Path.GetFullPath(missingDir)));
        }

        [Test()]
        public void GetCustomBIM360CacheDirectory_ExpandsEnvironmentVariables() {
            var cacheDir = Path.Combine(_tempRoot, "envcache");
            Directory.CreateDirectory(cacheDir);
            var previousValue = Environment.GetEnvironmentVariable("PYREVIT_TEST_BIM360_CACHE");
            Environment.SetEnvironmentVariable("PYREVIT_TEST_BIM360_CACHE", cacheDir);
            try {
                var iniPath = WriteIni("[CloudModelCache]\nCacheLocation=%PYREVIT_TEST_BIM360_CACHE%\n");
                var custom = pyRevitLabs.TargetApps.Revit.RevitCaches.GetCustomBIM360CacheDirectory(2024, iniPath);
                Assert.That(custom, Is.EqualTo(Path.GetFullPath(cacheDir)));
            }
            finally {
                Environment.SetEnvironmentVariable("PYREVIT_TEST_BIM360_CACHE", previousValue);
            }
        }

        [Test()]
        public void GetActiveBIM360CacheDirectory_UsesExistingCustomPath() {
            var cacheDir = Path.Combine(_tempRoot, "cache2025");
            Directory.CreateDirectory(cacheDir);
            var iniPath = WriteIni($"[CloudModelCache]\nCacheLocation={cacheDir}\n");

            var active = pyRevitLabs.TargetApps.Revit.RevitCaches.GetActiveBIM360CacheDirectory(2025, iniPath);
            Assert.That(active, Is.EqualTo(Path.GetFullPath(cacheDir)));
        }

        [Test()]
        public void GetActiveBIM360CacheDirectory_FallsBackWhenCustomMissing() {
            var missingDir = Path.Combine(_tempRoot, "does-not-exist");
            var iniPath = WriteIni($"[CloudModelCache]\nCacheLocation={missingDir}\n");

            var active = pyRevitLabs.TargetApps.Revit.RevitCaches.GetActiveBIM360CacheDirectory(2024, iniPath);
            var expected = pyRevitLabs.TargetApps.Revit.RevitCaches.GetBIM360CacheDirectory(2024);
            Assert.That(active, Is.EqualTo(expected));
        }

        [Test()]
        public void GetActiveBIM360CacheDirectory_Pre2024_UsesDefault() {
            var cacheDir = Path.Combine(_tempRoot, "cache2023");
            Directory.CreateDirectory(cacheDir);
            var iniPath = WriteIni($"[CloudModelCache]\nCacheLocation={cacheDir}\n");

            var active = pyRevitLabs.TargetApps.Revit.RevitCaches.GetActiveBIM360CacheDirectory(2023, iniPath);
            var expected = pyRevitLabs.TargetApps.Revit.RevitCaches.GetBIM360CacheDirectory(2023);
            Assert.That(active, Is.EqualTo(expected));
        }

        private string WriteIni(string contents, string fileName = "Revit.ini") {
            var path = Path.Combine(_tempRoot, fileName);
            File.WriteAllText(path, contents);
            return path;
        }
    }
}
