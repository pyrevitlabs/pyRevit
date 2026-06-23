using System;
using System.Collections.Generic;
using System.IO;
using pyRevitExtensionParser;
using pyRevitLabs.Configurations;
using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Ini.Extensions;

namespace pyRevitExtensionParserTester
{
    /// <summary>
    /// Guards against a fourth config reader ever diverging: the loader's
    /// PyRevitConfig adapter and the shared ConfigurationService must decode the
    /// same canonical (JSON-encoded) file into identical values. The CLI and
    /// Python engines read through the same ConfigurationService, so loader/service
    /// parity transitively covers all readers.
    /// </summary>
    [TestFixture]
    public class ConfigParityTests
    {
        private const string CanonicalIni =
            "[core]\n" +
            "rocketmode = true\n" +
            "startuplogtimeout = 10\n" +
            "user_locale = \"en_us\"\n" +
            "outputstylesheet = \"C:\\\\styles\\\\out.css\"\n" +
            "userextensions = [\"C:\\\\Tools\\\\ext1\",\"D:\\\\ext2\"]\n" +
            "\n" +
            "[telemetry]\n" +
            "active = true\n" +
            "utc_timestamps = true\n" +
            "telemetry_server_url = \"https://example.test/api/v2/scripts\"\n" +
            "apptelemetry_event_flags = \"0x4000400004003\"\n";

        private string _path;

        [SetUp]
        public void Setup()
        {
            _path = Path.Combine(Path.GetTempPath(), $"parity_{Guid.NewGuid():N}.ini");
            File.WriteAllText(_path, CanonicalIni);
        }

        [TearDown]
        public void Teardown()
        {
            if (_path != null && File.Exists(_path))
                File.Delete(_path);
        }

        [Test]
        public void LoaderAdapter_And_SharedService_DecodeIdentically()
        {
            var loader = PyRevitConfig.Load(_path);
            IConfigurationService service = new ConfigurationBuilder(false)
                .AddIniConfiguration(_path, ConfigurationService.DefaultConfigurationName)
                .Build();

            // core
            Assert.AreEqual(service.Core.RocketMode, loader.RocketMode, "rocketmode");
            Assert.AreEqual(service.Core.StartupLogTimeout, loader.StartupLogTimeout, "startuplogtimeout");
            Assert.AreEqual(service.Core.UserLocale, loader.UserLocale, "user_locale");
            Assert.AreEqual(service.Core.OutputStyleSheet, loader.OutputStyleSheet, "outputstylesheet");
            CollectionAssert.AreEqual(service.Core.UserExtensions!, loader.UserExtensionsList, "userextensions");

            // telemetry
            Assert.AreEqual(service.Telemetry.TelemetryStatus, loader.TelemetryState, "active");
            Assert.AreEqual(service.Telemetry.TelemetryUseUtcTimeStamps, loader.TelemetryUTCTimeStamps, "utc_timestamps");
            Assert.AreEqual(service.Telemetry.TelemetryServerUrl, loader.TelemetryServerUrl, "telemetry_server_url");
            Assert.AreEqual(service.Telemetry.AppTelemetryEventFlags, loader.AppTelemetryEventFlags, "apptelemetry_event_flags");
        }
    }
}
