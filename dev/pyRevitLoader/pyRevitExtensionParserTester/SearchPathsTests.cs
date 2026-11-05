using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using NUnit.Framework;
using pyRevitAssemblyBuilder.SessionManager;
using pyRevitExtensionParser;
using pyRevitExtensionParserTest.TestHelpers;

namespace pyRevitExtensionParserTester
{
    /// <summary>
    /// The search-path lists the loader hands to the runtimes that are not generated
    /// commands: an extension startup script, a session entry script, an event hook. Each
    /// assembles from sources that overlap, so every repeat that survives assembly puts a
    /// duplicate folder on <c>sys.path</c> - and on a duplicate the first match wins, which
    /// is how an out-of-date copy shadows a corrected one. #3687.
    /// </summary>
    [TestFixture]
    public class SearchPathsTests : TempFileTestBase
    {
        private static List<string> Repeated(IEnumerable<string> paths)
        {
            return paths
                .Where(p => !string.IsNullOrEmpty(p))
                .GroupBy(p => p, StringComparer.OrdinalIgnoreCase)
                .Where(g => g.Count() > 1)
                .Select(g => g.Key)
                .ToList();
        }

        // -------------------------------------------------------------------------
        // SearchPaths.DedupeKeepingFirstOccurrence - the rule every call site shares.
        // -------------------------------------------------------------------------

        [Test]
        public void Dedupe_CollapsesRepeats()
        {
            var result = SearchPaths.DedupeKeepingFirstOccurrence(
                new[] { "a", "b", "a", "c", "b" }).ToList();

            CollectionAssert.AreEqual(new[] { "a", "b", "c" }, result);
        }

        [Test]
        public void Dedupe_KeepsFirstOccurrenceOrder()
        {
            var result = SearchPaths.DedupeKeepingFirstOccurrence(
                new[] { "z", "a", "z", "a" }).ToList();

            CollectionAssert.AreEqual(new[] { "z", "a" }, result);
        }

        [Test]
        public void Dedupe_TreatsCaseOnlyDifferenceAsARepeat()
        {
            var result = SearchPaths.DedupeKeepingFirstOccurrence(
                new[] { @"C:\a\Lib", @"c:\a\lib" }).ToList();

            CollectionAssert.AreEqual(new[] { @"C:\a\Lib" }, result);
        }

        [Test]
        public void Dedupe_DropsEmptyEntries()
        {
            var result = SearchPaths.DedupeKeepingFirstOccurrence(
                new[] { "a", string.Empty, null, "a" }).ToList();

            CollectionAssert.AreEqual(new[] { "a" }, result);
        }

        // -------------------------------------------------------------------------
        // Hook search paths - a library extension listed twice is the overlap that
        // produced the duplicates before the dedupe.
        // -------------------------------------------------------------------------

        [Test]
        public void HookSearchPaths_AreDistinctWhenALibraryExtensionIsListedTwice()
        {
            var extDir = CreateSubDirectory("UiExt");
            Directory.CreateDirectory(Path.Combine(extDir, "lib"));

            var libRoot = CreateSubDirectory("Shared.lib");
            var nestedLib = Path.Combine(libRoot, "lib");
            Directory.CreateDirectory(nestedLib);

            var pyRoot = CreateSubDirectory("FakePyRevitRoot");
            Directory.CreateDirectory(Path.Combine(pyRoot, "pyrevitlib"));
            Directory.CreateDirectory(Path.Combine(pyRoot, "site-packages"));

            var duplicate = new ParsedExtension { Directory = libRoot, Name = "Shared" };
            var libs = new List<ParsedExtension> { duplicate, duplicate };

            var paths = new HookManager(new MockPythonLogger()).BuildHookSearchPaths(
                new ParsedExtension { Directory = extDir, Name = "UiExt" }, libs, pyRoot);

            CollectionAssert.IsEmpty(Repeated(paths), "repeated hook search path");
        }

        [Test]
        public void HookSearchPaths_KeepEveryDistinctFolder()
        {
            var extDir = CreateSubDirectory("UiExt");
            Directory.CreateDirectory(Path.Combine(extDir, "lib"));
            Directory.CreateDirectory(Path.Combine(extDir, "bin"));

            var libRoot = CreateSubDirectory("Shared.lib");
            var nestedLib = Path.Combine(libRoot, "lib");
            Directory.CreateDirectory(nestedLib);

            var pyRoot = CreateSubDirectory("FakePyRevitRoot");
            var pyrevitlib = Path.Combine(pyRoot, "pyrevitlib");
            var sitePackages = Path.Combine(pyRoot, "site-packages");
            Directory.CreateDirectory(pyrevitlib);
            Directory.CreateDirectory(sitePackages);

            var paths = new HookManager(new MockPythonLogger()).BuildHookSearchPaths(
                new ParsedExtension { Directory = extDir, Name = "UiExt" },
                new List<ParsedExtension> { new ParsedExtension { Directory = libRoot, Name = "Shared" } },
                pyRoot);

            var expected = new[]
            {
                Path.Combine(extDir, "lib"),
                Path.Combine(extDir, "bin"),
                libRoot,
                nestedLib,
                pyrevitlib,
                sitePackages
            };

            Assert.Multiple(() =>
            {
                foreach (var folder in expected)
                    Assert.That(paths.Select(Path.GetFullPath), Does.Contain(Path.GetFullPath(folder)));
            });
        }
    }
}
