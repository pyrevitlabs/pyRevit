using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

using Microsoft.VisualStudio.TestTools.UnitTesting;

using pyRevitLabs.Common;
using pyRevitLabs.Configurations.Ini;
using pyRevitLabs.Configurations.Sections;
using pyRevitLabs.PyRevit;

namespace pyRevitLabs.UnitTests {
    /// <summary>
    /// Regression tests for #4219: deleting one clone must not delete the user config shared by every clone.
    /// </summary>
    [TestClass]
    [DoNotParallelize]
    [TestCategory("HostFree")]
    [TestCategory("Unit")]
    public class PyRevitClonesDeleteTests {
        private string _tempRoot;
        private string _previousPyRevitPathOverride;
        private string _previousProgramDataPathOverride;

        /// <summary>Redirects pyRevit data folders to a temporary root.</summary>
        [TestInitialize]
        public void Setup() {
            _tempRoot = Path.Combine(Path.GetTempPath(), "pyRevitClonesDelete_" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(_tempRoot);
            _previousPyRevitPathOverride = Environment.GetEnvironmentVariable(PyRevitLabsConsts.PyRevitPathOverrideEnvVar);
            _previousProgramDataPathOverride = Environment.GetEnvironmentVariable(PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar);
            Environment.SetEnvironmentVariable(
                PyRevitLabsConsts.PyRevitPathOverrideEnvVar,
                Path.Combine(_tempRoot, "AppDataPyRevit"));
            Environment.SetEnvironmentVariable(
                PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar,
                Path.Combine(_tempRoot, "ProgramDataPyRevit"));
            PyRevitInstallScope.ClearCachedInstallScope();
            PyRevitInstallScope.SetRuntimeInstallRoot(null);
            PyRevitConfigService.Reload();
            Directory.CreateDirectory(PyRevitLabsConsts.PyRevitPath);
        }

        /// <summary>Restores environment overrides and the install scope, then deletes the temporary root.</summary>
        [TestCleanup]
        public void Cleanup() {
            PyRevitConfigService.Reload();
            PyRevitInstallScope.ClearCachedInstallScope();
            PyRevitInstallScope.SetRuntimeInstallRoot(null);
            Environment.SetEnvironmentVariable(
                PyRevitLabsConsts.PyRevitPathOverrideEnvVar,
                _previousPyRevitPathOverride);
            Environment.SetEnvironmentVariable(
                PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar,
                _previousProgramDataPathOverride);
            if (Directory.Exists(_tempRoot))
                CommonUtils.DeleteDirectory(_tempRoot);
        }

        private string CreateClone(string name) {
            var clonePath = Path.Combine(_tempRoot, name);
            Directory.CreateDirectory(Path.Combine(clonePath, "pyrevitlib", "pyrevit"));
            return clonePath;
        }

        private void RegisterTwoClones(out string firstPath, out string secondPath) {
            firstPath = CreateClone("first");
            secondPath = CreateClone("second");
            var cfg = PyRevitConfigs.GetConfigFile();
            cfg.SaveSection(new EnvironmentSection {
                Clones = new Dictionary<string, string> {
                    { "first", firstPath },
                    { "second", secondPath },
                }
            });
            cfg.SaveSection(new CoreSection { UserLocale = "de_de" });
        }

        /// <summary>Deleting one clone removes it and its registration but keeps the config file and the other clone.</summary>
        [TestMethod]
        public void Delete_SingleClone_KeepsConfigFileAndOtherClones() {
            RegisterTwoClones(out var firstPath, out var secondPath);
            var first = PyRevitClones.GetRegisteredClones().Single(c => c.Name == "first");

            PyRevitClones.Delete(first);

            Assert.IsFalse(Directory.Exists(firstPath));
            Assert.IsTrue(Directory.Exists(secondPath));
            Assert.IsTrue(File.Exists(PyRevitConsts.ConfigFilePath));
            PyRevitConfigService.Reload();
            CollectionAssert.AreEqual(
                new[] { "second" },
                PyRevitClones.GetRegisteredClones().Select(c => c.Name).ToArray());
            Assert.AreEqual("de_de", PyRevitConfigs.GetConfigFile().Core.UserLocale);
        }

        /// <summary>Deleting every clone without clearing configs keeps the config file.</summary>
        [TestMethod]
        public void DeleteAllClones_WithoutClearConfigs_KeepsConfigFile() {
            RegisterTwoClones(out var firstPath, out var secondPath);

            PyRevitClones.DeleteAllClones();

            Assert.IsFalse(Directory.Exists(firstPath));
            Assert.IsFalse(Directory.Exists(secondPath));
            Assert.IsTrue(File.Exists(PyRevitConsts.ConfigFilePath));
        }

        /// <summary>Deleting every clone with clearing configs also discards the user settings.</summary>
        [TestMethod]
        public void DeleteAllClones_WithClearConfigs_DiscardsUserSettings() {
            RegisterTwoClones(out var firstPath, out var secondPath);

            PyRevitClones.DeleteAllClones(clearConfigs: true);

            Assert.IsFalse(Directory.Exists(firstPath));
            Assert.IsFalse(Directory.Exists(secondPath));
            PyRevitConfigService.Reload();
            Assert.IsNull(PyRevitConfigs.GetConfigFile().Core.UserLocale);
            Assert.AreEqual(0, PyRevitClones.GetRegisteredClones().Count);
        }
    }
}
