using System;
using System.IO;

using NUnit.Framework;

using pyRevitLabs.Common;
using pyRevitLabs.Configurations.Ini;
using pyRevitLabs.PyRevit;

namespace pyRevitLabs.PyRevit.Integration.Tests {
    /// <summary>Tests seeding the machine-wide configuration from the active configuration.</summary>
    [TestFixture]
    [FixtureLifeCycle(LifeCycle.InstancePerTestCase)]
    [NonParallelizable]
    [Category("HostFree")]
    [Category("Integration")]
    public class PyRevitConfigsSeedTests {
        private const string ConfigContent = "[core]\r\nuserlocale = en_us\r\n";

        private string _tempRoot;
        private string _previousPyRevitPathOverride;
        private string _previousProgramDataPathOverride;
        private string _previousConfigScopeOverride;

        [SetUp]
        public void Setup() {
            _tempRoot = Path.Combine(Path.GetTempPath(), "pyRevitConfigsSeed_" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(_tempRoot);
            _previousPyRevitPathOverride = Environment.GetEnvironmentVariable(PyRevitLabsConsts.PyRevitPathOverrideEnvVar);
            _previousProgramDataPathOverride = Environment.GetEnvironmentVariable(PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar);
            _previousConfigScopeOverride = Environment.GetEnvironmentVariable(PyRevitInstallScope.ConfigScopeEnvVar);
            ClearConfigState();
        }

        [TearDown]
        public void Cleanup() {
            ClearConfigState();
            Environment.SetEnvironmentVariable(
                PyRevitLabsConsts.PyRevitPathOverrideEnvVar,
                _previousPyRevitPathOverride);
            Environment.SetEnvironmentVariable(
                PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar,
                _previousProgramDataPathOverride);
            Environment.SetEnvironmentVariable(
                PyRevitInstallScope.ConfigScopeEnvVar,
                _previousConfigScopeOverride);
            PyRevitInstallScope.ClearCachedInstallScope();
            PyRevitInstallScope.SetRuntimeInstallRoot(null);
            PyRevitConfigService.Reload();
            FixtureDirectory.Delete(_tempRoot);
        }

        [Test]
        public void TrySeedConfig_SameWritablePath_ReturnsTrueAndPreservesConfig() {
            SetScope(PyRevitInstallScope.ConfigScopeAllUsers);
            SetConfigRoots(_tempRoot, _tempRoot);
            string configFile = CreateConfig(_tempRoot, ConfigContent);

            Assert.That(Path.GetFullPath(PyRevitConsts.ConfigFilePath), Is.EqualTo(Path.GetFullPath(configFile)));
            Assert.That(Path.GetFullPath(PyRevitConsts.AdminConfigFilePath), Is.EqualTo(Path.GetFullPath(configFile)));
            Assert.That(PyRevitConfigs.TrySeedConfig(), Is.True);
            Assert.That(File.ReadAllText(configFile), Is.EqualTo(ConfigContent));
            Assert.That(IsReadOnly(configFile), Is.False);
        }

        [Test]
        public void TrySeedConfig_SameWritablePathWithLock_ReturnsTrueAndSetsReadOnly() {
            SetScope(PyRevitInstallScope.ConfigScopeAllUsers);
            SetConfigRoots(_tempRoot, _tempRoot);
            string configFile = CreateConfig(_tempRoot, ConfigContent);

            Assert.That(IsReadOnly(configFile), Is.False);
            Assert.That(PyRevitConfigs.TrySeedConfig(lockSeedConfig: true), Is.True);
            Assert.That(IsReadOnly(configFile), Is.True);
            Assert.That(File.ReadAllText(configFile), Is.EqualTo(ConfigContent));
        }

        [Test]
        public void TrySeedConfig_DifferentPath_CreatesTargetDirectoryAndCopiesConfig() {
            SetScope(PyRevitInstallScope.ConfigScopePerUser);
            string userRoot = Path.Combine(_tempRoot, "AppDataPyRevit");
            string machineRoot = Path.Combine(_tempRoot, "ProgramDataPyRevit");
            SetConfigRoots(userRoot, machineRoot);
            string configFile = CreateConfig(userRoot, ConfigContent);
            string machineConfigFile = Path.Combine(machineRoot, PyRevitLabsConsts.DefaultConfigsFileName);

            Assert.That(Directory.Exists(machineRoot), Is.False);
            Assert.That(PyRevitConfigs.TrySeedConfig(), Is.True);
            Assert.That(File.Exists(machineConfigFile), Is.True);
            Assert.That(File.ReadAllText(machineConfigFile), Is.EqualTo(ConfigContent));
            Assert.That(IsReadOnly(machineConfigFile), Is.False);
        }

        [Test]
        public void TrySeedConfig_DifferentPathWithLock_CopiesAndSetsReadOnly() {
            SetScope(PyRevitInstallScope.ConfigScopePerUser);
            string userRoot = Path.Combine(_tempRoot, "AppDataPyRevit");
            string machineRoot = Path.Combine(_tempRoot, "ProgramDataPyRevit");
            SetConfigRoots(userRoot, machineRoot);
            string configFile = CreateConfig(userRoot, ConfigContent);
            string machineConfigFile = Path.Combine(machineRoot, PyRevitLabsConsts.DefaultConfigsFileName);

            Assert.That(PyRevitConfigs.TrySeedConfig(lockSeedConfig: true), Is.True);
            Assert.That(File.ReadAllText(machineConfigFile), Is.EqualTo(ConfigContent));
            Assert.That(IsReadOnly(machineConfigFile), Is.True);
        }

        private void SetConfigRoots(string userRoot, string machineRoot) {
            Environment.SetEnvironmentVariable(PyRevitLabsConsts.PyRevitPathOverrideEnvVar, userRoot);
            Environment.SetEnvironmentVariable(PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar, machineRoot);
            PyRevitInstallScope.ClearCachedInstallScope();
            PyRevitConfigService.Reload();
        }

        private void SetScope(string scope) {
            Environment.SetEnvironmentVariable(PyRevitInstallScope.ConfigScopeEnvVar, scope);
            PyRevitInstallScope.ClearCachedInstallScope();
        }

        private static string CreateConfig(string configRoot, string content) {
            Directory.CreateDirectory(configRoot);
            string configFile = Path.Combine(configRoot, PyRevitLabsConsts.DefaultConfigsFileName);
            File.WriteAllText(configFile, content);
            return configFile;
        }

        private static bool IsReadOnly(string configFile) =>
            (File.GetAttributes(configFile) & FileAttributes.ReadOnly) != 0;

        private static void ClearConfigState() {
            PyRevitConfigService.Reload();
            PyRevitInstallScope.ClearCachedInstallScope();
            PyRevitInstallScope.SetRuntimeInstallRoot(null);
        }
    }
}
