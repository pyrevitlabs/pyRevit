using System.IO;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    internal class FullIntegrationQuoteTest
    {
        [Test]
        public void TestFullIntegrationWithParsedComponent()
        {
            // Create a temporary directory structure to test the full parsing pipeline
            var tempDir = Path.Combine(Path.GetTempPath(), "pyRevitQuoteTest", "TestExtension.extension", "TestTab.tab", "TestPanel.panel", "Search.pushbutton");
            
            try
            {
                Directory.CreateDirectory(tempDir);
                
                // Create the exact bundle.yaml from the user's Search button
                var bundleFile = Path.Combine(tempDir, "bundle.yaml");
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

                File.WriteAllText(bundleFile, testYaml, System.Text.Encoding.UTF8);
                
                // Create a dummy script file
                var scriptFile = Path.Combine(tempDir, "script.py");
                File.WriteAllText(scriptFile, "print('Hello World')");

                // Test full extension parsing
                var extensionDir = Path.Combine(Path.GetTempPath(), "pyRevitQuoteTest", "TestExtension.extension");
                var extensions = ParseInstalledExtensions(extensionDir).ToList();
                
                Assert.That(extensions.Count, Is.EqualTo(1), "Should find one extension");
                
                var extension = extensions[0];
                Assert.That(extension.Name, Is.EqualTo("TestExtension"), "Extension name should be TestExtension");
                
                // Navigate to the Search button component
                var tabComponent = extension.Children?.FirstOrDefault(c => c.Name == "TestTab");
                Assert.IsNotNull(tabComponent, "Should find TestTab component");
                
                var panelComponent = tabComponent.Children?.FirstOrDefault(c => c.Name == "TestPanel");
                Assert.IsNotNull(panelComponent, "Should find TestPanel component");
                
                var searchComponent = panelComponent.Children?.FirstOrDefault(c => c.Name == "Search");
                Assert.IsNotNull(searchComponent, "Should find Search component");
                
                // Test that Title property has no quotes
                Console.WriteLine($"SearchComponent.Title: '{searchComponent.Title}'");
                Console.WriteLine($"SearchComponent.Tooltip: '{searchComponent.Tooltip}'");
                
                // The Title property should be set to the default locale value (en_us) without quotes
                Assert.That(searchComponent.Title, Is.EqualTo("Search"), "Title should be 'Search' without quotes");
                Assert.That(searchComponent.Tooltip, Is.EqualTo("The best interface ever!"), "Tooltip should be 'The best interface ever!' without quotes");
                
                // Test localized titles are all quote-free
                Console.WriteLine("=== LocalizedTitles ===");
                foreach (var localizedTitle in searchComponent.LocalizedTitles)
                {
                    Console.WriteLine($"[{localizedTitle.Key}]: '{localizedTitle.Value}' (Length: {localizedTitle.Value.Length})");
                    
                    // Check for any quotes in the value
                    if (localizedTitle.Value.Contains("\"") || localizedTitle.Value.Contains("'"))
                    {
                        Assert.Fail($"LocalizedTitles still contains quotes in {localizedTitle.Key}: '{localizedTitle.Value}'");
                    }
                }
                
                // Test localized tooltips are all quote-free
                Console.WriteLine("=== LocalizedTooltips ===");
                foreach (var localizedTooltip in searchComponent.LocalizedTooltips)
                {
                    Console.WriteLine($"[{localizedTooltip.Key}]: '{localizedTooltip.Value}' (Length: {localizedTooltip.Value.Length})");
                    
                    // Check for any quotes in the value
                    if (localizedTooltip.Value.Contains("\"") || localizedTooltip.Value.Contains("'"))
                    {
                        Assert.Fail($"LocalizedTooltips still contains quotes in {localizedTooltip.Key}: '{localizedTooltip.Value}'");
                    }
                }
                
                // Specific verification of the problematic entries
                Assert.That(searchComponent.LocalizedTitles["en_us"], Is.EqualTo("Search"), "en_us title should be 'Search' without quotes");
                Assert.That(searchComponent.LocalizedTitles["es_es"], Is.EqualTo("Buscar"), "es_es title should be 'Buscar' without quotes");
                Assert.That(searchComponent.LocalizedTitles["fa"], Is.EqualTo("جستجو"), "fa title should be 'جستجو' without quotes");
                Assert.That(searchComponent.LocalizedTitles["bg"], Is.EqualTo("Търси"), "bg title should be 'Търси' without quotes");
                Assert.That(searchComponent.LocalizedTitles["nl_nl"], Is.EqualTo("Zoek"), "nl_nl title should be 'Zoek' without quotes");
                Assert.That(searchComponent.LocalizedTitles["fr_fr"], Is.EqualTo("Rechercher"), "fr_fr title should be 'Rechercher' without quotes");
                Assert.That(searchComponent.LocalizedTitles["de_de"], Is.EqualTo("Suche"), "de_de title should be 'Suche' without quotes");
            }
            finally
            {
                // Clean up
                var baseDir = Path.Combine(Path.GetTempPath(), "pyRevitQuoteTest");
                if (Directory.Exists(baseDir))
                {
                    Directory.Delete(baseDir, true);
                }
            }
        }
    }
}
