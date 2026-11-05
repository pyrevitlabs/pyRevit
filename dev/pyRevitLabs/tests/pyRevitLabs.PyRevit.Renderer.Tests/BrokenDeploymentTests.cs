using System;
using System.IO;
using System.Windows.Threading;

using Microsoft.VisualStudio.TestTools.UnitTesting;

using PyRevitLabs.PyRevit.Renderer;
using PyRevitLabs.PyRevit.Runtime;
using pyRevitLabs.PyRevit.Runtime.Shared;

namespace PyRevitLabs.PyRevit.Renderer.Tests {
    /// <summary>
    /// Pins that a renderer which cannot be loaded degrades to the stand-in
    /// instead of failing the output window.
    ///
    /// A half-updated installation leaves an isolated folder that disagrees
    /// with the runtime: the folder holds an older renderer, a corrupt file, or
    /// no renderer at all. Constructing the window must survive all three,
    /// because the window outlives the renderer and a failure there would abort
    /// the script that opened it.
    /// </summary>
    [TestClass]
    public class BrokenDeploymentTests {
        [TestMethod]
        public void CreateIsolated_ReportsABrokenDeploymentWhenTheRendererIsMissing() {
            var directory = CreateScratchDirectory();

            AssertBrokenDeployment(directory);
        }

        [TestMethod]
        public void CreateIsolated_ReportsABrokenDeploymentWhenTheRendererIsNotAnAssembly() {
            var directory = CreateScratchDirectory();
            File.WriteAllText(
                Path.Combine(directory, "pyRevitLabs.PyRevit.WebView2.dll"),
                "not an assembly");

            AssertBrokenDeployment(directory);
        }

        [TestMethod]
        public void CreateIsolated_ReportsABrokenDeploymentWhenTheRendererMissesTheContract() {
            var directory = CreateScratchDirectory();
            File.Copy(
                typeof(BrokenDeploymentTests).Assembly.Location,
                Path.Combine(directory, "pyRevitLabs.PyRevit.WebView2.dll"));

            AssertBrokenDeployment(directory);
        }

        private static void AssertBrokenDeployment(string isolatedDirectory) {
            StaTestRunner.Run(() => {
                var context = new WebView2LoadContext(isolatedDirectory);
                using (var renderer = ScriptRendererProvider.CreateIsolated(
                    context, isolatedDirectory, Dispatcher.CurrentDispatcher)) {
                    Assert.AreEqual(
                        RendererFailure.BrokenDeployment,
                        renderer.Failure,
                        "A renderer that cannot be loaded must report a broken deployment.");
                    Assert.IsFalse(renderer.IsCoreReady);
                    Assert.IsFalse(renderer.IsDocumentReady);
                    Assert.IsTrue(
                        renderer.InitializationFailed,
                        "The stand-in must report that it never initialized, so output is not silently dropped.");
                    Assert.IsTrue(
                        renderer.ReadyTask.IsCompleted,
                        "The stand-in must not leave the owner waiting for a renderer.");
                }
            });
        }

        private static string CreateScratchDirectory() {
            var directory = Path.Combine(
                Path.GetTempPath(),
                "pyrevit-renderer-broken-" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(directory);
            AppDomain.CurrentDomain.ProcessExit += (sender, args) => {
                try {
                    Directory.Delete(directory, true);
                }
                catch {
                }
            };
            return directory;
        }
    }
}
