using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using NUnit.Framework;
using pyRevitExtensionParserTest;

namespace pyRevitExtensionParserTest
{
    /// <summary>
    /// First-party scripts must not import <c>requests</c> directly. The vendored copy in
    /// site-packages reaches TLS through urllib3, which IronPython cannot drive: an HTTPS request
    /// dies with <c>bad ssl protocol type</c>. <c>pyrevit.compat.requests</c> resolves to the
    /// vendored copy under CPython and to the HttpClient-backed shim under IronPython, so
    /// scripts that go through it run on every engine. #3638.
    /// </summary>
    [TestFixture]
    public class EnginePortableRequestsImportTests
    {
        private static readonly Regex DirectRequestsImport = new Regex(
            @"^\s*(?:import\s+requests\b|from\s+requests\s+import)",
            RegexOptions.Multiline | RegexOptions.Compiled);

        private static IEnumerable<string> PythonFilesUnder(string root) {
            if (!Directory.Exists(root))
                yield break;
            foreach (string file in Directory.EnumerateFiles(root, "*.py", SearchOption.AllDirectories))
                yield return file;
        }

        private static string ExtensionsRoot =>
            Path.GetFullPath(Path.Combine(TestContext.CurrentContext.TestDirectory,
                "..", "..", "..", "..", "..", "..", "extensions"));

        [Test]
        public void NoFirstPartyScriptImportsRequestsDirectly() {
            var offenders = new List<string>();
            foreach (string file in PythonFilesUnder(ExtensionsRoot)) {
                if (DirectRequestsImport.IsMatch(File.ReadAllText(file)))
                    offenders.Add(file.Substring(ExtensionsRoot.Length).TrimStart(Path.DirectorySeparatorChar));
            }

            Assert.That(offenders, Is.Empty,
                "these scripts import requests directly and will fail on IronPython; "
                + "use 'from pyrevit.compat import requests' instead: "
                + string.Join(" | ", offenders));
        }

        [Test]
        public void DevToolsExtensionIsPresent() {
            // Guards the test above: if the extension folder is not where we expect, the scan
            // finds nothing and passes for the wrong reason.
            Assert.That(Directory.Exists(ExtensionsRoot), Is.True,
                "extensions root not found at " + ExtensionsRoot);
        }
    }
}
