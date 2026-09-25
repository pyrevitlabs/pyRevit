using System;
using System.IO;

using Microsoft.VisualStudio.TestTools.UnitTesting;

using pyRevitLabs.Common;
using pyRevitLabs.Configurations.Ini;
using pyRevitLabs.PyRevit;

namespace pyRevitLabs.UnitTests {
    [TestClass]
    [DoNotParallelize]
    public class PyRevitConfigsSeedTests {
        private const string ConfigContent = "[core]\r\nuserlocale = en_us\r\n";

        private string _tempRoot;
        private string _previousPyRevitPathOverride;
        private string _previousProgramDataPathOverride;
        private string _previousConfigScopeOverride;

        [TestInitialize]
        public void Setup() {
            _tempRoot = Path.Combine(Path.GetTempPath(), "pyRevitConfigsSeed_" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(_tempRoot);
            _previousPyRevitPathOverride = Environment.GetEnvironmentVariable(PyRevitLabsConsts.PyRevitPathOverrideEnvVar);
            _previousProgramDataPathOverride = Environment.GetEnvironmentVariable(PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar);
            _previousConfigScopeOverride = Environment.GetEnvironmentVariable(PyRevitInstallScope.ConfigScopeEnvVar);
            ClearConfigState();
        }

        [TestCleanup]
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
            CommonUtils.DeleteDirectory(_tempRoot, verbose: false);
        }

        [TestMethod]
        public void TrySeedConfig_SameWritablePath_ReturnsTrueAndPreservesConfig() {
            SetScope(PyRevitInstallScope.ConfigScopeAllUsers);
            SetConfigRoots(_tempRoot, _tempRoot);
            string configFile = CreateConfig(_tempRoot, ConfigContent);

            Assert.AreEqual(Path.GetFullPath(configFile), Path.GetFullPath(PyRevitConsts.ConfigFilePath));
            Assert.AreEqual(Path.GetFullPath(configFile), Path.GetFullPath(PyRevitConsts.AdminConfigFilePath));
            Assert.IsTrue(PyRevitConfigs.TrySeedConfig());
            Assert.AreEqual(ConfigContent, File.ReadAllText(configFile));
            Assert.IsFalse(IsReadOnly(configFile));
        }

        [TestMethod]
        public void TrySeedConfig_SameWritablePathWithLock_ReturnsTrueAndSetsReadOnly() {
            SetScope(PyRevitInstallScope.ConfigScopeAllUsers);
            SetConfigRoots(_tempRoot, _tempRoot);
            string configFile = CreateConfig(_tempRoot, ConfigContent);

            Assert.IsFalse(IsReadOnly(configFile));
            Assert.IsTrue(PyRevitConfigs.TrySeedConfig(lockSeedConfig: true));
            Assert.IsTrue(IsReadOnly(configFile));
            Assert.AreEqual(ConfigContent, File.ReadAllText(configFile));
        }

        [TestMethod]
        public void TrySeedConfig_DifferentPath_CreatesTargetDirectoryAndCopiesConfig() {
            SetScope(PyRevitInstallScope.ConfigScopePerUser);
            string userRoot = Path.Combine(_tempRoot, "AppDataPyRevit");
            string machineRoot = Path.Combine(_tempRoot, "ProgramDataPyRevit");
            SetConfigRoots(userRoot, machineRoot);
            string configFile = CreateConfig(userRoot, ConfigContent);
            string machineConfigFile = Path.Combine(machineRoot, PyRevitLabsConsts.DefaultConfigsFileName);

            Assert.IsFalse(Directory.Exists(machineRoot));
            Assert.IsTrue(PyRevitConfigs.TrySeedConfig());
            Assert.IsTrue(File.Exists(machineConfigFile));
            Assert.AreEqual(ConfigContent, File.ReadAllText(machineConfigFile));
            Assert.IsFalse(IsReadOnly(machineConfigFile));
        }

        [TestMethod]
        public void TrySeedConfig_DifferentPathWithLock_CopiesAndSetsReadOnly() {
            SetScope(PyRevitInstallScope.ConfigScopePerUser);
            string userRoot = Path.Combine(_tempRoot, "AppDataPyRevit");
            string machineRoot = Path.Combine(_tempRoot, "ProgramDataPyRevit");
            SetConfigRoots(userRoot, machineRoot);
            string configFile = CreateConfig(userRoot, ConfigContent);
            string machineConfigFile = Path.Combine(machineRoot, PyRevitLabsConsts.DefaultConfigsFileName);

            Assert.IsTrue(PyRevitConfigs.TrySeedConfig(lockSeedConfig: true));
            Assert.AreEqual(ConfigContent, File.ReadAllText(machineConfigFile));
            Assert.IsTrue(IsReadOnly(machineConfigFile));
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
