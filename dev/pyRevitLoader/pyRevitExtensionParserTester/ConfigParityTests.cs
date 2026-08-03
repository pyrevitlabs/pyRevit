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
    /// Holds the loader's config surface to the shared configuration service: for
    /// a canonical (JSON-encoded) file, every value the loader exposes must equal
    /// the service's typed section value.
    ///
    /// The loader projects the service through its own property layer, which adds
    /// fallback defaults and normalization. This pins that layer as a pass-through,
    /// so a property bound to the wrong section or key, or normalization that
    /// rewrites a value the file sets explicitly, surfaces as a mismatch.
    ///
    /// The CLI reads the same service and is covered along with it. The Python
    /// bridge decodes raw config strings on its own side; that decoding is covered
    /// by pyrevit.unittests.test_config_roundtrip.
    /// </summary>
    [TestFixture]
    public class ConfigParityTests
    {
        // Every value contradicts its section default, so an assertion cannot pass
        // on a property that never reaches the store and returns its fallback.
        private const string CanonicalIni =
            "[core]\n" +
            "rocketmode = false\n" +
            "startuplogtimeout = 42\n" +
            "user_locale = \"en_us\"\n" +
            "outputstylesheet = \"C:\\\\styles\\\\out.css\"\n" +
            "userextensions = [\"C:\\\\Tools\\\\ext1\",\"D:\\\\ext2\"]\n" +
            "\n" +
            "[telemetry]\n" +
            "active = true\n" +
            "utc_timestamps = false\n" +
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
        public void LoaderSurface_ProjectsSharedServiceValuesUnchanged()
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
