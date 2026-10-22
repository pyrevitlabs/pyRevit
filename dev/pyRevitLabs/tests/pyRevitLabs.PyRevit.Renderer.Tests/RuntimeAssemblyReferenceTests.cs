using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;

using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace PyRevitLabs.PyRevit.Renderer.Tests {
    /// <summary>
    /// Guards the metadata references of the deployed runtime assemblies.
    ///
    /// A metadata reference is enough to make the default load context bind
    /// the WebView2 stack, no matter where the file sits on disk. The .NET
    /// runtime must therefore carry no reference to any WebView2 assembly at
    /// all, while the .NET Framework runtime keeps the one to the renderer it
    /// runs in process.
    ///
    /// The references are read from the metadata, not from loaded assemblies,
    /// so that reading them cannot change what the test process has bound.
    /// </summary>
    [TestClass]
    public class RuntimeAssemblyReferenceTests {
        private static readonly string[] NetCoreRuntimeVersions = { "2025", "2026", "2027" };
        private static readonly string[] NetFxRuntimeVersions = { "2021", "2022", "2023", "2024" };

        [TestMethod]
        public void NetCoreRuntime_HasNoWebView2Reference() {
            foreach (var version in NetCoreRuntimeVersions) {
                var references = GetReferencedAssemblyNames(RequireRuntimeAssembly("netcore", version));

                var webView2 = references
                    .Where(name => name.StartsWith("Microsoft.Web.WebView2", StringComparison.OrdinalIgnoreCase))
                    .ToList();

                Assert.AreEqual(
                    0, webView2.Count,
                    "The .NET runtime " + version + " must not reference the WebView2 stack: "
                    + string.Join(", ", webView2));
            }
        }

        [TestMethod]
        public void NetCoreRuntime_ReferencesTheRendererContract() {
            foreach (var version in NetCoreRuntimeVersions) {
                var references = GetReferencedAssemblyNames(RequireRuntimeAssembly("netcore", version));

                Assert.IsTrue(
                    references.Contains("pyRevitLabs.PyRevit.Renderer"),
                    "The .NET runtime " + version + " must reference the renderer contract.");
            }
        }

        [TestMethod]
        public void NetFxRuntime_ReferencesTheWebView2Renderer() {
            foreach (var version in NetFxRuntimeVersions) {
                var references = GetReferencedAssemblyNames(RequireRuntimeAssembly("netfx", version));

                Assert.IsTrue(
                    references.Contains("pyRevitLabs.PyRevit.WebView2"),
                    "The .NET Framework runtime " + version + " must reference the WebView2 renderer.");
            }
        }

        private static IReadOnlyList<string> GetReferencedAssemblyNames(string assemblyPath) {
            using var stream = File.OpenRead(assemblyPath);
            using var peReader = new PEReader(stream);
            var reader = peReader.GetMetadataReader();

            return reader.AssemblyReferences
                .Select(handle => reader.GetString(reader.GetAssemblyReference(handle).Name))
                .ToList();
        }

        private static string RequireRuntimeAssembly(string netFolder, string revitVersion) {
            var fileName = "pyRevitLabs.PyRevit.Runtime." + revitVersion + ".dll";
            var enginesDirectory = Path.Combine(RepositoryPaths.Root, "bin", netFolder, "engines");
            if (!Directory.Exists(enginesDirectory))
                Assert.Inconclusive(
                    "'" + enginesDirectory + "' does not exist. Build the solution before running "
                    + "the renderer tests.");

            var candidates = Directory
                .GetFiles(enginesDirectory, fileName, SearchOption.AllDirectories)
                .OrderBy(path => path, StringComparer.Ordinal)
                .ToList();
            if (candidates.Count == 0)
                Assert.Inconclusive(
                    "'" + fileName + "' was not deployed. Build the solution before running the "
                    + "renderer tests.");

            return candidates[0];
        }
    }
}
