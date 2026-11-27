using System;
using System.IO;

using NUnit.Framework;

using pyRevitLabs.Common;
using pyRevitLabs.Configurations.Ini;
using pyRevitLabs.PyRevit;

namespace pyRevitLabs.PyRevit.Integration.Tests {
    /// <summary>Tests how administrator pins in the machine config override the user's agent settings.</summary>
    [TestFixture]
    [FixtureLifeCycle(LifeCycle.InstancePerTestCase)]
    [NonParallelizable]
    [Category("HostFree")]
    [Category("Unit")]
    public class PyRevitConfigsAgentAdminTests {
        private string _tempRoot;
        private string _adminConfig;
        private string _previousPyRevitPathOverride;
        private string _previousConfigScopeOverride;

        /// <summary>Points the user config and the machine config at a temporary root.</summary>
        [SetUp]
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

        /// <summary>Restores the machine config path, environment overrides and install scope, then deletes the temporary root.</summary>
        [TearDown]
        public void Cleanup() {
            AgentAdminPolicy.OverrideMachineConfigPath(null);
            Environment.SetEnvironmentVariable(PyRevitLabsConsts.PyRevitPathOverrideEnvVar, _previousPyRevitPathOverride);
            Environment.SetEnvironmentVariable(PyRevitInstallScope.ConfigScopeEnvVar, _previousConfigScopeOverride);
            PyRevitInstallScope.SetRuntimeInstallRoot(null);
            PyRevitInstallScope.ClearCachedInstallScope();
            PyRevitConfigs.ReloadConfig();
            FixtureDirectory.Delete(_tempRoot);
        }

        private string UserConfigPath => Path.Combine(_tempRoot, PyRevitLabsConsts.DefaultConfigsFileName);

        private void WriteUserConfig(string content) {
            File.WriteAllText(UserConfigPath, content);
            PyRevitConfigs.ReloadConfig();
        }

        private void WriteAdminConfig(string content) => File.WriteAllText(_adminConfig, content);

        [Test]
        public void NothingPinned_UserValuesApply() {
            WriteUserConfig("[agent]\r\nenabled = true\r\npolicy = auto\r\nengine = cpython\r\nuser_skills = true\r\n");

            Assert.That(PyRevitConfigs.GetAgentEnabled(), Is.True);
            Assert.That(PyRevitConfigs.GetAgentPolicy(), Is.EqualTo("auto"));
            Assert.That(PyRevitConfigs.GetAgentEngine(), Is.EqualTo("cpython"));
            Assert.That(PyRevitConfigs.GetAgentUserSkillsEnabled(), Is.True);
            Assert.That(PyRevitConfigs.IsAgentKeyManaged(PyRevitConsts.ConfigsAgentEnabledKey), Is.False);
        }

        [Test]
        public void PinnedEnabledFalse_BeatsUserTrue() {
            WriteUserConfig("[agent]\r\nenabled = true\r\n");
            WriteAdminConfig("[agent.admin]\r\nenabled = false\r\n");

            Assert.That(PyRevitConfigs.GetAgentEnabled(), Is.False);
            Assert.That(PyRevitConfigs.IsAgentKeyManaged(PyRevitConsts.ConfigsAgentEnabledKey), Is.True);
        }

        [Test]
        public void PinnedEnabledMalformed_ReadsAsDisabled() {
            WriteUserConfig("[agent]\r\nenabled = true\r\n");
            WriteAdminConfig("[agent.admin]\r\nenabled = maybe\r\n");

            Assert.That(PyRevitConfigs.GetAgentEnabled(), Is.False);
        }

        [Test]
        public void BlankPins_FailClosed() {
            WriteUserConfig("[agent]\r\nenabled = true\r\npolicy = auto\r\nengine = cpython\r\nuser_skills = true\r\nreckless = true\r\n");
            WriteAdminConfig("[agent.admin]\r\nenabled =\r\npolicy =\r\nengine =\r\nuser_skills =\r\nreckless =\r\n");

            Assert.That(PyRevitConfigs.GetAgentEnabled(), Is.False);
            Assert.That(PyRevitConfigs.GetAgentPolicy(), Is.EqualTo("readonly"));
            Assert.That(PyRevitConfigs.GetAgentEngine(), Is.EqualTo("ironpython"));
            Assert.That(PyRevitConfigs.GetAgentUserSkillsEnabled(), Is.False);
            Assert.That(PyRevitConfigs.GetAgentReckless(), Is.False);
            Assert.That(PyRevitConfigs.IsAgentKeyManaged(PyRevitConsts.ConfigsAgentEnabledKey), Is.True);
        }

