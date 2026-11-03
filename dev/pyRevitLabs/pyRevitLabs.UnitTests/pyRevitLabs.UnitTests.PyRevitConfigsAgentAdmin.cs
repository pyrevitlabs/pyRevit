using System;
using System.IO;

using Microsoft.VisualStudio.TestTools.UnitTesting;

using pyRevitLabs.Common;
using pyRevitLabs.Configurations.Ini;
using pyRevitLabs.PyRevit;

namespace pyRevitLabs.UnitTests {
    /// <summary>Tests how administrator pins in the machine config override the user's agent settings.</summary>
    [TestClass]
    [DoNotParallelize]
    public class PyRevitConfigsAgentAdminTests {
        private string _tempRoot;
        private string _adminConfig;
        private string _previousPyRevitPathOverride;
        private string _previousConfigScopeOverride;

        [TestInitialize]
        public void Setup() {
            _tempRoot = Path.Combine(Path.GetTempPath(), "pyRevitAgentAdmin_" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(_tempRoot);
            _adminConfig = Path.Combine(_tempRoot, "admin.ini");
            _previousPyRevitPathOverride = Environment.GetEnvironmentVariable(PyRevitLabsConsts.PyRevitPathOverrideEnvVar);
            _previousConfigScopeOverride = Environment.GetEnvironmentVariable(PyRevitInstallScope.ConfigScopeEnvVar);

            Environment.SetEnvironmentVariable(PyRevitLabsConsts.PyRevitPathOverrideEnvVar, _tempRoot);
            Environment.SetEnvironmentVariable(PyRevitInstallScope.ConfigScopeEnvVar, PyRevitInstallScope.ConfigScopePerUser);
            PyRevitInstallScope.SetRuntimeInstallRoot(_tempRoot);
            AgentAdminPolicy.OverrideMachineConfigPath(_adminConfig);
            PyRevitConfigs.ReloadConfig();
        }

        [TestCleanup]
        public void Cleanup() {
            AgentAdminPolicy.OverrideMachineConfigPath(null);
            Environment.SetEnvironmentVariable(PyRevitLabsConsts.PyRevitPathOverrideEnvVar, _previousPyRevitPathOverride);
            Environment.SetEnvironmentVariable(PyRevitInstallScope.ConfigScopeEnvVar, _previousConfigScopeOverride);
            PyRevitInstallScope.SetRuntimeInstallRoot(null);
            PyRevitInstallScope.ClearCachedInstallScope();
            PyRevitConfigs.ReloadConfig();
            CommonUtils.DeleteDirectory(_tempRoot, verbose: false);
        }

        private void WriteUserConfig(string content) {
            File.WriteAllText(Path.Combine(_tempRoot, PyRevitLabsConsts.DefaultConfigsFileName), content);
            PyRevitConfigs.ReloadConfig();
        }

        private void WriteAdminConfig(string content) => File.WriteAllText(_adminConfig, content);

        [TestMethod]
        public void NothingPinned_UserValuesApply() {
            WriteUserConfig("[agent]\r\nenabled = true\r\npolicy = auto\r\nengine = cpython\r\nuser_skills = true\r\n");

            Assert.IsTrue(PyRevitConfigs.GetAgentEnabled());
            Assert.AreEqual("auto", PyRevitConfigs.GetAgentPolicy());
            Assert.AreEqual("cpython", PyRevitConfigs.GetAgentEngine());
            Assert.IsTrue(PyRevitConfigs.GetAgentUserSkillsEnabled());
            Assert.IsFalse(PyRevitConfigs.IsAgentKeyManaged(PyRevitConsts.ConfigsAgentEnabledKey));
        }

        [TestMethod]
        public void PinnedEnabledFalse_BeatsUserTrue() {
            WriteUserConfig("[agent]\r\nenabled = true\r\n");
            WriteAdminConfig("[agent.admin]\r\nenabled = false\r\n");

            Assert.IsFalse(PyRevitConfigs.GetAgentEnabled());
            Assert.IsTrue(PyRevitConfigs.IsAgentKeyManaged(PyRevitConsts.ConfigsAgentEnabledKey));
        }

        [TestMethod]
        public void PinnedEnabledMalformed_ReadsAsDisabled() {
            WriteUserConfig("[agent]\r\nenabled = true\r\n");
            WriteAdminConfig("[agent.admin]\r\nenabled = maybe\r\n");

            Assert.IsFalse(PyRevitConfigs.GetAgentEnabled());
        }

        [TestMethod]
        public void PinnedEngine_BeatsUserEngine() {
            WriteUserConfig("[agent]\r\nengine = cpython\r\n");
            WriteAdminConfig("[agent.admin]\r\nengine = ironpython\r\n");

            Assert.AreEqual("ironpython", PyRevitConfigs.GetAgentEngine());
        }

        [TestMethod]
        public void PinnedUserSkillsFalse_BeatsUserTrue() {
            WriteUserConfig("[agent]\r\nuser_skills = true\r\n");
            WriteAdminConfig("[agent.admin]\r\nuser_skills = false\r\n");

            Assert.IsFalse(PyRevitConfigs.GetAgentUserSkillsEnabled());
        }

        [TestMethod]
        public void PolicyCeiling_CapsAMorePermissiveUserPolicy() {
            WriteUserConfig("[agent]\r\npolicy = auto\r\n");
            WriteAdminConfig("[agent.admin]\r\npolicy = ask\r\n");

            Assert.AreEqual("ask", PyRevitConfigs.GetAgentPolicy());
        }

        [TestMethod]
        public void PolicyCeiling_KeepsAStricterUserPolicy() {
            WriteUserConfig("[agent]\r\npolicy = readonly\r\n");
            WriteAdminConfig("[agent.admin]\r\npolicy = ask\r\n");

            Assert.AreEqual("readonly", PyRevitConfigs.GetAgentPolicy());
        }

        [TestMethod]
        public void PolicyCeilingMalformed_ReadsAsReadOnly() {
            WriteUserConfig("[agent]\r\npolicy = auto\r\n");
            WriteAdminConfig("[agent.admin]\r\npolicy = whatever\r\n");

            Assert.AreEqual("readonly", PyRevitConfigs.GetAgentPolicy());
            Assert.AreEqual("readonly", PyRevitConfigs.GetAgentPolicyCeiling());
        }

        [TestMethod]
        public void PlainAgentSectionInMachineConfig_DoesNotLock() {
            WriteUserConfig("[agent]\r\nenabled = true\r\n");
            WriteAdminConfig("[agent]\r\nenabled = false\r\n");

            Assert.IsTrue(PyRevitConfigs.GetAgentEnabled());
            Assert.IsFalse(PyRevitConfigs.IsAgentKeyManaged(PyRevitConsts.ConfigsAgentEnabledKey));
        }

        [TestMethod]
        public void SetAgentEnabled_WhenPinned_ThrowsAndLeavesUserConfigUntouched() {
            WriteUserConfig("[agent]\r\nenabled = false\r\n");
            WriteAdminConfig("[agent.admin]\r\nenabled = false\r\n");
            string before = File.ReadAllText(Path.Combine(_tempRoot, PyRevitLabsConsts.DefaultConfigsFileName));

            Assert.ThrowsException<PyRevitSettingManagedException>(() => PyRevitConfigs.SetAgentEnabled(true));
            Assert.AreEqual(before, File.ReadAllText(Path.Combine(_tempRoot, PyRevitLabsConsts.DefaultConfigsFileName)));
        }

        [TestMethod]
        public void SetAgentEngine_WhenPinned_Throws() {
            WriteUserConfig("[agent]\r\n");
            WriteAdminConfig("[agent.admin]\r\nengine = ironpython\r\n");

            Assert.ThrowsException<PyRevitSettingManagedException>(() => PyRevitConfigs.SetAgentEngine("cpython"));
        }

        [TestMethod]
        public void SetAgentUserSkillsEnabled_WhenPinned_Throws() {
            WriteUserConfig("[agent]\r\n");
            WriteAdminConfig("[agent.admin]\r\nuser_skills = false\r\n");

            Assert.ThrowsException<PyRevitSettingManagedException>(() => PyRevitConfigs.SetAgentUserSkillsEnabled(true));
        }

        [TestMethod]
        public void SetAgentPolicy_AboveTheCeiling_Throws() {
            WriteUserConfig("[agent]\r\n");
            WriteAdminConfig("[agent.admin]\r\npolicy = ask\r\n");

            Assert.ThrowsException<PyRevitSettingManagedException>(() => PyRevitConfigs.SetAgentPolicy("auto"));
        }

        [TestMethod]
        public void SetAgentPolicy_AtOrBelowTheCeiling_IsSaved() {
            WriteUserConfig("[agent]\r\n");
            WriteAdminConfig("[agent.admin]\r\npolicy = ask\r\n");

            PyRevitConfigs.SetAgentPolicy("readonly");

            Assert.AreEqual("readonly", PyRevitConfigs.GetAgentPolicy());
        }
    }
}
