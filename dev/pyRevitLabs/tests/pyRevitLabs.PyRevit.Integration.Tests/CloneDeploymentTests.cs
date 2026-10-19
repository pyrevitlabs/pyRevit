using System;
using System.IO;
using System.IO.Compression;
using LibGit2Sharp;
using Microsoft.VisualStudio.TestTools.UnitTesting;
using pyRevitLabs.Common;
using pyRevitLabs.Configurations.Ini;
using pyRevitLabs.PyRevit;

namespace pyRevitLabs.PyRevit.Integration.Tests {
    /// <summary>Exercises deployment against local archives and repositories without user configuration.</summary>
    [TestClass]
    [DoNotParallelize]
    [TestCategory("HostFree")]
    [TestCategory("Integration")]
    public class PyRevitTests {
        private string _root;
        private string _source;
        private string _archive;
        private string _previousConfigRoot;
        private string _previousScope;
        private string _previousMachineRoot;
        private string _previousTemp;
        private string _previousLocalAppData;
        private const string CloneName = "FixtureClone";

        /// <summary>Creates a minimal clone and an isolated configuration directory.</summary>
        [TestInitialize]
        public void Setup() {
            _root = Path.Combine(Path.GetTempPath(), "pyrevit-deploy-" + Guid.NewGuid().ToString("N"));
            _source = Path.Combine(_root, "source");
            Directory.CreateDirectory(Path.Combine(_source, "pyrevitlib", "pyrevit"));
            Directory.CreateDirectory(Path.Combine(_source, "bin"));
            File.WriteAllText(Path.Combine(_source, "pyrevitlib", "pyrevit", "version"), "7.0.0");
            File.WriteAllText(Path.Combine(_source, "pyRevitfile"), "[deployments]\ncore = ['bin', 'pyrevitlib', 'pyRevitfile']\n");
            _archive = Path.Combine(_root, "image-" + Guid.NewGuid().ToString("N") + ".zip");
            ZipFile.CreateFromDirectory(_source, _archive);
            _previousConfigRoot = Environment.GetEnvironmentVariable(PyRevitLabsConsts.PyRevitPathOverrideEnvVar);
            _previousMachineRoot = Environment.GetEnvironmentVariable(PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar);
            _previousScope = Environment.GetEnvironmentVariable(PyRevitInstallScope.ConfigScopeEnvVar);
            _previousTemp = Environment.GetEnvironmentVariable("TEMP");
            _previousLocalAppData = Environment.GetEnvironmentVariable("LOCALAPPDATA");
            Environment.SetEnvironmentVariable(PyRevitLabsConsts.PyRevitPathOverrideEnvVar, Path.Combine(_root, "config"));
            Environment.SetEnvironmentVariable(PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar, Path.Combine(_root, "machine"));
            Environment.SetEnvironmentVariable(PyRevitInstallScope.ConfigScopeEnvVar, "user");
            PyRevitInstallScope.ClearCachedInstallScope();
            PyRevitConfigService.Reload();
        }

        /// <summary>Restores configuration discovery and removes fixture files.</summary>
        [TestCleanup]
        public void Cleanup() {
            try {
                PyRevitConfigService.Reload();
            }
            finally {
                Environment.SetEnvironmentVariable(PyRevitLabsConsts.PyRevitPathOverrideEnvVar, _previousConfigRoot);
                Environment.SetEnvironmentVariable(PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar, _previousMachineRoot);
                Environment.SetEnvironmentVariable(PyRevitInstallScope.ConfigScopeEnvVar, _previousScope);
                Environment.SetEnvironmentVariable("TEMP", _previousTemp);
                Environment.SetEnvironmentVariable("LOCALAPPDATA", _previousLocalAppData);
                PyRevitInstallScope.ClearCachedInstallScope();
                FixtureDirectory.Delete(_root);
            }
        }