        [Test]
        public void GetAdminConfigFolderRisk_WhenTheFolderDoesNotExist_ReturnsNull() {
            AgentAdminPolicy.OverrideMachineConfigPath(Path.Combine(_tempRoot, "absent", "pyRevit_config.ini"));

            Assert.That(PyRevitConfigs.GetAdminConfigFolderRisk(), Is.Null);
        }

        [Test]
        public void PinnedEngine_BeatsUserEngine() {
            WriteUserConfig("[agent]\r\nengine = cpython\r\n");
            WriteAdminConfig("[agent.admin]\r\nengine = ironpython\r\n");

            Assert.That(PyRevitConfigs.GetAgentEngine(), Is.EqualTo("ironpython"));
        }

        [Test]
        public void PinnedUserSkillsFalse_BeatsUserTrue() {
            WriteUserConfig("[agent]\r\nuser_skills = true\r\n");
            WriteAdminConfig("[agent.admin]\r\nuser_skills = false\r\n");

            Assert.That(PyRevitConfigs.GetAgentUserSkillsEnabled(), Is.False);
        }

        [Test]
        public void PinnedRecklessFalse_BeatsUserTrue() {
            WriteUserConfig("[agent]\r\nreckless = true\r\n");
            WriteAdminConfig("[agent.admin]\r\nreckless = false\r\n");

            Assert.That(PyRevitConfigs.GetAgentReckless(), Is.False);
            Assert.That(PyRevitConfigs.IsAgentKeyManaged(PyRevitConsts.ConfigsAgentRecklessKey), Is.True);
        }

        [Test]
        public void PinnedRecklessMalformed_ReadsAsOff() {
            WriteUserConfig("[agent]\r\nreckless = true\r\n");
            WriteAdminConfig("[agent.admin]\r\nreckless = maybe\r\n");

            Assert.That(PyRevitConfigs.GetAgentReckless(), Is.False);
        }

        [Test]
        public void SetAgentReckless_WhenPinned_Throws() {
            WriteUserConfig("[agent]\r\n");
            WriteAdminConfig("[agent.admin]\r\nreckless = false\r\n");

            Assert.Throws<PyRevitSettingManagedException>(() => PyRevitConfigs.SetAgentReckless(true));
        }

        [Test]
        public void PolicyCeiling_CapsAMorePermissiveUserPolicy() {
            WriteUserConfig("[agent]\r\npolicy = auto\r\n");
            WriteAdminConfig("[agent.admin]\r\npolicy = ask\r\n");

            Assert.That(PyRevitConfigs.GetAgentPolicy(), Is.EqualTo("ask"));
        }

        [Test]
        public void PolicyCeiling_KeepsAStricterUserPolicy() {
            WriteUserConfig("[agent]\r\npolicy = readonly\r\n");
            WriteAdminConfig("[agent.admin]\r\npolicy = ask\r\n");

            Assert.That(PyRevitConfigs.GetAgentPolicy(), Is.EqualTo("readonly"));
        }

        [Test]
        public void PolicyCeilingMalformed_ReadsAsReadOnly() {
            WriteUserConfig("[agent]\r\npolicy = auto\r\n");
            WriteAdminConfig("[agent.admin]\r\npolicy = whatever\r\n");

            Assert.That(PyRevitConfigs.GetAgentPolicy(), Is.EqualTo("readonly"));
            Assert.That(PyRevitConfigs.GetAgentPolicyCeiling(), Is.EqualTo("readonly"));
        }

        [Test]
        public void PlainAgentSectionInMachineConfig_DoesNotLock() {
            WriteUserConfig("[agent]\r\nenabled = true\r\n");
            WriteAdminConfig("[agent]\r\nenabled = false\r\n");

            Assert.That(PyRevitConfigs.GetAgentEnabled(), Is.True);
            Assert.That(PyRevitConfigs.IsAgentKeyManaged(PyRevitConsts.ConfigsAgentEnabledKey), Is.False);
        }

        [Test]
        public void SetAgentEnabled_WhenPinned_ThrowsAndLeavesUserConfigUntouched() {
            WriteUserConfig("[agent]\r\nenabled = false\r\n");
            WriteAdminConfig("[agent.admin]\r\nenabled = false\r\n");
            string before = File.ReadAllText(UserConfigPath);

            Assert.Throws<PyRevitSettingManagedException>(() => PyRevitConfigs.SetAgentEnabled(true));
            Assert.That(File.ReadAllText(UserConfigPath), Is.EqualTo(before));
        }

        [Test]
        public void SetAgentEngine_WhenPinned_Throws() {
            WriteUserConfig("[agent]\r\n");
            WriteAdminConfig("[agent.admin]\r\nengine = ironpython\r\n");

            Assert.Throws<PyRevitSettingManagedException>(() => PyRevitConfigs.SetAgentEngine("cpython"));
        }

