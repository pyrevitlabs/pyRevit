using System;
using System.IO;

using Microsoft.VisualStudio.TestTools.UnitTesting;

using PyRevitLoader;

namespace PyRevitLabs.PyRevit.Renderer.Tests {
    /// <summary>
    /// Guards the policy that keeps the WebView2 stack out of the host
    /// process default load context.
    ///
    /// The policy is the single place that knows which files the loader must
    /// leave alone, so that the loader and the deployment cannot drift apart.
    /// </summary>
    [TestClass]
    public class AssemblyLoadPolicyTests {
        private static readonly string[] WebView2StackFileNames = {
            "Microsoft.Web.WebView2.Core.dll",
            "Microsoft.Web.WebView2.Wpf.dll",
            "Microsoft.Web.WebView2.WinForms.dll",
            "WebView2Loader.dll",
            "pyRevitLabs.PyRevit.WebView2.dll",
        };

        [TestMethod]
        public void IsolatedOnNetCore_IsTrueForThisBuild() {
            Assert.IsTrue(AssemblyLoadPolicy.IsolatedOnNetCore);
        }

        [TestMethod]
        public void ShouldSkip_RejectsTheWebView2StackOnNetCore() {
            foreach (var fileName in WebView2StackFileNames) {
                var decision = AssemblyLoadPolicy.ShouldSkip(fileName);

                Assert.IsTrue(
                    decision.Skip,
                    "'" + fileName + "' must be skipped on .NET. " + decision.Reason);
            }
        }

        [TestMethod]
        public void ShouldSkip_AllowsTheWebView2StackOnNetFramework() {
            foreach (var fileName in WebView2StackFileNames) {
                var decision = AssemblyLoadPolicy.ShouldSkip(fileName, isolatedOnNetCore: false);

                Assert.IsFalse(
                    decision.Skip,
                    "'" + fileName + "' must not be skipped on .NET Framework. " + decision.Reason);
            }
        }

        [TestMethod]
        public void ShouldSkip_AllowsAssembliesOutsideTheWebView2Stack() {
            var decision = AssemblyLoadPolicy.ShouldSkip("pyRevitLabs.Common.dll");

            Assert.IsFalse(decision.Skip, decision.Reason);
        }

        [TestMethod]
        public void ShouldSkip_MatchesTheFileNameOfAPath() {
            var decision = AssemblyLoadPolicy.ShouldSkip(
                Path.Combine("bin", "netcore", "Microsoft.Web.WebView2.Core.dll"));

            Assert.IsTrue(decision.Skip, decision.Reason);
        }

        [TestMethod]
        public void ShouldSkip_RejectsTheRuntimeOfAnotherRevitYear() {
            foreach (var fileName in new[] { "pyRevitLabs.PyRevit.Runtime.2025.dll", "pyRevitLabs.PyRevit.Runtime.2027.dll" }) {
                var decision = AssemblyLoadPolicy.ShouldSkip(
                    Path.Combine("bin", "netcore", "engines", "IPY342", fileName), "2026");

                Assert.IsTrue(decision.Skip, "'" + fileName + "' must be skipped in Revit 2026. " + decision.Reason);
            }
        }

        [TestMethod]
        public void ShouldSkip_AllowsTheHostYearRuntimeAndSharedRuntime() {
            foreach (var fileName in new[] { "pyRevitLabs.PyRevit.Runtime.2026.dll", "pyRevitLabs.PyRevit.Runtime.Shared.dll" }) {
                var decision = AssemblyLoadPolicy.ShouldSkip(fileName, "2026");

                Assert.IsFalse(decision.Skip, "'" + fileName + "' must load in Revit 2026. " + decision.Reason);
            }
        }

        [TestMethod]
        public void ShouldSkip_WithHostYearStillRejectsTheWebView2Stack() {
            var decision = AssemblyLoadPolicy.ShouldSkip("Microsoft.Web.WebView2.Core.dll", "2026");

            Assert.IsTrue(decision.Skip, decision.Reason);
        }

        [TestMethod]
        public void ShouldSkip_WithoutRuntimeYearKeepsEveryRuntime() {
            foreach (var runtimeYear in new[] { null, "" }) {
                var decision = AssemblyLoadPolicy.ShouldSkip("pyRevitLabs.PyRevit.Runtime.2021.dll", runtimeYear);

                Assert.IsFalse(decision.Skip, decision.Reason);
            }
        }

        [TestMethod]
        public void GetRuntimeYear_ReadsOnlyPerYearRuntimes() {
            Assert.AreEqual("2025", AssemblyLoadPolicy.GetRuntimeYear("pyRevitLabs.PyRevit.Runtime.2025"));
            Assert.AreEqual(
                "2021",
                AssemblyLoadPolicy.GetRuntimeYear(Path.Combine("engines", "IPY342", "pyRevitLabs.PyRevit.Runtime.2021.dll")));
            Assert.IsNull(AssemblyLoadPolicy.GetRuntimeYear("pyRevitLabs.PyRevit.Runtime.Shared"));
            Assert.IsNull(AssemblyLoadPolicy.GetRuntimeYear("pyRevitLabs.PyRevit.Runtime."));
            Assert.IsNull(AssemblyLoadPolicy.GetRuntimeYear("pyRevitLabs.PyRevit"));
            Assert.IsNull(AssemblyLoadPolicy.GetRuntimeYear(null));
        }

        [TestMethod]
        public void Loader_FiltersRuntimesByHostYear() {
            var source = File.ReadAllText(
                Path.Combine(AppContext.BaseDirectory, "Sources", "PyRevitLoaderApplication.cs"));

            StringAssert.Contains(source, "ControlledApplication.VersionNumber");
        }

        [TestMethod]
        public void Runner_KeepsTheRuntimeItIsCompiledAgainst() {
            var source = File.ReadAllText(
                Path.Combine(AppContext.BaseDirectory, "Sources", "PyRevitRunnerApplication.cs"));

            StringAssert.Contains(source, "GetReferencedAssemblies()");
            StringAssert.Contains(source, "AssemblyLoadPolicy.GetRuntimeYear");
            Assert.IsFalse(
                source.Contains("VersionNumber"),
                "The runner binds to the runtime of the Revit year it was compiled against, not the host year.");
        }

        [TestMethod]
        public void Loader_UsesTheSharedPolicy() {
            var source = File.ReadAllText(
                Path.Combine(AppContext.BaseDirectory, "Sources", "PyRevitLoaderApplication.cs"));

            StringAssert.Contains(source, "AssemblyLoadPolicy.ShouldSkip");
            Assert.IsFalse(
                source.Contains("Microsoft.Web.WebView2.Core.dll"),
                "The file names of the isolated stack belong to the shared policy, not to the loader.");
        }
    }
}
