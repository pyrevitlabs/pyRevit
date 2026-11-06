using System.IO;
using NUnit.Framework;
using pyRevitExtensionParser;
using pyRevitLabs.Common;
using pyRevitLabs.Configurations;
using pyRevitLabs.Configurations.Ini;

namespace pyRevitExtensionParserTester
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
    [NonParallelizable]
    public class MachineConfigIsolationTests
    {
        private const string PlantedConfig = "[core]\nread_script_metadata = false\n";

        private string _cloneMarker;
        private string _cloneConfig;

        [SetUp]
        public void PlantCloneLocalConfig()
        {
            var assemblyDir = Path.GetDirectoryName(typeof(PyRevitInstallScope).Assembly.Location);
            _cloneMarker = Path.Combine(assemblyDir, "pyRevitfile");
            _cloneConfig = Path.Combine(assemblyDir, PyRevitLabsConsts.DefaultConfigsFileName);
            RemoveLeftoversOfAnInterruptedRun();
            if (File.Exists(_cloneMarker) || File.Exists(_cloneConfig))
            {
                _cloneMarker = null;
                _cloneConfig = null;
                Assert.Inconclusive("The test output folder already holds a pyRevitfile or pyRevit_config.ini");
            }

            File.WriteAllText(_cloneMarker, string.Empty);
            File.WriteAllText(_cloneConfig, PlantedConfig);
        }

        /// <summary>
        /// Deletes the marker and config a killed run left behind, recognised by their exact
        /// planted content; anything else in the output folder is left alone.
        /// </summary>
        private void RemoveLeftoversOfAnInterruptedRun()
        {
            if (File.Exists(_cloneMarker) && File.Exists(_cloneConfig)
                && new FileInfo(_cloneMarker).Length == 0
                && File.ReadAllText(_cloneConfig) == PlantedConfig)
            {
                File.Delete(_cloneMarker);
                File.Delete(_cloneConfig);
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
