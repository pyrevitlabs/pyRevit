using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
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

        /// <summary>
        /// Finds import statements that bind the vendored <c>requests</c> directly.
        /// </summary>
        /// <remarks>
        /// Text is scanned with string literals removed first, because a docstring or a sample
        /// block mentioning <c>import requests</c> must not count, and because it would otherwise
        /// hide a real import that follows it on the same line. Dotted module names and
        /// backslash line continuations are handled because both are ordinary Python that this
        /// scan must not miss.
        /// </remarks>
        private static Regex[] BuildDirectImportPatterns()
        {
            string module = @"[A-Za-z_]\w*(?:\s*\.\s*[A-Za-z_]\w*)*(?:\s+as\s+[A-Za-z_]\w*)?";
            string other = module + @"(?:\s*,\s*" + module + @")*\s*,\s*";

            return new[]
            {
                new Regex(
                    @"^[ \t]*import[ \t]+(?!(?:pyrevit\.)?netrequests\b)(?:" + other + ")?"
                        + RequestsModule + @"\b",
                    RegexOptions.Multiline | RegexOptions.Compiled),
                new Regex(
                    @"^[ \t]*from[ \t]+" + RequestsModule + @"(?:\s*\.\s*[A-Za-z_]\w*)*[ \t]+import\b",
                    RegexOptions.Multiline | RegexOptions.Compiled),
            };
        }

        /// <summary>
        /// Removes comments and string literals, and joins backslash line continuations.
        /// </summary>
        /// <remarks>
        /// A docstring or sample block mentioning <c>import requests</c> must not count, and it
        /// must not hide a real import that follows on the same line either, so literals are
        /// blanked rather than skipped. Line continuations are joined first because
        /// <c>import os, \</c> followed by <c>requests</c> is one statement spanning two lines.
        /// </remarks>
        private static string StripStringLiteralsAndComments(string source)
        {
            string joined = Regex.Replace(source, @"\\\r?\n", " ");
            var stripped = new StringBuilder(joined.Length);
            int i = 0;
            while (i < joined.Length)
            {
                char c = joined[i];
                if (c == '#')
                {
                    while (i < joined.Length && joined[i] != '\n')
                        i++;
                }
                else if (c == '"' || c == '\'')
                {
                    char quote = c;
                    int quoteCount = i + 2 < joined.Length
                        && joined[i + 1] == quote && joined[i + 2] == quote ? 3 : 1;
                    i += quoteCount;
                    while (i < joined.Length)
                    {
                        if (joined[i] == '\\')
                        {
                            i += 2;
                            continue;
                        }

                        if (joined[i] != quote)
                        {
                            i++;
                            continue;
                        }

                        int run = 0;
                        while (i < joined.Length && joined[i] == quote)
                        {
                            run++;
                            i++;
                        }

                        if (run < quoteCount)
                            i = i - run + 1;
                        else
                            break;
                    }

                    stripped.Append('\n');
                }
                else
                {
                    stripped.Append(c);
                    i++;
                }
            }

            return stripped.ToString();
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
                string source = StripStringLiteralsAndComments(File.ReadAllText(file));
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
                "import os.path, requests",
                "import os.path as p, requests",
                "from requests import get",
                "from requests.sessions import Session",
                "from requests.adapters import HTTPAdapter",
                "import requests  # engine test",
                "import os, \\\n    requests",
            };

            var shouldNotMatch = new[]
            {
                "from pyrevit.compat import requests",
                "import pyrevit.netrequests as requests",
                "requests = 1",
                "import requestsy",
                "print('import requests')",
                "\"\"\"Usage:\n    import requests\n\"\"\"",
                "def f():\n    '''\n    import requests\n    '''",
            };

            Assert.Multiple(() => {
                foreach (string source in shouldMatch)
                {
                    string stripped = StripStringLiteralsAndComments(source);
                    Assert.That(DirectRequestsImports.Any(p => p.IsMatch(stripped)), Is.True,
                        "should have been flagged: " + source);
                }

                foreach (string source in shouldNotMatch)
                {
                    string stripped = StripStringLiteralsAndComments(source);
                    Assert.That(DirectRequestsImports.Any(p => p.IsMatch(stripped)), Is.False,
                        "should not have been flagged: " + source);
                }
            });
        }
    }
}
