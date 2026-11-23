using System.IO;
using NUnit.Framework;
using pyRevitExtensionParser;
using pyRevitLabs.Common;
using pyRevitLabs.Configurations;
using pyRevitLabs.Configurations.Ini;

namespace pyRevitExtensionParser.Tests
{
    /// <summary>
    /// Proves <see cref="MachineConfigIsolation"/> also hides a clone-local
    /// <c>pyRevit_config.ini</c>, which outranks the per-user config it redirects.
    /// </summary>
    /// <remarks>
    /// The clone is simulated by dropping <c>pyRevitfile</c> and a config into the
    /// folder of <c>pyRevitLabs.Common.dll</c>, the first directory the unisolated
    /// install-root search inspects.
    /// </remarks>
    [TestFixture]
    [Category("HostFree")]
    [Category("Integration")]
    [NonParallelizable]
    public class MachineConfigIsolationTests
    {
        private const string PlantedConfig = "[core]\nread_script_metadata = false\n";

        private string? _cloneMarker;
        private string? _cloneConfig;

        [SetUp]
        public void PlantCloneLocalConfig()
        {
            _cloneMarker = null;
            _cloneConfig = null;
            var assemblyDir = Path.GetDirectoryName(typeof(PyRevitInstallScope).Assembly.Location)!;
            var cloneMarker = Path.Combine(assemblyDir, "pyRevitfile");
            var cloneConfig = Path.Combine(assemblyDir, PyRevitLabsConsts.DefaultConfigsFileName);
            RemoveLeftoversOfAnInterruptedRun(cloneMarker, cloneConfig);
            if (File.Exists(cloneMarker) || File.Exists(cloneConfig))
                Assert.Inconclusive("The test output folder already holds a pyRevitfile or pyRevit_config.ini");

            _cloneMarker = cloneMarker;
            _cloneConfig = cloneConfig;
            File.WriteAllText(cloneMarker, string.Empty);
            File.WriteAllText(cloneConfig, PlantedConfig);
        }

        /// <summary>
        /// Deletes the marker and config a killed run left behind, recognised by their exact
        /// planted content; anything else in the output folder is left alone.
        /// </summary>
        private static void RemoveLeftoversOfAnInterruptedRun(string cloneMarker, string cloneConfig)
        {
            if (File.Exists(cloneMarker) && File.Exists(cloneConfig)
                && new FileInfo(cloneMarker).Length == 0
                && File.ReadAllText(cloneConfig) == PlantedConfig)
            {
                File.Delete(cloneMarker);
                File.Delete(cloneConfig);
            }
        }

        [TearDown]
        public void RemoveCloneLocalConfig()
        {
            if (_cloneMarker != null)
                File.Delete(_cloneMarker);
            if (_cloneConfig != null)
                File.Delete(_cloneConfig);
            ResetConfigState();
        }

        private static void ResetConfigState()
        {
            PyRevitConfigStore.Reset();
            PyRevitConfig.ClearCache();
            ExtensionParser.ClearAllCaches();
        }

        [Test]
        public void CloneLocalConfig_IsIgnoredAfterStoreReset()
        {
            ResetConfigState();

            var config = PyRevitConfig.Load();

            Assert.That(PyRevitInstallScope.GetLocalConfigFilePath(), Is.Null);
            Assert.That(config.ConfigPath, Is.EqualTo(PyRevitConfigPaths.UserConfigFilePath));
            Assert.That(config.ReadScriptMetadata, Is.True);
        }
    }
}
