using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using NUnit.Framework;

namespace pyRevitExtensionParserTest
{
    /// <summary>
    /// Guards the rule that first-party scripts reach <c>requests</c> through
    /// <c>pyrevit.compat</c>, never by importing the vendored copy directly.
    /// </summary>
    /// <remarks>
    /// The vendored copy in site-packages reaches TLS through urllib3, which IronPython cannot
    /// drive: an HTTPS request dies with <c>bad ssl protocol type</c>.
    /// <c>pyrevit.compat.requests</c> resolves to the vendored copy under CPython and to the
    /// HttpClient-backed shim under IronPython, so scripts that go through it run on every engine.
    /// #3638.
    ///
    /// The scan covers every first-party script rather than the one file that was wrong, because
    /// the failure is silent: a direct import looks fine until it is run on the default engine.
    /// </remarks>
    [TestFixture]
    public class EnginePortableRequestsImportTests
    {
        private const string RequestsModule = "requests";

        private static readonly Regex[] DirectRequestsImports = BuildDirectImportPatterns();

        private static Regex[] BuildDirectImportPatterns()
        {
            return new[]
            {
                new Regex(
                    @"^[ \t]*import[ \t]+(?!(?:pyrevit\.)?netrequests\b)(?:[A-Za-z_]\w*[ \t]*,[ \tt]*)*"
                        + RequestsModule + @"\b",
                    RegexOptions.Multiline | RegexOptions.Compiled),
                new Regex(
                    @"^[ \t]*from[ \t]+" + RequestsModule + @"(?:\.[A-Za-z_]\w*)*[ \t]+import\b",
                    RegexOptions.Multiline | RegexOptions.Compiled),
            };
        }

        private static IEnumerable<string> PythonFilesUnder(string root)
        {
            if (!Directory.Exists(root))
                yield break;

            foreach (string file in Directory.EnumerateFiles(root, "*.py", SearchOption.AllDirectories))
                yield return file;
        }

        private static string ExtensionsRoot
        {
            get
            {
                return Path.GetFullPath(Path.Combine(
                    TestContext.CurrentContext.TestDirectory,
                    "..", "..", "..", "..", "..", "..", "extensions"));
            }
        }

        private static List<string> ScriptsImportingRequestsDirectly()
        {
            var offenders = new List<string>();
            foreach (string file in PythonFilesUnder(ExtensionsRoot))
            {
                string source = File.ReadAllText(file);
                if (DirectRequestsImports.Any(pattern => pattern.IsMatch(source)))
                    offenders.Add(file.Substring(ExtensionsRoot.Length)
                        .TrimStart(Path.DirectorySeparatorChar));
            }

            return offenders;
        }

        [Test]
        public void NoFirstPartyScriptImportsRequestsDirectly()
        {
            List<string> offenders = ScriptsImportingRequestsDirectly();

            Assert.That(offenders, Is.Empty,
                "these scripts import requests directly and will fail on IronPython; use "
                + "'from pyrevit.compat import requests' instead: "
                + string.Join(" | ", offenders));
        }

        [Test]
        public void DevToolsExtensionIsPresent()
        {
            Assert.That(Directory.Exists(ExtensionsRoot), Is.True,
                "extensions root not found at " + ExtensionsRoot);
        }

        [Test]
        public void DetectsEveryDirectImportForm()
        {
            var shouldMatch = new[]
            {
                "import requests",
                "    import requests",
                "import os, requests",
                "import os, sys, requests",
                "from requests import get",
                "from requests.sessions import Session",
                "from requests.adapters import HTTPAdapter",
            };

            var shouldNotMatch = new[]
            {
                "from pyrevit.compat import requests",
                "import pyrevit.netrequests as requests",
                "# import requests",
                "requests = 1",
                "import requestsy",
            };

            Assert.Multiple(() => {
                foreach (string source in shouldMatch)
                {
                    Assert.That(DirectRequestsImports.Any(p => p.IsMatch(source)), Is.True,
                        "should have been flagged: " + source);
                }

                foreach (string source in shouldNotMatch)
                {
                    Assert.That(DirectRequestsImports.Any(p => p.IsMatch(source)), Is.False,
                        "should not have been flagged: " + source);
                }
            });
        }
    }
}
