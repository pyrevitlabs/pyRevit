using pyRevitExtensionParser;
using System.IO;
using NUnit.Framework;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    internal class HelpUrlTests
    {
        [Test]
        public void TestSingleLineHelpUrl()
        {
            var yamlContent = @"title:
  en_us: Test Command
help_url: https://github.com/pyrevitlabs/pyRevit
";
            var tempFile = Path.GetTempFileName();
            File.WriteAllText(tempFile, yamlContent);

            try
            {
                var bundle = BundleParser.BundleYamlParser.Parse(tempFile);

                TestContext.Out.WriteLine($"HelpUrl: {bundle.HelpUrl ?? "null"}");

                Assert.That(bundle.HelpUrl, Is.EqualTo("https://github.com/pyrevitlabs/pyRevit"),
                    "HelpUrl should be parsed from single-line value");
            }
            finally
            {
                File.Delete(tempFile);
            }
        }

        [Test]
        public void TestSingleLineHelpUrlWithQuotes()
        {
            var yamlContent = @"title:
  en_us: Test Command
help_url: ""https://github.com/pyrevitlabs/pyRevit""
";
            var tempFile = Path.GetTempFileName();
            File.WriteAllText(tempFile, yamlContent);

            try
            {
                var bundle = BundleParser.BundleYamlParser.Parse(tempFile);

                TestContext.Out.WriteLine($"HelpUrl: {bundle.HelpUrl ?? "null"}");

                Assert.That(bundle.HelpUrl, Is.EqualTo("https://github.com/pyrevitlabs/pyRevit"),
                    "HelpUrl should be parsed and quotes should be stripped");
            }
            finally
            {
                File.Delete(tempFile);
            }
        }

        [Test]
        public void TestLocalizedHelpUrls()
        {
            var yamlContent = @"title:
  en_us: Test Command
help_url:
  en_us: https://github.com/pyrevitlabs/pyRevit
  fr_fr: https://github.com/pyrevitlabs/pyRevit/blob/main/docs/fr
  de_de: https://github.com/pyrevitlabs/pyRevit/blob/main/docs/de
";
            var tempFile = Path.GetTempFileName();
            File.WriteAllText(tempFile, yamlContent);

            try
            {
                var bundle = BundleParser.BundleYamlParser.Parse(tempFile);

                TestContext.Out.WriteLine($"HelpUrls count: {bundle.HelpUrls?.Count ?? 0}");
                if (bundle.HelpUrls != null)
                {
                    foreach (var kvp in bundle.HelpUrls)
                    {
                        TestContext.Out.WriteLine($"  {kvp.Key}: {kvp.Value}");
                    }
                }

                Assert.That(bundle.HelpUrls, Is.Not.Null, "HelpUrls dictionary should be created");
                Assert.That(bundle.HelpUrls, Has.Count.EqualTo(3), "Should have 3 localized help URLs");
                Assert.That(bundle.HelpUrls["en_us"], Is.EqualTo("https://github.com/pyrevitlabs/pyRevit"));
                Assert.That(bundle.HelpUrls["fr_fr"], Is.EqualTo("https://github.com/pyrevitlabs/pyRevit/blob/main/docs/fr"));
                Assert.That(bundle.HelpUrls["de_de"], Is.EqualTo("https://github.com/pyrevitlabs/pyRevit/blob/main/docs/de"));
            }
            finally
            {
                File.Delete(tempFile);
            }
        }

        [Test]
        public void TestHelpUrlInComponent()
        {
            var yamlContent = @"title:
  en_us: Test Command
help_url: https://example.com/help
";
            var tempFile = Path.GetTempFileName();
            File.WriteAllText(tempFile, yamlContent);

            try
            {
                var bundle = BundleParser.BundleYamlParser.Parse(tempFile);

                Assert.That(bundle.HelpUrl, Is.EqualTo("https://example.com/help"));

                TestContext.Out.WriteLine($"Bundle HelpUrl: {bundle.HelpUrl}");
            }
            finally
            {
                File.Delete(tempFile);
            }
        }

        [Test]
        public void TestHelpUrlsWiringToComponent()
        {
            var yamlContent = @"title:
  en_us: Test Command
help_url:
  en_us: https://example.com/help/en
  fr_fr: https://example.com/help/fr
";
            var tempFile = Path.GetTempFileName();
            File.WriteAllText(tempFile, yamlContent);

            try
            {
                var bundle = BundleParser.BundleYamlParser.Parse(tempFile);

                Assert.That(bundle.HelpUrls, Is.Not.Null, "HelpUrls should be populated in ParsedBundle");
                Assert.That(bundle.HelpUrls["en_us"], Is.EqualTo("https://example.com/help/en"));
                Assert.That(bundle.HelpUrls["fr_fr"], Is.EqualTo("https://example.com/help/fr"));

                TestContext.Out.WriteLine($"Bundle HelpUrls: {bundle.HelpUrls.Count} entries");
                TestContext.Out.WriteLine($"  en_us: {bundle.HelpUrls["en_us"]}");
                TestContext.Out.WriteLine($"  fr_fr: {bundle.HelpUrls["fr_fr"]}");
            }
            finally
            {
                File.Delete(tempFile);
            }
        }

        [Test]
        public void TestNoHelpUrlSpecified()
        {
            var yamlContent = @"title:
  en_us: Test Command
";
            var tempFile = Path.GetTempFileName();
            File.WriteAllText(tempFile, yamlContent);

            try
            {
                var bundle = BundleParser.BundleYamlParser.Parse(tempFile);

                TestContext.Out.WriteLine($"HelpUrl: {bundle.HelpUrl ?? "null"}");
                TestContext.Out.WriteLine($"HelpUrls: {bundle.HelpUrls?.Count ?? 0}");

                Assert.That(bundle.HelpUrl, Is.Null, "HelpUrl should be null when not specified");
                Assert.That(bundle.HelpUrls, Is.Null.Or.Empty, "HelpUrls should be null or empty when not specified");
            }
            finally
            {
                File.Delete(tempFile);
            }
        }



        [Test]
        public void TestHelpUrlWithSpaces()
        {
            var yamlContent = @"title:
  en_us: Test Command
help_url: https://example.com/path with spaces
";
            var tempFile = Path.GetTempFileName();
            File.WriteAllText(tempFile, yamlContent);

            try
            {
                var bundle = BundleParser.BundleYamlParser.Parse(tempFile);

                TestContext.Out.WriteLine($"HelpUrl: {bundle.HelpUrl ?? "null"}");

                Assert.That(bundle.HelpUrl, Is.EqualTo("https://example.com/path with spaces"),
                    "HelpUrl should preserve spaces in URLs");
            }
            finally
            {
                File.Delete(tempFile);
            }
        }

        [Test]
        public void TestYouTubeHelpUrl()
        {
            var yamlContent = @"title:
  en_us: Test Command
help_url: ""https://www.youtube.com/watch?v=H7b8hjHbauE&t=8s&list=PLc_1PNcpnV57FWI6G8Cd09umHpSOzvamf""
";
            var tempFile = Path.GetTempFileName();
            File.WriteAllText(tempFile, yamlContent);

            try
            {
                var bundle = BundleParser.BundleYamlParser.Parse(tempFile);

                TestContext.Out.WriteLine($"HelpUrl: {bundle.HelpUrl ?? "null"}");

                Assert.That(bundle.HelpUrl, Is.EqualTo("https://www.youtube.com/watch?v=H7b8hjHbauE&t=8s&list=PLc_1PNcpnV57FWI6G8Cd09umHpSOzvamf"),
                    "HelpUrl should parse complex YouTube URL");
            }
            finally
            {
                File.Delete(tempFile);
            }
        }

        [Test]
        public void TestLocalizedYouTubeHelpUrls()
        {
            var yamlContent = @"title:
  en_us: Test Command
help_url:
  en_us: ""https://www.youtube.com/watch?v=H7b8hjHbauE&t=8s&list=PLc_1PNcpnV57FWI6G8Cd09umHpSOzvamf""
  chinese_s: ""https://www.youtube.com/watch?v=H7b8hjHbauE&t=8s&list=PLc_1PNcpnV57FWI6G8Cd09umHpSOzvamf""
";
            var tempFile = Path.GetTempFileName();
            File.WriteAllText(tempFile, yamlContent);

            try
            {
                var bundle = BundleParser.BundleYamlParser.Parse(tempFile);

                TestContext.Out.WriteLine($"HelpUrls count: {bundle.HelpUrls?.Count ?? 0}");
                if (bundle.HelpUrls != null)
                {
                    foreach (var kvp in bundle.HelpUrls)
                    {
                        TestContext.Out.WriteLine($"  {kvp.Key}: {kvp.Value}");
                    }
                }

                Assert.That(bundle.HelpUrls, Is.Not.Null, "HelpUrls dictionary should be created");
                Assert.That(bundle.HelpUrls, Has.Count.EqualTo(2), "Should have 2 localized help URLs");
                Assert.That(bundle.HelpUrls["en_us"], Is.EqualTo("https://www.youtube.com/watch?v=H7b8hjHbauE&t=8s&list=PLc_1PNcpnV57FWI6G8Cd09umHpSOzvamf"));
                Assert.That(bundle.HelpUrls["chinese_s"], Is.EqualTo("https://www.youtube.com/watch?v=H7b8hjHbauE&t=8s&list=PLc_1PNcpnV57FWI6G8Cd09umHpSOzvamf"));
            }
            finally
            {
                File.Delete(tempFile);
            }
        }
    }
}
