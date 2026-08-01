using System;
using System.IO;
using pyRevitLabs.PyRevit;
using pyRevitLabs.Configurations;
using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Ini;
using pyRevitLabs.Configurations.Ini.Extensions;

namespace pyRevitExtensionParserTester
{
    /// <summary>
    /// Get-after-set coverage for the CLI configuration facade (PyRevitConfigs).
    /// Each setter must write the intended section/key and the matching getter
    /// must read it back; a fresh read of the file proves the value reached
    /// disk, not just the live snapshot.
    ///
    /// The facade resolves its service through the process-wide store. These tests
    /// take that global over with a temp-file factory (the same SetFactory seam the
    /// store's own tests use), so they never touch real machine config. The store
    /// is static, so the fixture is non-parallel and resets the store around each
    /// test.
    /// </summary>
    [TestFixture]
    [NonParallelizable]
    public class PyRevitConfigsFacadeTests
    {
        private string _path;

        [SetUp]
        public void SetUp()
        {
            _path = Path.Combine(Path.GetTempPath(), $"facade_{Guid.NewGuid():N}.ini");
            File.WriteAllText(_path, "[core]\n");

            PyRevitConfigStore.SetFactory(_ =>
                new ConfigurationBuilder(false)
                    .AddIniConfiguration(_path, ConfigurationService.DefaultConfigurationName)
                    .Build());
            PyRevitConfigStore.Reload();
        }

        [TearDown]
        public void TearDown()
        {
            PyRevitConfigStore.Reload();
            if (_path != null && File.Exists(_path))
                File.Delete(_path);
        }

        [OneTimeTearDown]
        public void OneTimeTearDown() => PyRevitConfigStore.Reset();

        /// <summary>A fresh service over the temp file, to prove a write hit disk.</summary>
        private IConfigurationService ReadFromDisk() =>
            new ConfigurationBuilder(false)
                .AddIniConfiguration(_path, ConfigurationService.DefaultConfigurationName)
                .Build();

        // ---- core ----

        [Test]
        public void RocketMode_SetTrue_GetReturnsTrue_AndPersists()
        {
            PyRevitConfigs.SetRocketMode(true);

            Assert.IsTrue(PyRevitConfigs.GetRocketMode());
            Assert.AreEqual(true, ReadFromDisk().Core.RocketMode);
        }

        [Test]
        public void RocketMode_SetFalse_GetReturnsFalse()
        {
            PyRevitConfigs.SetRocketMode(false);

            Assert.IsFalse(PyRevitConfigs.GetRocketMode());
            Assert.AreEqual(false, ReadFromDisk().Core.RocketMode);
        }

        [Test]
        public void StartupLogTimeout_RoundTrips()
        {
            PyRevitConfigs.SetStartupLogTimeout(42);

            Assert.AreEqual(42, PyRevitConfigs.GetStartupLogTimeout());
            Assert.AreEqual(42, ReadFromDisk().Core.StartupLogTimeout);
        }

        [Test]
        public void FileLogging_RoundTrips()
        {
            PyRevitConfigs.SetFileLogging(true);

            Assert.IsTrue(PyRevitConfigs.GetFileLogging());
            Assert.AreEqual(true, ReadFromDisk().Core.FileLogging);
        }

        [Test] // Debug implies verbose, so both flags are written; the pair reads back as Debug.
        public void LoggingLevel_Debug_SetsBothFlags()
        {
            PyRevitConfigs.SetLoggingLevel(PyRevitLogLevels.Debug);

            Assert.AreEqual(PyRevitLogLevels.Debug, PyRevitConfigs.GetLoggingLevel());
            var disk = ReadFromDisk();
            Assert.AreEqual(true, disk.Core.Debug);
            Assert.AreEqual(true, disk.Core.Verbose);
        }

        [Test]
        public void LoggingLevel_Verbose_MapsToVerboseAndClearsDebug()
        {
            PyRevitConfigs.SetLoggingLevel(PyRevitLogLevels.Verbose);

            Assert.AreEqual(PyRevitLogLevels.Verbose, PyRevitConfigs.GetLoggingLevel());
            var disk = ReadFromDisk();
            Assert.AreEqual(false, disk.Core.Debug);
            Assert.AreEqual(true, disk.Core.Verbose);
        }

        // ---- routes ----

        [Test]
        public void RoutesServerPort_RoundTrips()
        {
            PyRevitConfigs.SetRoutesServerPort(12345);

            Assert.AreEqual(12345, PyRevitConfigs.GetRoutesServerPort());
            Assert.AreEqual(12345, ReadFromDisk().Routes.Port);
        }

        [Test]
        public void RoutesServerHost_RoundTrips()
        {
            PyRevitConfigs.SetRoutesServerHost("127.0.0.1");

            Assert.AreEqual("127.0.0.1", PyRevitConfigs.GetRoutesServerHost());
            Assert.AreEqual("127.0.0.1", ReadFromDisk().Routes.Host);
        }

        [Test]
        public void RoutesServer_EnableDisable_TogglesStatus()
        {
            PyRevitConfigs.EnableRoutesServer();
            Assert.IsTrue(PyRevitConfigs.GetRoutesServerStatus());

            PyRevitConfigs.DisableRoutesServer();
            Assert.IsFalse(PyRevitConfigs.GetRoutesServerStatus());
        }

        // ---- telemetry ----

        [Test]
        public void TelemetryStatus_RoundTrips()
        {
            PyRevitConfigs.SetTelemetryStatus(true);

            Assert.IsTrue(PyRevitConfigs.GetTelemetryStatus());
            Assert.AreEqual(true, ReadFromDisk().Telemetry.TelemetryStatus);
        }

        [Test] // Large hex flags must persist verbatim as a string (no 32-bit overflow).
        public void AppTelemetryFlags_LargeHex_RoundTripsAsString()
        {
            PyRevitConfigs.SetAppTelemetryFlags("0x4000400004003");

            Assert.AreEqual("0x4000400004003", PyRevitConfigs.GetAppTelemetryFlags());
            Assert.AreEqual("0x4000400004003", ReadFromDisk().Telemetry.AppTelemetryEventFlags);
        }

        // ---- durability across a store rebuild ----

        [Test] // After a reload drops the cached service, the value is re-read from disk.
        public void SetValue_SurvivesStoreReload()
        {
            PyRevitConfigs.SetRocketMode(true);
            PyRevitConfigs.SetStartupLogTimeout(7);

            PyRevitConfigs.ReloadConfig();

            Assert.IsTrue(PyRevitConfigs.GetRocketMode());
            Assert.AreEqual(7, PyRevitConfigs.GetStartupLogTimeout());
        }
    }
}