        [Test]
        public void SetAgentUserSkillsEnabled_WhenPinned_Throws() {
            WriteUserConfig("[agent]\r\n");
            WriteAdminConfig("[agent.admin]\r\nuser_skills = false\r\n");

            Assert.Throws<PyRevitSettingManagedException>(() => PyRevitConfigs.SetAgentUserSkillsEnabled(true));
        }

        [Test]
        public void SetAgentPolicy_AboveTheCeiling_Throws() {
            WriteUserConfig("[agent]\r\n");
            WriteAdminConfig("[agent.admin]\r\npolicy = ask\r\n");

            Assert.Throws<PyRevitSettingManagedException>(() => PyRevitConfigs.SetAgentPolicy("auto"));
        }

        [Test]
        public void LockAgentKey_PinsTheValueForGetters() {
            WriteUserConfig("[agent]\r\nenabled = true\r\nengine = cpython\r\n");

            PyRevitConfigs.LockAgentKey(PyRevitConsts.ConfigsAgentEnabledKey, "False");
            PyRevitConfigs.LockAgentKey(PyRevitConsts.ConfigsAgentEngineKey, "IronPython");

            Assert.That(PyRevitConfigs.GetAgentEnabled(), Is.False);
            Assert.That(PyRevitConfigs.GetAgentEngine(), Is.EqualTo("ironpython"));
        }

        [Test]
        public void LockAgentKey_InvalidValue_Throws() {
            Assert.Throws<PyRevitException>(() => PyRevitConfigs.LockAgentKey(PyRevitConsts.ConfigsAgentEnabledKey, "maybe"));
            Assert.Throws<PyRevitException>(() => PyRevitConfigs.LockAgentKey(PyRevitConsts.ConfigsAgentPolicyKey, "yolo"));
            Assert.Throws<PyRevitException>(() => PyRevitConfigs.LockAgentKey(PyRevitConsts.ConfigsAgentEngineKey, "lua"));
            Assert.Throws<PyRevitException>(() => PyRevitConfigs.LockAgentKey(PyRevitConsts.ConfigsAgentTabHighlightKey, "false"));
            Assert.That(File.Exists(_adminConfig), Is.False);
        }

        [Test]
        public void LockAgentKey_InvalidValue_ThrowsBeforeTouchingPermissions() {
            Assert.Throws<PyRevitException>(
                () => PyRevitConfigs.LockAgentKey(PyRevitConsts.ConfigsAgentEnabledKey, "maybe", restrictAccess: true));
            Assert.That(File.Exists(_adminConfig), Is.False);
        }

        [Test]
        public void LockAgentKey_EmptyMachineConfig_IsPinned() {
            WriteAdminConfig(string.Empty);

            PyRevitConfigs.LockAgentKey(PyRevitConsts.ConfigsAgentEnabledKey, "false");

            Assert.That(PyRevitConfigs.GetAgentPin(PyRevitConsts.ConfigsAgentEnabledKey), Is.EqualTo("false"));
        }

        [Test]
        public void UnlockAgentKey_RestoresTheUserValue() {
            WriteUserConfig("[agent]\r\nenabled = true\r\n");
            PyRevitConfigs.LockAgentKey(PyRevitConsts.ConfigsAgentEnabledKey, "false");
            Assert.That(PyRevitConfigs.GetAgentEnabled(), Is.False);

            PyRevitConfigs.UnlockAgentKey(PyRevitConsts.ConfigsAgentEnabledKey);

            Assert.That(PyRevitConfigs.GetAgentEnabled(), Is.True);
            Assert.That(PyRevitConfigs.IsAgentKeyManaged(PyRevitConsts.ConfigsAgentEnabledKey), Is.False);
        }

        [Test]
        public void UnlockAllAgentKeys_ClearsEveryPin() {
            WriteUserConfig("[agent]\r\nenabled = true\r\n");
            PyRevitConfigs.LockAgentKey(PyRevitConsts.ConfigsAgentEnabledKey, "false");
            PyRevitConfigs.LockAgentKey(PyRevitConsts.ConfigsAgentPolicyKey, "readonly");

            PyRevitConfigs.UnlockAllAgentKeys();

            Assert.That(PyRevitConfigs.GetAgentEnabled(), Is.True);
            Assert.That(PyRevitConfigs.GetAgentPolicyCeiling(), Is.Null);
        }

        [Test]
        public void SetAgentPolicy_AtOrBelowTheCeiling_IsSaved() {
            WriteUserConfig("[agent]\r\n");
            WriteAdminConfig("[agent.admin]\r\npolicy = ask\r\n");

            PyRevitConfigs.SetAgentPolicy("readonly");

            Assert.That(PyRevitConfigs.GetAgentPolicy(), Is.EqualTo("readonly"));
        }
    }
}
