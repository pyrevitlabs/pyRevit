using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace PyRevitLabs.PyRevit.Renderer.Tests {
    /// <summary>
    /// Guards the deployment layout the WebView2 isolation depends on.
    ///
    /// On .NET the loader sweeps every assembly in the binary folder into the
    /// host process default load context. A WebView2 assembly sitting there
    /// binds pyRevit's newer wrapper against the core the host process
    /// already carries, which is what crashed Revit in pyRevit#3806. The
    /// stack therefore lives in the isolated folder, and only there.
    /// </summary>
    [TestClass]
    [TestCategory("HostFree")]
    [TestCategory("Integration")]
    public class DeploymentLayoutTests {
        private static readonly string[] WebView2StackFileNames = {
            "Microsoft.Web.WebView2.Core.dll",
            "Microsoft.Web.WebView2.Wpf.dll",
            "Microsoft.Web.WebView2.WinForms.dll",
            "WebView2Loader.dll",
            "pyRevitLabs.PyRevit.WebView2.dll",
        };

        [TestMethod]
        public void NetCoreBinFolder_DoesNotCarryTheWebView2Stack() {
            var binDirectory = RequireBuiltBinDirectory("netcore");

            var found = WebView2StackFileNames
                .Where(name => File.Exists(Path.Combine(binDirectory, name)))
                .ToList();

            Assert.AreEqual(
                0, found.Count,
                "The loader loads every assembly in the binary folder into the host process: "
                + string.Join(", ", found));
        }

        [TestMethod]
        public void NetCoreIsolatedFolder_CarriesTheWholeWebView2Stack() {
            var isolatedDirectory = Path.Combine(
                RequireBuiltBinDirectory("netcore"), "isolated");
            if (!Directory.Exists(isolatedDirectory))
                Assert.Inconclusive("The isolated folder was not deployed.");

            var missing = WebView2StackFileNames
                .Where(name => !File.Exists(Path.Combine(isolatedDirectory, name)))
                .ToList();

            Assert.AreEqual(
                0, missing.Count,
                "The isolated folder must carry the whole WebView2 stack: " + string.Join(", ", missing));
        }

        [TestMethod]
        public void NetFxBinFolder_StillCarriesTheWebView2Stack() {
            var binDirectory = RequireBuiltBinDirectory("netfx");

            var missing = new[] {
                "Microsoft.Web.WebView2.Core.dll",
                "Microsoft.Web.WebView2.Wpf.dll",
                "Microsoft.Web.WebView2.WinForms.dll",
                "pyRevitLabs.PyRevit.WebView2.dll",
            }
                .Where(name => !File.Exists(Path.Combine(binDirectory, name)))
                .ToList();

            Assert.AreEqual(
                0, missing.Count,
                "The .NET Framework runtime has no isolated load context, so the renderer stays "
                + "in the host process: " + string.Join(", ", missing));
        }

        private static string RequireBuiltBinDirectory(string netFolder) {
            var binDirectory = Path.Combine(RepositoryPaths.Root, "bin", netFolder);
            if (!Directory.Exists(binDirectory))
                Assert.Inconclusive(
                    "'" + binDirectory + "' does not exist. Build the solution before running "
                    + "the renderer tests.");

            return binDirectory;
        }
    }
}
