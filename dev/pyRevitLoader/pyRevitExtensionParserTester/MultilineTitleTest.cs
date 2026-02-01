using NUnit.Framework;
using pyRevitExtensionParser;
using System;
using System.IO;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    public class MultilineTitleTest
    {
        private string _testDir;

        [SetUp]
        public void Setup()
        {
            _testDir = Path.Combine(Path.GetTempPath(), $"pyRevitMultilineTest_{Guid.NewGuid():N}");
            Directory.CreateDirectory(_testDir);
        }

        [TearDown]
        public void TearDown()
        {
            if (Directory.Exists(_testDir))
            {
                try
                {
                    Directory.Delete(_testDir, true);
                }
                catch
                {
                    // Ignore cleanup errors in tests
                }
            }
        }

        [Test]
        public void TestMultilineTitleWithEmptyLine_FoldedStyle()
        {
            // This is the exact format from Set Workset.pushbutton/bundle.yaml
            var bundleContent = @"title:
  ru: >-
    Задать

    раб. набор
  fr_fr: >-
    Active

    Sous-Projet
  en_us: >-
    Set

    Workset
  de_de: >-
    Set

    Workset
  chinese_s: ""设置\n工作集""
tooltip:
  en_us: Test tooltip
author: Test Author";

            var bundlePath = Path.Combine(_testDir, "bundle.yaml");
            File.WriteAllText(bundlePath, bundleContent);

            TestContext.Out.WriteLine("=== Testing Multiline Title with Empty Line (Folded Style) ===");
            TestContext.Out.WriteLine($"Bundle path: {bundlePath}");
            TestContext.Out.WriteLine($"Bundle content:\n{bundleContent}");

            var bundle = BundleParser.BundleYamlParser.Parse(bundlePath);

            TestContext.Out.WriteLine("\n=== Parsed Titles ===");
            foreach (var kvp in bundle.Titles)
            {
                TestContext.Out.WriteLine($"[{kvp.Key}]: '{kvp.Value.Replace("\n", "\\n")}'");
            }

            // Verify all titles were parsed correctly
            Assert.IsTrue(bundle.Titles.ContainsKey("ru"), "Should have ru title");
            Assert.IsTrue(bundle.Titles.ContainsKey("fr_fr"), "Should have fr_fr title");
            Assert.IsTrue(bundle.Titles.ContainsKey("en_us"), "Should have en_us title");
            Assert.IsTrue(bundle.Titles.ContainsKey("de_de"), "Should have de_de title");
            Assert.IsTrue(bundle.Titles.ContainsKey("chinese_s"), "Should have chinese_s title");

            // For folded style (>-), empty lines become paragraph breaks (single newline)
            Assert.That(bundle.Titles["en_us"], Does.Contain("Set"), "en_us title should contain 'Set'");
            Assert.That(bundle.Titles["en_us"], Does.Contain("Workset"), "en_us title should contain 'Workset'");
            
            // The title should have both "Set" and "Workset" separated by a single newline
            Assert.That(bundle.Titles["en_us"], Is.EqualTo("Set\nWorkset"), 
                $"Expected 'Set\\nWorkset' but got '{bundle.Titles["en_us"].Replace("\n", "\\n")}'");

            Assert.That(bundle.Titles["fr_fr"], Is.EqualTo("Active\nSous-Projet"),
                $"Expected 'Active\\nSous-Projet' but got '{bundle.Titles["fr_fr"].Replace("\n", "\\n")}'");

            Assert.That(bundle.Titles["ru"], Does.Contain("Задать"));
            Assert.That(bundle.Titles["ru"], Does.Contain("раб. набор"));

            // Chinese should have escaped newline processed
            Assert.That(bundle.Titles["chinese_s"], Is.EqualTo("设置\n工作集"));

            TestContext.Out.WriteLine("\n=== All Multiline Title Tests Passed! ===");
        }

        [Test]
        public void TestMultilineTitleWithEmptyLine_LiteralStyle()
        {
            // Test with literal style (|-) which should preserve exact line breaks including empty lines
            var bundleContent = @"title:
  en_us: |-
    Set

    Workset
  de_de: |-
    German

    Title
tooltip:
  en_us: Test tooltip
author: Test Author";

            var bundlePath = Path.Combine(_testDir, "bundle_literal.yaml");
            File.WriteAllText(bundlePath, bundleContent);

            TestContext.Out.WriteLine("=== Testing Multiline Title with Empty Line (Literal Style) ===");
            TestContext.Out.WriteLine($"Bundle content:\n{bundleContent}");

            var bundle = BundleParser.BundleYamlParser.Parse(bundlePath);

            TestContext.Out.WriteLine("\n=== Parsed Titles ===");
            foreach (var kvp in bundle.Titles)
            {
                TestContext.Out.WriteLine($"[{kvp.Key}]: '{kvp.Value.Replace("\n", "\\n")}'");
            }

            // Literal style should preserve empty lines as double newlines
            Assert.That(bundle.Titles["en_us"], Does.Contain("Set"));
            Assert.That(bundle.Titles["en_us"], Does.Contain("Workset"));
            
            // Expected: "Set\n\nWorkset" (with empty line preserved as double newline)
            Assert.That(bundle.Titles["en_us"], Is.EqualTo("Set\n\nWorkset"),
                $"Expected 'Set\\n\\nWorkset' but got '{bundle.Titles["en_us"].Replace("\n", "\\n")}'");

            TestContext.Out.WriteLine("\n=== Literal Style Test Passed! ===");
        }

        [Test]
        public void TestSimpleMultilineTitleNoEmptyLine()
        {
            // Test that normal multiline without empty lines still works
            var bundleContent = @"title:
  en_us: >-
    Set
    Workset
tooltip:
  en_us: Test tooltip
author: Test Author";

            var bundlePath = Path.Combine(_testDir, "bundle_simple.yaml");
            File.WriteAllText(bundlePath, bundleContent);

            TestContext.Out.WriteLine("=== Testing Simple Multiline Title (No Empty Line) ===");
            TestContext.Out.WriteLine($"Bundle content:\n{bundleContent}");

            var bundle = BundleParser.BundleYamlParser.Parse(bundlePath);

            TestContext.Out.WriteLine($"\n[en_us]: '{bundle.Titles["en_us"]}'");

            // Folded style without empty lines should join with spaces
            Assert.That(bundle.Titles["en_us"], Is.EqualTo("Set Workset"),
                $"Expected 'Set Workset' but got '{bundle.Titles["en_us"]}'");

            TestContext.Out.WriteLine("\n=== Simple Multiline Test Passed! ===");
        }
    }
}