        /// <summary>Expands environment variables before creating deployment staging directories.</summary>
        [TestMethod]
        public void DeployFromImage_UsesExpandedTempForStaging() {
            var localAppData = Path.Combine(_root, "LocalAppData");
            Directory.CreateDirectory(localAppData);
            Environment.SetEnvironmentVariable("LOCALAPPDATA", localAppData);
            Environment.SetEnvironmentVariable("TEMP", "%LOCALAPPDATA%\\Temp");
            var destination = Path.Combine(_root, "expanded-temp-clone");

            PyRevitClones.DeployFromImage(CloneName, deploymentName: "core", branchName: null,
                imagePath: _archive, destPath: destination, installBinaries: false);

            Assert.IsTrue(Directory.Exists(Path.Combine(destination, "bin")));
            Assert.IsTrue(Directory.Exists(Path.Combine(destination, "pyrevitlib", "pyrevit")));
            var expandedTemp = CommonUtils.GetUserTempDirectory();
            Assert.IsFalse(expandedTemp.Contains("%"));
            Assert.IsTrue(Directory.Exists(expandedTemp));
        }

        /// <summary>Deploys a local image with full or reduced content.</summary>
        [DataTestMethod]
        [DataRow(null)]
        [DataRow("core")]
        public void DeployFromImage_RegistersRequestedDeployment(string deployment) {
            PyRevitClones.DeployFromImage(CloneName, deploymentName: deployment, branchName: "fixture",
                imagePath: _archive, destPath: Path.Combine(_root, "image"), installBinaries: false);
            var clone = PyRevitClones.GetRegisteredClone(CloneName);
            Assert.AreEqual("fixture", clone.Branch);
            Assert.IsTrue(File.Exists(Path.Combine(clone.ClonePath, "pyRevitfile")));
            if (deployment != null) Assert.AreEqual(deployment, clone.Deployment.Name);
        }

        /// <summary>Clones a local Git repository without downloading binary artifacts.</summary>
        [DataTestMethod]
        [DataRow("master")]
        [DataRow("develop")]
        public void DeployFromRepo_ChecksOutRequestedBranch(string branch) {
            Repository.Init(_source);
            using (var repository = new Repository(_source)) {
                Commands.Stage(repository, "*");
                var author = new Signature("Test", "test@example.invalid", DateTimeOffset.UtcNow);
                repository.Commit("fixture", author, author);
                if (repository.Head.FriendlyName != branch) repository.CreateBranch(branch);
            }
            PyRevitClones.DeployFromRepo(CloneName, branchName: branch, repoUrl: _source,
                destPath: Path.Combine(_root, "repo"), installBinaries: false);
            var clone = PyRevitClones.GetRegisteredClone(CloneName);
            Assert.IsTrue(clone.IsRepoDeploy);
            Assert.AreEqual(branch, clone.Branch);
        }

        /// <summary>Reduced deployments are explicitly unsupported for Git clones.</summary>
        [TestMethod]
        public void DeployFromRepo_WithDeployment_ThrowsNotImplemented() {
            Assert.ThrowsException<NotImplementedException>(() => PyRevitClones.DeployFromRepo(
                CloneName, deploymentName: "core", repoUrl: _source,
                destPath: Path.Combine(_root, "unsupported"), installBinaries: false));
        }

        /// <summary>Removing a clone registration preserves other clones and the checkout on disk.</summary>
        [TestMethod]
        public void UnregisterClone_PersistsRemovalAndPreservesOtherClones() {
            const string sourceCloneName = "SourceClone";
            var destination = Path.Combine(_root, "registered-clone");
            PyRevitClones.RegisterClone(sourceCloneName, _source);
            PyRevitClones.DeployFromImage(CloneName, imagePath: _archive,
                destPath: destination, installBinaries: false);

            PyRevitClones.UnregisterClone(PyRevitClones.GetRegisteredClone(CloneName));
            PyRevitConfigService.Reload();

            Assert.ThrowsException<PyRevitException>(() => PyRevitClones.GetRegisteredClone(CloneName));
            Assert.AreEqual(_source, PyRevitClones.GetRegisteredClone(sourceCloneName).ClonePath);
            Assert.IsTrue(Directory.Exists(destination));
        }
    }
}
