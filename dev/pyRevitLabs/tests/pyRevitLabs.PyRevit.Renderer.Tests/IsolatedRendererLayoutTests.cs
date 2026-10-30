using System;
using System.IO;

using Microsoft.VisualStudio.TestTools.UnitTesting;

using PyRevitLabs.PyRevit.Runtime;

namespace PyRevitLabs.PyRevit.Renderer.Tests {
    /// <summary>
    /// Guards the discovery of the isolated renderer folder.
    ///
    /// The runtime assembly is deployed to an engine folder, and the isolated
    /// folder sits next to the engines. The search has to find the binary
    /// folder from there, and it has to fail with a diagnosable error when
    /// the installation does not look the way it is expected to.
    /// </summary>
    [TestClass]
    [TestCategory("HostFree")]
    [TestCategory("Integration")]
    public class IsolatedRendererLayoutTests {
        private string _root;

        [TestInitialize]
        public void SetUp() {
            _root = Path.Combine(
                Path.GetTempPath(),
                "pyrevit-renderer-layout-" + Guid.NewGuid().ToString("N"));
        }

        [TestCleanup]
        public void TearDown() {
            if (Directory.Exists(_root))
                Directory.Delete(_root, recursive: true);
        }

        [TestMethod]
        public void ResolveBinDirectory_StopsAtTheFolderThatHoldsTheEngines() {
            var engineDirectory = CreateEngineFolder();

            var binDirectory = IsolatedRendererLayout.ResolveBinDirectory(engineDirectory);

            Assert.AreEqual(Path.Combine(_root, "bin", "netcore"), binDirectory);
        }

        [TestMethod]
        public void ResolveIsolatedDirectory_FindsTheIsolatedFolderBesideTheEngines() {
            var engineDirectory = CreateEngineFolder();

            var isolatedDirectory = IsolatedRendererLayout.ResolveIsolatedDirectory(engineDirectory);

            Assert.AreEqual(
                Path.Combine(_root, "bin", "netcore", "isolated"), isolatedDirectory);
        }

        [TestMethod]
        public void ResolveBinDirectory_ReportsAMissingLayout() {
            var driveRoot = Path.GetPathRoot(Path.GetTempPath());
            if (Directory.Exists(Path.Combine(driveRoot, IsolatedRendererLayout.EnginesFolderName)))
                Assert.Inconclusive(
                    "The drive root carries an 'engines' folder, so the layout probe cannot run.");

            var probe = Path.Combine(driveRoot, "pyrevit-renderer-layout-probe");

            var exception = Assert.ThrowsException<DirectoryNotFoundException>(
                () => IsolatedRendererLayout.ResolveBinDirectory(probe));

            StringAssert.Contains(exception.Message, "pyRevit binary folder");
        }

        private string CreateEngineFolder() {
            var engineDirectory = Path.Combine(_root, "bin", "netcore", "engines", "IPY2712PR");
            Directory.CreateDirectory(engineDirectory);
            return engineDirectory;
        }
    }
}
