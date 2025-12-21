using pyRevitExtensionParser;
using System.IO;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    internal class QuoteDebuggingTest
    {
        [Test]
        public void DebugUserSpecificSearchButton()
        {
            // Create the exact bundle.yaml from the user's Search button
            var testYaml = @"tooltip:
  ru: Самый лучший интерфейс!
  en_us: The best interface ever!
  es_es: Lo mejor que hay!
  de_de: Öffnet das Eingabefeld für die Suche!
  fr_fr: La meilleure interface!
title:
  ru: Поиск
  en_us: 'Search'
  fa: 'جستجو'
  bg: 'Търси'
  nl_nl: 'Zoek'
  fr_fr: 'Rechercher'
  de_de: 'Suche'
  es_es: ""Buscar""
context: zero-doc";

            var tempFile = Path.GetTempFileName();
            try
            {
                File.WriteAllText(tempFile, testYaml, System.Text.Encoding.UTF8);

                // Test 1: Direct BundleParser parsing
                var bundleResult = BundleParser.BundleYamlParser.Parse(tempFile);
                
                Console.WriteLine("=== BundleParser Results ===");
                foreach (var title in bundleResult.Titles)
                {
                    Console.WriteLine($"[{title.Key}]: '{title.Value}' (Length: {title.Value.Length})");
                    
                    // Check for any quotes in the value
                    if (title.Value.Contains("\"") || title.Value.Contains("'"))
                    {
                        Assert.Fail($"BundleParser failed to strip quotes from {title.Key}: '{title.Value}'");
                    }
                }

                // Test 2: GetLocalizedValue method behavior
                Console.WriteLine("\n=== GetLocalizedValue Results ===");
                var enUsTitle = GetLocalizedValue(bundleResult.Titles, "en_us");
                var esEsTitle = GetLocalizedValue(bundleResult.Titles, "es_es");
                var faTitle = GetLocalizedValue(bundleResult.Titles, "fa");
                
                Console.WriteLine($"en_us: '{enUsTitle}'");
                Console.WriteLine($"es_es: '{esEsTitle}'");
                Console.WriteLine($"fa: '{faTitle}'");
                
                // Verify these don't have quotes
                Assert.That(enUsTitle, Is.EqualTo("Search"), "en_us title should be 'Search' without quotes");
                Assert.That(esEsTitle, Is.EqualTo("Buscar"), "es_es title should be 'Buscar' without quotes");
                Assert.That(faTitle, Is.EqualTo("جستجو"), "fa title should be 'جستجو' without quotes");
            }
            finally
            {
                if (File.Exists(tempFile))
                    File.Delete(tempFile);
            }
        }

        /// <summary>
        /// Helper method to test GetLocalizedValue behavior (same as in ExtensionParser)
        /// </summary>
        private static string? GetLocalizedValue(System.Collections.Generic.Dictionary<string, string> localizedValues, string? preferredLocale = null)
        {
            if (localizedValues == null || localizedValues.Count == 0)
                return null;

            // Try preferred locale first
            if (preferredLocale != null && localizedValues.ContainsKey(preferredLocale))
                return localizedValues[preferredLocale];

            // Try default locale
            if (localizedValues.ContainsKey(DefaultLocale))
                return localizedValues[DefaultLocale];

            // Return first available value
            return localizedValues.Values.FirstOrDefault();
        }
    }
}